"""FastAPI-приложение REST API для веб-панели администратора."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
