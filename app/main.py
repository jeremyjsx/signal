from fastapi import FastAPI

from app.core.config import settings
from app.core.middleware import AuthMiddleware
from app.core.router import router as api_router
from app.modules.health.routes import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
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
