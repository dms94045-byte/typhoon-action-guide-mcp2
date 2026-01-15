from __future__ import annotations

import contextlib

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route
from starlette.middleware.cors import CORSMiddleware

from mcp.server.fastmcp import FastMCP

from typhoon_mcp.kma_client import KmaTyphoonClient
from typhoon_mcp.logic import build_response
from typhoon_mcp.prompts import SYSTEM_PROMPT


mcp = FastMCP("Typhoon Action Guide MCP", json_response=True)
client = KmaTyphoonClient()


@mcp.prompt()
def typhoon_action_guide_system_prompt() -> str:
    """태풍 대응 행동 가이드 MCP 시스템 프롬프트"""
    return SYSTEM_PROMPT


@mcp.tool()
async def typhoon_action_guide(user_message: str) -> str:
    """사용자 메시지를 기반으로 태풍 대응 행동 가이드를 생성합니다."""
    return await build_response(user_message, client)


async def health(request):
    return JSONResponse({"ok": True, "name": "Typhoon Action Guide MCP"})


async def root(request):
    return PlainTextResponse("Typhoon Action Guide MCP is running. MCP endpoint is /mcp")


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        yield


def _make_streamable_app():
    """
    MCP SDK 버전에 따라 streamable_http_app() 시그니처가 달라질 수 있어
    허용 호스트 옵션이 있으면 사용하고, 없으면 기본값으로 생성합니다.
    """
    try:
        # 일부 버전에서 allowed_hosts 인자를 지원할 수 있어 선제 대응
        return mcp.streamable_http_app(allowed_hosts=["*"])
    except TypeError:
        return mcp.streamable_http_app()


# Streamable HTTP 앱을 /mcp 경로로 제공 (기본값)
streamable_app = _make_streamable_app()

starlette_app = Starlette(
    routes=[
        Route("/", root, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Mount("/", app=streamable_app),  # exposes /mcp by default
    ],
    lifespan=lifespan,
)

# 1) CORS: 브라우저 기반 MCP 클라이언트/테스터 호환
#    (Streamable HTTP는 Mcp-Session-Id 헤더를 사용)
cors_app = CORSMiddleware(
    starlette_app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


# uvicorn entry:
#   uvicorn app:app --host 0.0.0.0 --port $PORT

# 최종 ASGI app
app = cors_app
