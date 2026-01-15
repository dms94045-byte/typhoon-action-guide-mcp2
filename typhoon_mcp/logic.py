from __future__ import annotations
import datetime as dt
import math
from typing import Optional, Tuple

from .kma_client import KmaTyphoonClient, TyphoonPoint
from .region import find_region, infer_environment, infer_intent, Region
from .formatter import parse_kst_yyyymmddhhmm, fmt_kst_baseline, fmt_risk_window, KST

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # 지구 반지름(km)
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def stage(now: dt.datetime, risk_start: dt.datetime, risk_end: dt.datetime) -> str:
    if now < risk_start:
        return "접근 전"
    if risk_start <= now <= risk_end:
        return "영향 중"
    return "통과 후"

def choose_actions(env: str, stg: str) -> tuple[list[str], list[str], str]:
    # 최대 3 / 2 / 1문장
    base_before = [
        "잠들기 전에 창문·베란다 주변(화분/간판/자전거 등)을 고정하거나 실내로 옮기세요.",
        "휴대폰을 충분히 충전하고, 재난 알림을 켜두세요.",
        "침수 우려가 있으면 차량은 지하·저지대 대신 상대적으로 높은 곳으로 옮겨두세요.",
    ]
    base_during = [
        "가능하면 실내에 머물고, 불필요한 외출·이동은 미루세요.",
        "창문은 닫고, 유리 주변에서는 떨어져 있는 것이 안전합니다.",
        "공식 안내(지자체/기상청/재난문자)를 수시로 확인하세요.",
    ]
    base_after = [
        "떨어진 전선·파손 시설물에 가까이 가지 마세요.",
        "침수된 도로·지하차도는 우회하고, 주변 안전을 먼저 확인하세요.",
        "정리·복구는 바람이 약해진 뒤, 안전이 확인된 다음에 진행하세요.",
    ]

    forbid_coast = ["파도·강수 상황을 보러 해안/방파제에 접근", "강풍 시간대 해안도로·교량 통과"]
    forbid_river = ["침수된 도로·지하차도 진입", "지하주차장/반지하 출입을 늦게 결정"]
    forbid_mountain = ["계곡·등산로 접근", "비탈면/산사태 우려 지역 통행"]
    forbid_inland = ["강풍 시간대 옥외 작업", "가로수·간판 많은 길로 이동"]

    if stg == "접근 전":
        must = base_before
    elif stg == "영향 중":
        must = base_during
    else:
        must = base_after

    if env == "해안·섬":
        forbid = forbid_coast
        summary_hint = "해안 접근을 피하고 실내에서 대비"
    elif env == "저지대·하천":
        forbid = forbid_river
        summary_hint = "침수 위험을 먼저 줄이기"
    elif env == "산간":
        forbid = forbid_mountain
        summary_hint = "산사태·계곡 급류 위험을 피하기"
    elif env == "내륙":
        forbid = forbid_inland
        summary_hint = "강풍·낙하물 위험을 피하기"
    else:
        forbid = ["불필요한 외출·이동", "위험 지역(해안·하천·산간) 접근"]
        summary_hint = "불필요한 이동을 줄이기"

    # 제한
    must = must[:3]
    forbid = forbid[:2]

    one_line = {
        "접근 전": f"가장 위험한 시간대 전에 미리 대비하고, {summary_hint}가 중요합니다.",
        "영향 중": f"지금은 영향이 커질 수 있어, 이동을 줄이고 {summary_hint}가 중요합니다.",
        "통과 후": f"지나간 뒤에도 잔여 강풍·침수·파손 위험이 남을 수 있어, {summary_hint}를 유지하세요.",
    }[stg]

    return must, forbid, one_line

def summarize_track(points: list[TyphoonPoint], region: Optional[Region], now: dt.datetime) -> tuple[str, str | None, tuple[dt.datetime, dt.datetime] | None]:
    # typLoc가 있으면 활용하되, 없으면 거리기반 요약
    if not points:
        return "현재 발표된 태풍(열대저압부) 정보가 없습니다.", None, None

    # 시간순 정렬
    pts_sorted = sorted(points, key=lambda p: p.typTm)

    # 위험시간(가장 가까운 지점) 계산
    center_dt = None
    risk_text = None
    risk_window = None

    if region:
        best = None
        for idx, p in enumerate(pts_sorted):
            if p.lat is None or p.lon is None:
                continue
            d = haversine_km(region.lat, region.lon, p.lat, p.lon)
            if best is None or d < best[0]:
                best = (d, idx, p)
        if best:
            _, idx, p = best
            center_dt = parse_kst_yyyymmddhhmm(p.typTm)
            prev_dt = parse_kst_yyyymmddhhmm(pts_sorted[idx-1].typTm) if idx-1 >= 0 else None
            next_dt = parse_kst_yyyymmddhhmm(pts_sorted[idx+1].typTm) if idx+1 < len(pts_sorted) else None
            if center_dt:
                risk_text, start_dt, end_dt = fmt_risk_window(center_dt, prev_dt, next_dt, now)
                risk_window = (start_dt, end_dt)

    # 이동 요약문
    # typLoc: "○○ 남쪽 해상" 같은 문구가 들어오는 경우가 많음
    loc_phrase = None
    for p in reversed(pts_sorted):
        if p.loc_kr:
            loc_phrase = p.loc_kr
            break

    if loc_phrase and center_dt and risk_text:
        track = f"태풍은 {risk_text} 무렵 {loc_phrase} 부근을 지나갈 가능성이 있습니다."
    elif center_dt and risk_text:
        where = (region.name + " 부근") if region else "사용자 지역 부근"
        track = f"태풍은 {risk_text} 무렵 {where}에 가장 가깝게 접근할 가능성이 있습니다."
    else:
        # 지역이 없거나 계산 불가
        track = "태풍의 예상 경로는 변동될 수 있어, 현재 예보 기준으로 가장 영향이 큰 시간대를 우선 안내합니다."

    return track, (risk_text if risk_text else None), risk_window

