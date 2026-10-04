import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from grzyby_server import db
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


# Features add their routers here: app.include_router(notes) — and a layer in pyproject.toml.
