# gateway/main.py
"""
FastAPI Application Entry Point for NotebookLM Gateway.
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gateway.auth_manager import GatewayAuthManager
from gateway.api_keys import APIKeyStore
from gateway.routes import notebooks, sources, chat, studio, admin

logger = logging.getLogger("notebooklm_gateway")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


class GatewayState:
    redis = None
    auth_mgr: GatewayAuthManager = None
    key_store: APIKeyStore = None
    start_time: float = 0.0


state = GatewayState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing NotebookLM Gateway Application...")
    state.start_time = time.time()

    # Redis connection (optional)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis.asyncio as aioredis
        state.redis = aioredis.from_url(redis_url, decode_responses=True)
        await state.redis.ping()
        logger.info("Redis connected successfully at %s", redis_url)
    except Exception as e:
        logger.info("Redis disabled or unreachable (%s); using in-memory / SQLite fallback.", e)
        state.redis = None

    # Auth & API Key Store
    token_dir = os.getenv("TOKEN_DIR", "./storage/tokens")
    db_path = os.getenv("DB_PATH", "./storage/db/gateway.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    state.auth_mgr = GatewayAuthManager(token_dir=token_dir)
    state.key_store = APIKeyStore(db_path=db_path, redis=state.redis)
    await state.key_store.init()

    app.state.app_state = state
    yield

    if state.redis:
        try:
            await state.redis.aclose()
        except Exception:
            pass
    logger.info("NotebookLM Gateway shut down cleanly.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="NotebookLM Personal API Gateway",
        description="Production API Gateway for NotebookLM Automation System (Video Overviews, Slide Decks, Audio, Reports, Chat)",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # Attach Routers
    app.include_router(notebooks.router, prefix="/v1")
    app.include_router(sources.router, prefix="/v1")
    app.include_router(chat.router, prefix="/v1")
    app.include_router(studio.router, prefix="/v1")
    app.include_router(admin.router)

    # Exception Handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(req: Request, exc: Exception):
        logger.error("Unhandled Exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": str(exc)},
        )

    @app.get("/health")
    async def health():
        accounts = state.auth_mgr.list_accounts() if state.auth_mgr else []
        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - state.start_time, 1) if state.start_time else 0,
            "redis_connected": state.redis is not None,
            "configured_accounts_count": len(accounts),
            "accounts": [a["account_id"] for a in accounts],
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("GATEWAY_HOST", "0.0.0.0")
    port = int(os.getenv("GATEWAY_PORT", "8000"))
    uvicorn.run("gateway.main:app", host=host, port=port, reload=True)
