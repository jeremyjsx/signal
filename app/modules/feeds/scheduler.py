import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session
from app.modules.feeds.models import JobRun
from app.modules.feeds.service import fetch_and_review_feeds

logger = logging.getLogger(__name__)


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
    lock_acquired = False
    async with async_session() as session:
        run = JobRun(job_name="fetch_feeds", status="running")
        session.add(run)
        await session.commit()
        await session.refresh(run)

        start = datetime.now()
        try:
            lock_acquired = bool(
                (
                    await session.execute(
                        text(
                            "SELECT pg_try_advisory_lock(:app_key, :job_key)"
                        ),
                        {
                            "app_key": settings.job_lock_app_key,
                            "job_key": settings.job_lock_fetch_feeds_key,
                        },
                    )
                ).scalar()
            )
            if not lock_acquired:
                run.status = "skipped"
                run.message = "Skipped because another instance is running the job."
                return

            new_articles = await fetch_and_review_feeds(session)
            run.status = "success"
            run.new_articles = new_articles
        except Exception as exc:
            run.status = "failed"
            run.message = str(exc)[:500]
            logger.exception("Failed running fetch_all_feeds_job")
        finally:
            if lock_acquired:
                await session.execute(
                    text("SELECT pg_advisory_unlock(:app_key, :job_key)"),
                    {
                        "app_key": settings.job_lock_app_key,
                        "job_key": settings.job_lock_fetch_feeds_key,
                    },
                )
            finished = datetime.now()
            run.finished_at = finished
            run.duration_ms = int((finished - start).total_seconds() * 1000)
            await session.commit()