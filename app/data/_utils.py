import logging
import time
from collections.abc import Callable
from datetime import date
from typing import TypeVar

import pandas as pd

from app.models import PriceBar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_call(fn: Callable[[], T], *, attempts: int = 3, delay_seconds: float = 2.0) -> T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                wait = delay_seconds * attempt
                logger.warning("请求失败，%ss 后重试 (%d/%d): %s", wait, attempt, attempts, exc)
                time.sleep(wait)
    assert last_error is not None
    raise last_error


def bars_from_dataframe(df: pd.DataFrame) -> list[PriceBar]:
    """将 OHLCV DataFrame 转为 PriceBar 列表（按日期升序）。"""
    if df.empty:
        return []

    normalized = df.copy()
    if not isinstance(normalized.index, pd.DatetimeIndex):
        if "date" in normalized.columns:
            normalized["date"] = pd.to_datetime(normalized["date"])
            normalized = normalized.set_index("date")
        else:
            normalized.index = pd.to_datetime(normalized.index)

    normalized = normalized.sort_index()

    bars: list[PriceBar] = []
    for idx, row in normalized.iterrows():
        bars.append(
            PriceBar(
                date=idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10]),
                open=float(row["Open"] if "Open" in row else row["open"]),
                high=float(row["High"] if "High" in row else row["high"]),
                low=float(row["Low"] if "Low" in row else row["low"]),
                close=float(row["Close"] if "Close" in row else row["close"]),
                volume=float(row.get("Volume", row.get("volume", 0)) or 0),
            )
        )
    return bars
