"""FastAPI 应用:聊天接口 + 健康检查 + 限流。"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import chat_daily_limit, chat_limit, chat_window_ms
from .data_loader import data_loader
from .policy import assert_publication_ready, sanitize_candidate, validate_chat_payload

limiter = Limiter(key_func=get_remote_address, default_limits=[])


def create_app() -> FastAPI:
    candidate, style, presentation, answer_question = data_loader.load()
    assert_publication_ready(candidate)
    public_candidate = sanitize_candidate(candidate)

    app = FastAPI(title="Interview Agent", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_request: Request, _exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "RATE_LIMITED", "message": "提问有些频繁，请稍后再试。"}},
        )

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/profile")
    async def profile() -> dict:
        return {
            "candidate": public_candidate,
            "style": style.model_dump(),
            "presentation": presentation.model_dump(),
        }

    @app.post("/api/chat")
    @limiter.limit(f"{chat_limit()}/{chat_window_ms() // 1000}second;{chat_daily_limit()}/day")
    async def chat(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "INVALID_JSON", "message": "请求格式无效。"}},
            )
        try:
            message, history = validate_chat_payload(payload)
        except ValueError as exc:
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "INVALID_QUESTION", "message": str(exc)}},
            )
        try:
            result = answer_question(message, history)
        except Exception:
            return JSONResponse(
                status_code=502,
                content={"error": {"code": "ASSISTANT_UNAVAILABLE", "message": "面试助理暂时无法回答，你仍可以继续浏览候选人资料。"}},
            )
        return JSONResponse(
            jsonable_encoder(result.model_dump()),
            headers={"cache-control": "no-store"},
        )

    return app
