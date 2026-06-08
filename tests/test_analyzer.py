from datetime import date, timedelta

import pytest

from app.analysis.analyzer import analyze_quote, build_report
from app.models import Market, Opinion, PriceBar, StockQuote


def _make_quote(closes: list[float], market: Market = Market.US) -> StockQuote:
    base = date(2025, 1, 1)
    bars = [
        PriceBar(
            date=base + timedelta(days=i),
            open=c,
            high=c * 1.01,
            low=c * 0.99,
            close=c,
            volume=1_000_000,
        )
        for i, c in enumerate(closes)
    ]
    return StockQuote(symbol="TEST", name="Test Co", market=market, currency="USD", bars=bars)


def test_analyze_quote_returns_opinion():
    # 上涨趋势：价格逐步走高
    closes = [100 + i * 2 for i in range(30)]
    result = analyze_quote(_make_quote(closes))
    assert result.opinion in {Opinion.BUY, Opinion.HOLD, Opinion.SELL}
    assert result.ma5 > 0
    assert -100 < result.change_1d_pct < 100


def test_build_report_summary():
    quotes = [
        _make_quote([100 + i for i in range(25)], Market.US),
        _make_quote([50 + i * 0.5 for i in range(25)], Market.CN),
    ]
    report = build_report(quotes)
    assert len(report.analyses) == 2
    assert "共分析" in report.summary
    assert report.generated_at
