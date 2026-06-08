from datetime import datetime, timezone

import numpy as np

from app.models import MarketReport, Opinion, StockAnalysis, StockQuote


def _rsi(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = gains[-period:].mean()
    avg_loss = losses[-period:].mean()
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return (current - previous) / previous * 100


def analyze_quote(quote: StockQuote) -> StockAnalysis:
    closes = np.array([bar.close for bar in quote.bars], dtype=float)
    last = float(closes[-1])
    prev = float(closes[-2]) if len(closes) >= 2 else last
    prev5 = float(closes[-6]) if len(closes) >= 6 else last

    ma5 = float(closes[-5:].mean()) if len(closes) >= 5 else last
    ma20 = float(closes[-20:].mean()) if len(closes) >= 20 else last
    rsi14 = _rsi(closes)

    change_1d = _pct_change(last, prev)
    change_5d = _pct_change(last, prev5)

    opinion, rationale = _derive_opinion(change_1d, change_5d, ma5, ma20, rsi14)

    return StockAnalysis(
        symbol=quote.symbol,
        name=quote.name,
        market=quote.market,
        last_close=round(last, 4),
        change_1d_pct=round(change_1d, 2),
        change_5d_pct=round(change_5d, 2),
        ma5=round(ma5, 4),
        ma20=round(ma20, 4),
        rsi14=round(rsi14, 2),
        opinion=opinion,
        rationale=rationale,
    )


def _derive_opinion(
    change_1d: float,
    change_5d: float,
    ma5: float,
    ma20: float,
    rsi14: float,
) -> tuple[Opinion, str]:
    bullish = ma5 > ma20 and change_5d > 0 and rsi14 < 70
    bearish = ma5 < ma20 and change_5d < 0 and rsi14 > 30

    if bullish and change_1d >= -1:
        return Opinion.BUY, "短期均线多头排列，5 日动量为正且 RSI 未过热，趋势偏多。"
    if bearish and change_1d <= 1:
        return Opinion.SELL, "短期均线空头排列，5 日动量为负且 RSI 未超卖，趋势偏空。"
    if rsi14 >= 75:
        return Opinion.SELL, "RSI 处于高位区域，短线追高风险较大，建议减仓或观望。"
    if rsi14 <= 25:
        return Opinion.BUY, "RSI 处于低位区域，可能存在超跌反弹机会，可小仓位关注。"
    return Opinion.HOLD, "趋势与动量信号不一致，建议持有观望，等待更明确方向。"


def build_report(quotes: list[StockQuote]) -> MarketReport:
    analyses = [analyze_quote(q) for q in quotes]
    buy = sum(1 for a in analyses if a.opinion == Opinion.BUY)
    sell = sum(1 for a in analyses if a.opinion == Opinion.SELL)
    hold = sum(1 for a in analyses if a.opinion == Opinion.HOLD)

    market_label = {"us": "美股", "cn": "A股", "hk": "港股"}
    by_market: dict[str, list[StockAnalysis]] = {}
    for a in analyses:
        by_market.setdefault(market_label[a.market.value], []).append(a)

    lines = [
        f"共分析 {len(analyses)} 只标的：买入 {buy} / 持有 {hold} / 卖出 {sell}。",
    ]
    for label, items in by_market.items():
        picks = "、".join(f"{i.name}({i.opinion.value})" for i in items[:5])
        lines.append(f"{label}：{picks}")

    return MarketReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        analyses=analyses,
        summary=" ".join(lines),
    )
