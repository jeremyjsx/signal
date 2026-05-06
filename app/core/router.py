from fastapi import APIRouter

from app.modules.articles.routes import router as articles_router
from app.modules.feeds.routes import router as feeds_router

router = APIRouter()

router.include_router(feeds_router)
router.include_router(articles_router)