async def build_response(user_text: str, client: KmaTyphoonClient) -> str:
    now = dt.datetime.now(KST)

    region = find_region(user_text)
    env = infer_environment(user_text) or ("해안·섬" if (region and region.name in ["제주", "제주시", "서귀포", "부산", "여수", "목포", "남해안", "동해안", "서해안"]) else None)
    intent = infer_intent(user_text)

    # 정보가 거의 없으면 질문 유도(2단계 중 1단계만 제시)
    if (region is None) and (env is None) and (intent == "일반"):
        return (
            "빠르게 안내해드릴게요.\n"
            "지금 계신 곳은 어디에 더 가까운가요?\n\n"
            "1️⃣ 해안·섬 지역\n"
            "2️⃣ 내륙 도시\n"
            "3️⃣ 산간·하천 인근"
        )

    try:
        tmFc, points, typ_name = await client.fetch_latest()
    except Exception:
        # API 실패/키 누락 등
        return (
            "[기준 정보]\n"
            "현재는 공식 태풍 예보 정보를 불러오지 못했습니다. (API 설정/네트워크 문제)\n\n"
            "[태풍 이동 및 시간 요약]\n"
            "정확한 경로 안내 대신, 안전을 위한 기본 행동만 우선 안내드립니다.\n\n"
            "[지금 반드시 해야 할 행동]\n"
            "- 창문·베란다 주변 물건을 고정하거나 실내로 옮기세요.\n"
            "- 재난 알림을 켜고 휴대폰을 충전해두세요.\n"
            "- 해안·하천·산간 등 위험 지역 접근은 피하세요.\n\n"
            "[하면 안 되는 행동]\n"
            "- 위험 상황 확인을 위해 밖으로 나가기\n"
            "- 침수 우려 지역(지하차도/하천변) 이동\n\n"
            "[한 줄 요약]\n"
            "지금은 예보를 불러오는 중이므로, 기본 대비를 먼저 해두는 것이 좋습니다."
        )

    if not tmFc or not points:
        # 예보 자체가 없을 때
        base = fmt_kst_baseline(tmFc) if tmFc else "현재 태풍 예보 데이터를 찾지 못했습니다."
        return (
            f"[기준 정보]\n{base}\n\n"
            "[태풍 이동 및 시간 요약]\n"
            "현재 발표된 태풍(열대저압부) 정보가 없습니다.\n\n"
            "[지금 반드시 해야 할 행동]\n"
            "- 기상특보/재난문자 등 공식 안내를 확인하세요.\n"
            "- 해안·하천·산간 등 위험 지역 접근은 피하세요.\n"
            "- 야외 활동 계획은 보수적으로 조정하세요.\n\n"
            "[하면 안 되는 행동]\n"
            "- 확인되지 않은 소문에 따라 이동\n"
            "- 위험 지역(해안·하천·산간) 접근\n\n"
            "[한 줄 요약]\n"
            "현재는 태풍 정보가 없지만, 공식 안내를 수시로 확인하는 것이 안전합니다."
        )

    base = fmt_kst_baseline(tmFc)

    track, risk_text, risk_window = summarize_track(points, region, now)

    if env is None:
        env = "내륙" if region else "일반"

    # 위험시간이 계산되지 않으면, 질문 대신 '지역을 알려달라'는 보조 문구를 한 줄만 추가
    if risk_text is None:
        extra = "지역(예: 제주/부산/대전 등)을 알려주시면 '가장 위험한 시간대'를 더 정확히 안내할 수 있어요."
        stg = "접근 전"
        must, forbid, one_line = choose_actions(env, stg)
        return _render(base, track + "\n" + extra, must, forbid, one_line)

    stg = stage(now, risk_window[0], risk_window[1]) if risk_window else "접근 전"
    must, forbid, one_line = choose_actions(env, stg)

    # intent별 문구를 조금 조정
    if intent == "외출가능":
        one_line = "지금 외출·이동이 필요한지 판단할 때는, '가장 위험한 시간대'를 피하는 것이 핵심입니다."
    elif intent == "안전시점":
        one_line = "태풍이 지나간 뒤에도 잔여 강풍·침수·시설물 피해가 있을 수 있어, 주변 안전을 먼저 확인하세요."

    return _render(base, track + (f"\n\n가장 영향이 큰 시간: {risk_text}" if risk_text else ""), must, forbid, one_line)

def _render(base: str, track: str, must: list[str], forbid: list[str], one_line: str) -> str:
    must_lines = "\n".join([f"- {x}" for x in must])
    forbid_lines = "\n".join([f"- {x}" for x in forbid])
    return (
        f"[기준 정보]\n{base}\n\n"
        f"[태풍 이동 및 시간 요약]\n{track}\n\n"
        f"[지금 반드시 해야 할 행동]\n{must_lines}\n\n"
        f"[하면 안 되는 행동]\n{forbid_lines}\n\n"
        f"[한 줄 요약]\n{one_line}"
    )
