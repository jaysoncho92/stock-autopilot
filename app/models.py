from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Market(str, Enum):
    US = "us"
    CN = "cn"
    HK = "hk"


class Opinion(str, Enum):
    BUY = "买入"
    HOLD = "持有"
    SELL = "卖出"


class PriceBar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class StockQuote(BaseModel):
    symbol: str
    name: str
    market: Market
    currency: str
    bars: list[PriceBar] = Field(min_length=1)


class StockAnalysis(BaseModel):
    symbol: str
    name: str
    market: Market
    last_close: float
    change_1d_pct: float
    change_5d_pct: float
    ma5: float
    ma20: float
    rsi14: float
    opinion: Opinion
    rationale: str


class MarketReport(BaseModel):
    generated_at: str
    analyses: list[StockAnalysis]
    summary: str
