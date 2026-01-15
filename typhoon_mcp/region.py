from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Region:
    name: str
    lat: float
    lon: float

# 한국 주요 권역/도시의 대략 좌표 (행정경계가 아니라 "가까운 지점"을 잡기 위한 용도)
# 정밀 서비스가 목적이 아니므로, PlayMCP 데모·프로토타입 수준의 보수적 근사값만 사용합니다.
REGIONS: list[Region] = [
    Region("제주", 33.4996, 126.5312),
    Region("제주시", 33.4996, 126.5312),
    Region("서귀포", 33.2541, 126.5601),
    Region("부산", 35.1796, 129.0756),
    Region("울산", 35.5384, 129.3114),
    Region("창원", 35.2278, 128.6811),
    Region("대구", 35.8714, 128.6014),
    Region("대전", 36.3504, 127.3845),
    Region("광주", 35.1595, 126.8526),
    Region("전주", 35.8242, 127.1480),
    Region("목포", 34.8118, 126.3922),
    Region("여수", 34.7604, 127.6622),
    Region("포항", 36.0190, 129.3435),
    Region("강릉", 37.7519, 128.8761),
    Region("춘천", 37.8813, 127.7298),
    Region("수원", 37.2636, 127.0286),
    Region("인천", 37.4563, 126.7052),
    Region("서울", 37.5665, 126.9780),
    Region("세종", 36.4800, 127.2890),
    Region("남해안", 34.9, 128.0),
    Region("동해안", 37.0, 129.0),
    Region("서해안", 36.5, 126.3),
    Region("내륙", 36.3, 127.7),
]

_ALIASES: dict[str, str] = {
    "제주도": "제주",
    "제주도민": "제주",
    "서귀포시": "서귀포",
    "부산시": "부산",
    "대전시": "대전",
    "남해": "남해안",
    "남해안": "남해안",
    "동해": "동해안",
    "서해": "서해안",
    "수도권": "서울",
    "서울시": "서울",
    "인천시": "인천",
    "전라도": "전주",
    "경상도": "대구",
}

def find_region(text: str) -> Optional[Region]:
    if not text:
        return None

    # 별칭 먼저
    for k, v in _ALIASES.items():
        if k in text:
            return next((r for r in REGIONS if r.name == v), None)

    # 직접 매칭(길이가 긴 것 우선)
    candidates = sorted(REGIONS, key=lambda r: len(r.name), reverse=True)
    for r in candidates:
        if r.name in text:
            return r

    # "~ 근처" 패턴
    m = re.search(r"([가-힣]{2,6})\s*근처", text)
    if m:
        key = m.group(1)
        for r in candidates:
            if key in r.name or r.name in key:
                return r

    return None

def infer_environment(text: str) -> str | None:
    if not text:
        return None
    t = text

    if any(k in t for k in ["해안", "바다", "방파제", "항구", "해변", "섬", "연안"]):
        return "해안·섬"
    if any(k in t for k in ["하천", "강", "저지대", "침수", "지하", "지하주차장", "하수", "배수구"]):
        return "저지대·하천"
    if any(k in t for k in ["산", "계곡", "산간", "비탈", "사면", "산사태"]):
        return "산간"
    if any(k in t for k in ["도시", "시내", "내륙", "아파트", "주택가"]):
        return "내륙"
    return None

def infer_intent(text: str) -> str:
    t = text or ""
    if any(k in t for k in ["언제", "몇 시", "시간", "최대", "제일", "가장", "영향"]):
        return "위험시간"
    if any(k in t for k in ["나가", "외출", "출발", "이동", "운전", "괜찮", "가능"]):
        return "외출가능"
    if any(k in t for k in ["안전", "언제쯤", "지났", "통과", "끝", "괜찮아져"]):
        return "안전시점"
    return "일반"
