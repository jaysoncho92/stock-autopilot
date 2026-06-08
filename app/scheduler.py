import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.jobs.market_report import run_market_report_job

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _parse_cron(expression: str) -> dict[str, str]:
    parts = expression.split()
    if len(parts) != 5:
        raise ValueError(f"无效的 cron 表达式（需要 5 段）: {expression}")
    minute, hour, day, month, day_of_week = parts
    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "day_of_week": day_of_week,
    }


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    settings = get_settings()
    _scheduler = AsyncIOScheduler()

    cron_kwargs = _parse_cron(settings.schedule_cron)
    _scheduler.add_job(
        run_market_report_job,
        trigger=CronTrigger(**cron_kwargs, timezone="UTC"),
        id="market_report",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("定时任务已启动，cron=%s", settings.schedule_cron)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("定时任务已停止")
