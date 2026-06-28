"""FastAPI-приложение REST API для веб-панели администратора."""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api import auth, ws
from api.routers import cache, chats, graph, media, stats, users

app = FastAPI(
    title="Zynto Bot Admin API",
    version="1.0.0",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": str(exc)},
    )


PREFIX = "/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(ws.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(chats.router, prefix=PREFIX)
app.include_router(media.router, prefix=PREFIX)
app.include_router(stats.router, prefix=PREFIX)
app.include_router(graph.router, prefix=PREFIX)
app.include_router(cache.router, prefix=PREFIX)


@app.get("/v1/health")
async def health() -> dict:
    return {"status": "ok"}


# ── Раздача React SPA ──────────────────────────────────────────────────────
_SPA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")

if os.path.isdir(_SPA_DIR):
    _assets = os.path.join(_SPA_DIR, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="spa_assets")

    @app.get("/", include_in_schema=False)
    async def _spa_root() -> FileResponse:
        return FileResponse(os.path.join(_SPA_DIR, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(os.path.join(_SPA_DIR, "index.html"))
