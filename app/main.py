from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.middleware import AuthMiddleware
from app.core.router import router as api_router
from app.modules.feeds.scheduler import create_scheduler
from app.modules.health.routes import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    register_middlewares(app)
    register_routes(app)

    return app


def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(AuthMiddleware)


def register_routes(app: FastAPI) -> None:
    app.include_router(api_router, prefix="/api")
    app.include_router(health_router)


app = create_app()
