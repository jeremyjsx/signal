from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api"):
            api_key = request.headers.get("X-API-Key")
            if api_key != settings.api_key:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)