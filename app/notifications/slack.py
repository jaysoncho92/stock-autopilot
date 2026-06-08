import logging

import httpx

from app.models import MarketReport

logger = logging.getLogger(__name__)

_MARKET_LABEL = {"us": "🇺🇸 美股", "cn": "🇨🇳 A股", "hk": "🇭🇰 港股"}


def format_slack_message(report: MarketReport) -> str:
    lines = [
        "*📊 Stock Autopilot 每日行情分析*",
        f"_生成时间 (UTC): {report.generated_at}_",
        "",
        f"*摘要*：{report.summary}",
        "",
    ]

    current_market = None
    for item in report.analyses:
        label = _MARKET_LABEL.get(item.market.value, item.market.value)
        if label != current_market:
            lines.extend(["", f"*{label}*"])
            current_market = label
        lines.append(
            f"• *{item.name}* (`{item.symbol}`) "
            f"收盘 {item.last_close} | 1D {item.change_1d_pct:+.2f}% | 5D {item.change_5d_pct:+.2f}% "
            f"| MA5/MA20 {item.ma5}/{item.ma20} | RSI {item.rsi14}\n"
            f"  *建议：{item.opinion.value}* — {item.rationale}"
        )

    lines.extend(["", "_免责声明：本报告仅供参考，不构成投资建议。_"])
    return "\n".join(lines)


async def send_slack_report(webhook_url: str, report: MarketReport) -> None:
    payload = {"text": format_slack_message(report)}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()
    logger.info("Slack 报告已推送，标的数量=%d", len(report.analyses))
