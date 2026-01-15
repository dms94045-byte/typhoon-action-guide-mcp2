# 🌀 태풍 대응 행동 가이드 MCP (PlayMCP 제출용)

이 서버는 MCP Streamable HTTP 전송 방식으로 동작하며, 엔드포인트는 기본적으로 `/mcp` 입니다.  
공공데이터포털의 **기상청_태풍정보 조회서비스**(REST, JSON/XML)를 호출해 최신 통보문 기준으로 안내합니다.

---

## 1) 로컬 실행

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt

# .env 생성
cp .env.example .env
# KMA_TYPHOON_SERVICE_KEY 값만 채우기

uvicorn app:app --host 0.0.0.0 --port 8000
```

- 기본 안내: `http://localhost:8000/`
- 헬스체크: `http://localhost:8000/health`
- MCP 엔드포인트: `http://localhost:8000/mcp`

---

## 2) Render 배포 (Standard 플랜)

### (A) GitHub에 업로드
- 이 저장소 전체를 GitHub에 푸시합니다.
- `.env`는 절대 커밋하지 말고, `.env.example`만 올립니다.

### (B) Render에서 Web Service 생성
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Environment Variable:
  - `KMA_TYPHOON_SERVICE_KEY` = 공공데이터포털 서비스키(문자열 그대로)

배포 후 MCP URL 예시: `https://<render-app>.onrender.com/mcp`

---

## 3) PlayMCP 등록(개요)
- Server URL: `https://<render-app>.onrender.com/mcp`
- Transport: Streamable HTTP

---

## 4) MCP에서 제공하는 도구/프롬프트

### Prompt
- `typhoon_action_guide_system_prompt()` : “태풍 대응 행동 가이드 MCP” 운영 규칙(시스템 프롬프트)

### Tool
- `typhoon_action_guide(user_message: str) -> str`  
  사용자 문장을 받아 아래 고정 출력 구조로 반환합니다:
  - [기준 정보] / [태풍 이동 및 시간 요약] / [지금 반드시 해야 할 행동] / [하면 안 되는 행동] / [한 줄 요약]

---

## 5) API 파라미터 메모
요청 주소(공공데이터포털 문서 기준):
- `https://apis.data.go.kr/1360000/TyphoonInfoService/getTyphoonInfo`

필수 파라미터:
- `serviceKey`, `pageNo`, `numOfRows`, `fromTmFc`, `toTmFc`

---

## 6) 보안 메모
서비스키를 채팅/문서에 그대로 붙여넣었다면, 키 재발급/폐기 후 새 키로 교체하는 것을 권장합니다.
