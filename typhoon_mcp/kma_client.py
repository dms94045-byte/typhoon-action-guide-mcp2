from __future__ import annotations
import asyncio
import datetime as dt
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from .config import KMA_TYPHOON_SERVICE_KEY, HTTP_TIMEOUT, CACHE_TTL_SECONDS

BASE_URL = "https://apis.data.go.kr/1360000/TyphoonInfoService/getTyphoonInfo"

@dataclass
class TyphoonPoint:
    tmFc: str          # 통보문 발표 시각 (YYYYMMDDHHMM)
    typSeq: str | None # 태풍번호
    tmSeq: str | None  # 통보문 발표 호수
    typTm: str         # 태풍시각 (YYYYMMDDHHMM)
    lat: float | None
    lon: float | None
    loc_kr: str | None
    dir: str | None
    sp_kmh: float | None
    ps_hpa: float | None
    ws_ms: float | None
    rad15_km: float | None
    rad25_km: float | None
    name_kr: str | None
    name_en: str | None

class KmaTyphoonClient:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, list[TyphoonPoint]]] = {}
        self._lock = asyncio.Lock()

    async def fetch_latest(self) -> tuple[str | None, list[TyphoonPoint], str | None]:
        """
        Returns:
          - 기준 통보문 발표시각(tmFc) (없으면 None)
          - 해당 tmFc의 관측/예측 점 목록
          - 태풍 이름(한글) (없으면 None)
        """
        if not KMA_TYPHOON_SERVICE_KEY:
            raise RuntimeError("KMA_TYPHOON_SERVICE_KEY 환경변수가 설정되지 않았습니다.")

        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))  # KST
        # 공공데이터포털 태풍정보는 통상 최근 며칠 범위로 조회하는 패턴이 많아, 보수적으로 최근 3일로 조회
        start = (now - dt.timedelta(days=2)).strftime("%Y%m%d")
        end = now.strftime("%Y%m%d")

        cache_key = f"{start}:{end}"
        async with self._lock:
            cached = self._cache.get(cache_key)
            if cached and (now.timestamp() - cached[0]) < CACHE_TTL_SECONDS:
                pts = cached[1]
                tmfc = max((p.tmFc for p in pts), default=None)
                name = _pick_name(pts)
                return tmfc, _filter_latest_bulletin(pts, tmfc), name

        params = {
            "serviceKey": KMA_TYPHOON_SERVICE_KEY,  # data.go.kr는 serviceKey/ServiceKey 둘 다 수용되는 경우가 많음
            "pageNo": 1,
            "numOfRows": 5000,
            "dataType": "JSON",
            "fromTmFc": start,
            "toTmFc": end,
        }

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.get(BASE_URL, params=params)
            r.raise_for_status()
            data = r.json()

        pts = _parse_points(data)
        async with self._lock:
            self._cache[cache_key] = (now.timestamp(), pts)

        tmfc = max((p.tmFc for p in pts), default=None)
        latest_pts = _filter_latest_bulletin(pts, tmfc)
        name = _pick_name(latest_pts)
        return tmfc, latest_pts, name

def _safe_float(x: Any) -> float | None:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None

def _parse_points(data: dict[str, Any]) -> list[TyphoonPoint]:
    # expected: {"response":{"header":...,"body":{"items":{"item":[...]}}}}
    items = (
        data.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
    )
    if isinstance(items, dict):
        items = [items]

    out: list[TyphoonPoint] = []
    for it in items or []:
        out.append(
            TyphoonPoint(
                tmFc=str(it.get("tmFc") or ""),
                typSeq=(str(it.get("typSeq")) if it.get("typSeq") is not None else None),
                tmSeq=(str(it.get("tmSeq")) if it.get("tmSeq") is not None else None),
                typTm=str(it.get("typTm") or ""),
                lat=_safe_float(it.get("typLat")),
                lon=_safe_float(it.get("typLon")),
                loc_kr=(it.get("typLoc") or None),
                dir=(it.get("typDir") or None),
                sp_kmh=_safe_float(it.get("typSp")),
                ps_hpa=_safe_float(it.get("typPs")),
                ws_ms=_safe_float(it.get("typWs")),
                rad15_km=_safe_float(it.get("typ15")),
                rad25_km=_safe_float(it.get("typ25")),
                name_kr=(it.get("typName") or None),
                name_en=(it.get("typEn") or None),
            )
        )
    return out

def _filter_latest_bulletin(pts: list[TyphoonPoint], tmfc: str | None) -> list[TyphoonPoint]:
    if not tmfc:
        return pts
    subset = [p for p in pts if p.tmFc == tmfc]
    # 같은 tmFc에서 tmSeq가 여러 개일 수 있으니, 가장 큰 tmSeq만 남김
    tmseqs = [p.tmSeq for p in subset if p.tmSeq and p.tmSeq.isdigit()]
    if not tmseqs:
        return subset
    latest_tmseq = max(int(x) for x in tmseqs)
    return [p for p in subset if (p.tmSeq and p.tmSeq.isdigit() and int(p.tmSeq) == latest_tmseq)]

def _pick_name(pts: list[TyphoonPoint]) -> Optional[str]:
    for p in pts:
        if p.name_kr:
            return p.name_kr
    return None
