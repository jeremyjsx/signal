from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import async_session
from app.modules.feeds.service import fetch_and_review_feeds


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    
    scheduler.add_job(
        fetch_all_feeds_job,
        trigger=IntervalTrigger(hours=settings.fetch_interval_hours),
        id="fetch_feeds",
        replace_existing=True,
    )
    
    return scheduler


async def fetch_all_feeds_job():
    async with async_session() as session:
        await fetch_and_review_feeds(session)