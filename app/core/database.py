from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import database_uses_tls, settings


class Base(DeclarativeBase):
    pass


_engine_kwargs: dict[str, Any] = {"echo": settings.debug}
if database_uses_tls(settings.database_url, settings.database_ssl):
    _engine_kwargs["connect_args"] = {"ssl": True}

engine = create_async_engine(settings.database_url, **_engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
