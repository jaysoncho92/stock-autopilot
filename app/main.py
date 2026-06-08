import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app import __version__
from app.config import get_settings
from app.jobs.market_report import get_last_error, get_last_report, run_market_report_job
from app.models import MarketReport
from app.scheduler import get_scheduler, shutdown_scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="Stock Autopilot",
    description="定时拉取美股/A股/港股行情，生成分析报告并通过 Slack 推送",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    scheduler = get_scheduler()
    return {
        "status": "ok",
        "version": __version__,
        "scheduler_running": scheduler is not None and scheduler.running,
        "slack_configured": bool(get_settings().slack_webhook_url),
    }


@app.get("/report/latest", response_model=MarketReport | None)
async def latest_report() -> MarketReport | None:
    return get_last_report()


@app.post("/jobs/run", response_model=MarketReport)
async def trigger_report_job() -> MarketReport:
    try:
        return await run_market_report_job()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/jobs/status")
async def job_status() -> dict:
    scheduler = get_scheduler()
    job = scheduler.get_job("market_report") if scheduler else None
    return {
        "last_report_at": get_last_report().generated_at if get_last_report() else None,
        "last_error": get_last_error(),
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "schedule_cron": get_settings().schedule_cron,
    }
