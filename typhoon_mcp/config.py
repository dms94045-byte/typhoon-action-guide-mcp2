import os

def get_env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return v

# 공공데이터포털(기상청_태풍정보 조회서비스) 서비스키 (URL 인코딩 형태 그대로 사용 가능)
KMA_TYPHOON_SERVICE_KEY = get_env("KMA_TYPHOON_SERVICE_KEY")

# Render/서버 설정
PORT = int(get_env("PORT", "8000") or "8000")
HOST = get_env("HOST", "0.0.0.0") or "0.0.0.0"

# 외부 API 호출 타임아웃(초)
HTTP_TIMEOUT = float(get_env("HTTP_TIMEOUT", "10") or "10")

# 캐시 TTL(초)
CACHE_TTL_SECONDS = int(get_env("CACHE_TTL_SECONDS", "600") or "600")
