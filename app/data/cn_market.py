import logging

import akshare as ak
import pandas as pd

from app.data._utils import retry_call
from app.models import Market, PriceBar, StockQuote

logger = logging.getLogger(__name__)

_CN_NAME_CACHE: dict[str, str] = {}


def _load_cn_name(symbol: str) -> str:
    if symbol in _CN_NAME_CACHE:
        return _CN_NAME_CACHE[symbol]
    try:
        spot = ak.stock_zh_a_spot_em()
        row = spot.loc[spot["代码"] == symbol]
        if not row.empty:
            name = str(row.iloc[0]["名称"])
            _CN_NAME_CACHE[symbol] = name
            return name
    except Exception:
        logger.debug("无法获取 A 股名称 %s", symbol, exc_info=True)
    return symbol


def fetch_cn_quotes(symbols: list[str]) -> list[StockQuote]:
    quotes: list[StockQuote] = []
    for symbol in symbols:
        try:
            df = retry_call(
                lambda s=symbol: ak.stock_zh_a_hist(symbol=s, period="daily", adjust="qfq"),
                attempts=3,
                delay_seconds=3.0,
            )
            if df is None or df.empty:
                logger.warning("A 股 %s 无历史数据", symbol)
                continue

            bars: list[PriceBar] = []
            for _, row in df.tail(90).iterrows():
                bars.append(
                    PriceBar(
                        date=pd.to_datetime(row["日期"]).date(),
                        open=float(row["开盘"]),
                        high=float(row["最高"]),
                        low=float(row["最低"]),
                        close=float(row["收盘"]),
                        volume=float(row.get("成交量", 0) or 0),
                    )
                )

            quotes.append(
                StockQuote(
                    symbol=symbol,
                    name=_load_cn_name(symbol),
                    market=Market.CN,
                    currency="CNY",
                    bars=bars,
                )
            )
        except Exception:
            logger.exception("拉取 A 股 %s 失败", symbol)
    return quotes
