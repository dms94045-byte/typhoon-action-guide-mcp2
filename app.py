from __future__ import annotations

import contextlib

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from mcp.server.fastmcp import FastMCP

from typhoon_mcp.kma_client import KmaTyphoonClient
from typhoon_mcp.logic import build_response
from typhoon_mcp.prompts import SYSTEM_PROMPT


# =========================================================
# MCP Core
# =========================================================

mcp = FastMCP(
    "Typhoon Action Guide MCP",
    json_response=True,
)

client = KmaTyphoonClient()


@mcp.prompt()
def typhoon_action_guide_system_prompt() -> str:
    """태풍 대응 행동 가이드 MCP 시스템 프롬프트"""
    return SYSTEM_PROMPT


@mcp.tool()
async def typhoon_action_guide(user_message: str) -> str:
    """사용자 메시지를 기반으로 태풍 대응 행동 가이드를 생성합니다."""
    return await build_response(user_message, client)


# =========================================================
# Basic Endpoints
# =========================================================

async def root(request):
    return PlainTextResponse(
        "Typhoon Action Guide MCP is running.\n"
        "MCP endpoint: /mcp"
    )


async def health(request):
    return JSONResponse({"ok": True})


# =========================================================
# Lifespan (FastMCP 세션 관리)
# =========================================================

@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        yield


# =========================================================
# Starlette App (중요)
# =========================================================

app = Starlette(
    routes=[
        Route("/", root, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        # FastMCP는 자체적으로 /mcp 경로를 노출함
        Route("/mcp", mcp.streamable_http_app(), methods=["POST"]),
    ],
    lifespan=lifespan,
)

# =========================================================
# Middleware (Render + PlayMCP 대응 핵심)
# =========================================================

# 1️⃣ Host 검증 완화 (Render 프록시 대응)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)

# 2️⃣ CORS (PlayMCP 콘솔 테스트용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

# =========================================================
# uvicorn 실행
# =========================================================
# Render Start Command:
# uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers
