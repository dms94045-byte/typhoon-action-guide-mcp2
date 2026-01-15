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


# =========================================================
# ✅ DNS rebinding/Host 검사 끄기 (PlayMCP 프록시 환경 필수)
# =========================================================
TransportSecuritySettings = None
for _path in (
    "mcp.server.transport_security",
    "mcp.server.security",
    "mcp.server.transport.security",
):
    try:
        mod = __import__(_path, fromlist=["TransportSecuritySettings"])
        TransportSecuritySettings = getattr(mod, "TransportSecuritySettings")
        break
    except Exception:
        pass

if TransportSecuritySettings is None:
    # 여기로 떨어지면, 네 설치된 mcp 패키지에 보안 설정이 없다는 뜻이라
    # requirements에서 mcp 버전을 올려야 함 (아래 2번 참고)
    mcp = FastMCP("Typhoon Action Guide MCP", json_response=True)
else:
    mcp = FastMCP(
        "Typhoon Action Guide MCP",
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )

client = KmaTyphoonClient()


@mcp.prompt()
def typhoon_action_guide_system_prompt() -> str:
    return SYSTEM_PROMPT


@mcp.tool()
async def typhoon_action_guide(user_message: str) -> str:
    return await build_response(user_message, client)


async def health(request):
    return JSONResponse({"ok": True, "name": "Typhoon Action Guide MCP"})


async def root(request):
    return PlainTextResponse("Typhoon Action Guide MCP is running. MCP endpoint is /mcp")


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        yield


# ✅ /mcp 는 streamable_http_app()가 처리 (기본이 /mcp)
starlette_app = Starlette(
    routes=[
        Route("/", root, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)

app = CORSMiddleware(
    starlette_app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)
