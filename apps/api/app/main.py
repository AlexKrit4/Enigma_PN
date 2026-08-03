from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import from_url as redis_from_url

from app.config import get_settings
from app.routers import admin, auth, orders, plans, subscription

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.redis = redis_from_url(settings.redis_url, decode_responses=True)
    log.info("api_started", brand=settings.brand_name, marzban_mock=settings.marzban_mock)
    yield
    await app.state.redis.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=f"{settings.brand_name} API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(plans.router)
    app.include_router(auth.router)
    app.include_router(orders.router)
    app.include_router(subscription.router)
    app.include_router(admin.router)

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "brand": settings.brand_name, "marzban_mock": settings.marzban_mock}

    return app


app = create_app()
