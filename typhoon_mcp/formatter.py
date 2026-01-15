from __future__ import annotations
import datetime as dt
from typing import Tuple, Optional

KST = dt.timezone(dt.timedelta(hours=9))

def parse_kst_yyyymmddhhmm(s: str) -> Optional[dt.datetime]:
    if not s:
        return None
    try:
        return dt.datetime.strptime(s, "%Y%m%d%H%M").replace(tzinfo=KST)
    except Exception:
        return None

def fmt_kst_baseline(tmFc: str) -> str:
    d = parse_kst_yyyymmddhhmm(tmFc)
    if not d:
        return "기준 시각 정보를 불러오지 못했습니다."
    return f"{d.month}월 {d.day}일 {d.hour}시 기준 태풍 예보를 반영했습니다."

def time_bucket(d: dt.datetime) -> str:
    h = d.hour
    if h >= 22 or h < 1:
        return "늦은 밤"
    if 1 <= h < 6:
        return "새벽"
    if 6 <= h < 9:
        return "이른 아침"
    if 9 <= h < 12:
        return "오전"
    if 12 <= h < 18:
        return "낮"
    if 18 <= h < 22:
        return "저녁"
    return "밤"

def day_word(d: dt.datetime, now: dt.datetime) -> str:
    dd = (d.date() - now.date()).days
    if dd == 0:
        return "오늘"
    if dd == 1:
        return "내일"
    if dd == -1:
        return "어제"
    return f"{d.month}월 {d.day}일"

def fmt_range(start: dt.datetime, end: dt.datetime, now: dt.datetime) -> str:
    # "오늘 늦은 밤~내일 새벽" / "내일 오전 9~12시"
    sw = day_word(start, now)
    ew = day_word(end, now)
    sb = time_bucket(start)
    eb = time_bucket(end)

    # 시간을 범위로 더 정확하게 보여주기 위해 "시" 범위를 추가
    sH = start.hour
    eH = end.hour
    if start.date() == end.date():
        return f"{sw} {sb} {sH}~{eH}시 사이"
    # 날짜가 바뀌면 생활시간대만
    return f"{sw} {sb}~{ew} {eb} 사이"

def fmt_risk_window(center: dt.datetime, prev: Optional[dt.datetime], next_: Optional[dt.datetime], now: dt.datetime) -> Tuple[str, dt.datetime, dt.datetime]:
    # prev/next 간격이 너무 크면 +-3시간 기본
    default_start = center - dt.timedelta(hours=3)
    default_end = center + dt.timedelta(hours=3)

    start = prev or default_start
    end = next_ or default_end

    # 너무 넓으면 기본값으로 조정
    if (end - start) > dt.timedelta(hours=12):
        start, end = default_start, default_end

    # end가 start보다 앞서면 정리
    if end <= start:
        start, end = default_start, default_end

    return fmt_range(start, end, now), start, end
