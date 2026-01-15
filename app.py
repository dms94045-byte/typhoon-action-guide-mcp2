from __future__ import annotations

import contextlib
import os

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

# Streamable HTTP 앱을 /mcp 경로로 제공 (기본값)
starlette_app = Starlette(
    routes=[
        Route("/", root, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Mount("/", app=mcp.streamable_http_app()),  # exposes /mcp by default
    ],
    lifespan=lifespan,
)

# CORS: 브라우저 기반 MCP 클라이언트/테스터 호환을 위해
# (Streamable HTTP는 Mcp-Session-Id 헤더를 사용)
app = CORSMiddleware(
    starlette_app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

# uvicorn entry:
#   uvicorn app:app --host 0.0.0.0 --port $PORT
