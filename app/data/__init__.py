from app.data.cn_market import fetch_cn_quotes
from app.data.hk_market import fetch_hk_quotes
from app.data.us_market import fetch_us_quotes
from app.models import StockQuote


def fetch_all_quotes(
    us_symbols: list[str],
    cn_symbols: list[str],
    hk_symbols: list[str],
) -> list[StockQuote]:
    quotes: list[StockQuote] = []
    quotes.extend(fetch_us_quotes(us_symbols))
    quotes.extend(fetch_cn_quotes(cn_symbols))
    quotes.extend(fetch_hk_quotes(hk_symbols))
    return quotes
