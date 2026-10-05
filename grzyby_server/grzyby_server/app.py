import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel
from starlette.routing import Route

from grzyby_server import db
from grzyby_server.mcp_key import RequireKey
from grzyby_server.miejsca.tools import server as mcp
from grzyby_server.settings import settings

# Routes are declared without an /api prefix. The prefix belongs to the edge — the vite
# proxy in development, nginx in the image — which strips it before the request lands here.
# uvicorn configures its own logger, so messages here show up next to its startup lines.
log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # Without the database there is nothing to serve, so the server fails to start with a
    # clear error rather than failing every request later.
    db.pool.open(wait=True, timeout=10)
    with db.pool.connection() as conn:
        for name in db.migrate(conn):
            log.info("applied migration %s", name)
    # The MCP transport's own lifespan: a mounted app's lifespan never runs on its own.
    async with mcp.session_manager.run():
        yield
    db.pool.close()


app = FastAPI(title="grzyby", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Health(BaseModel):
    status: str


# Touches nothing outside the process, so it doubles as the cluster's liveness probe.
@app.get("/health")
def health() -> Health:
    return Health(status="ok")


# The MCP endpoint for chatbots, at /mcp — not under /api: it is the product's public address
# (nginx and the vite proxy pass it through unchanged). Stateless with JSON responses: every
# request stands alone, so any replica can answer and nothing is kept between calls.
mcp_http = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(allowed_hosts=settings.mcp_allowed_hosts),
)
# Every route of the MCP app (one: /mcp) behind the key.
app.router.routes.extend(
    Route(route.path, endpoint=RequireKey(route.app, settings.mcp_key, allow_public=settings.allow_public))
    if isinstance(route, Route)
    else route
    for route in mcp_http.routes
)

# Features add their routers here: app.include_router(notes) — and a layer in pyproject.toml.
