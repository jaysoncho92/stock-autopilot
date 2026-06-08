import logging

import yfinance as yf

from app.data._utils import bars_from_dataframe
from app.models import Market, StockQuote

logger = logging.getLogger(__name__)


def fetch_hk_quotes(symbols: list[str]) -> list[StockQuote]:
    quotes: list[StockQuote] = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3mo", auto_adjust=True)
            bars = bars_from_dataframe(hist)
            if not bars:
                logger.warning("港股 %s 无历史数据", symbol)
                continue
            info = ticker.info or {}
            name = info.get("shortName") or info.get("longName") or symbol
            quotes.append(
                StockQuote(
                    symbol=symbol,
                    name=name,
                    market=Market.HK,
                    currency=str(info.get("currency", "HKD")),
                    bars=bars,
                )
            )
        except Exception:
            logger.exception("拉取港股 %s 失败", symbol)
    return quotes
