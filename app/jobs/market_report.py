import logging

from app.analysis.analyzer import build_report
from app.config import Settings, get_settings
from app.data import fetch_all_quotes
from app.models import MarketReport
from app.notifications.slack import send_slack_report

logger = logging.getLogger(__name__)

_last_report: MarketReport | None = None
_last_error: str | None = None


def get_last_report() -> MarketReport | None:
    return _last_report


def get_last_error() -> str | None:
    return _last_error


async def run_market_report_job(settings: Settings | None = None) -> MarketReport:
    global _last_report, _last_error

    cfg = settings or get_settings()
    logger.info("开始执行行情分析与报告任务")

    try:
        quotes = fetch_all_quotes(cfg.us_symbols(), cfg.cn_symbols(), cfg.hk_symbols())
        if not quotes:
            raise RuntimeError("未能拉取任何行情数据，请检查网络或关注列表配置")

        report = build_report(quotes)
        _last_report = report
        _last_error = None

        if cfg.slack_webhook_url:
            await send_slack_report(cfg.slack_webhook_url, report)
        else:
            logger.warning("未配置 SLACK_WEBHOOK_URL，报告仅保存在内存与 API 中")

        logger.info("任务完成：%s", report.summary)
        return report
    except Exception as exc:
        _last_error = str(exc)
        logger.exception("行情报告任务失败")
        raise
