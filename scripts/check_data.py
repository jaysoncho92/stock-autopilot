"""行情数据获取自检：A股 / 港股 / 美股 过去 N 天数据是否正常。

用法：
    python scripts/check_data.py            # 默认过去 5 天
    python scripts/check_data.py --days 5
"""

from __future__ import annotations

import argparse

from market_data import (index_block, stock_quote, stock_history,
                         A_INDICES, HK_INDICES, US_INDICES)

# 个股自检样本（每个市场几只代表性标的）
SAMPLE_STOCKS = {
    "A股": ("a", [("600519", "贵州茅台"), ("000858", "五粮液"), ("300750", "宁德时代")]),
    "港股": ("hk", [("00700", "腾讯控股"), ("09988", "阿里巴巴-W"), ("03690", "美团-W")]),
    "美股": ("us", [("AAPL", "苹果"), ("TSLA", "特斯拉"), ("NVDA", "英伟达")]),
}


def _fmt_hist(hist: list[dict]) -> str:
    if not hist:
        return "（无历史，仅实时）"
    parts = [f"{h['date']} {h['close']}({h.get('change_pct', 0):+.2f}%)" for h in hist]
    return " | ".join(parts)


def check_market(label: str, indices: list[dict], days: int) -> bool:
    print(f"\n{'='*72}\n【{label}】过去 {days} 个交易日\n{'='*72}")
    block = index_block(indices, days)
    ok = True
    for rec in block:
        rt = rec.get("realtime")
        rt_str = (f"实时 {rt['price']} ({rt['change_pct']:+.2f}%)" if rt else "实时 N/A")
        n = len(rec.get("history") or [])
        status = "OK " if (rt or n > 0) else "FAIL"
        if not (rt or n > 0):
            ok = False
        print(f"[{status}] {rec['name']:<16} {rt_str:<24} 历史{n}天")
        if rec.get("history"):
            print(f"        {_fmt_hist(rec['history'])}")
        if rec.get("history_error"):
            print(f"        history_error: {rec['history_error']}")
    return ok


def check_stocks(days: int) -> dict[str, bool]:
    print(f"\n{'#'*72}\n个股行情自检（实时 + 近 {days} 日历史）\n{'#'*72}")
    results = {}
    for label, (market, stocks) in SAMPLE_STOCKS.items():
        print(f"\n【{label} 个股】")
        ok = True
        for code, name in stocks:
            q = stock_quote(code, market)
            try:
                hist = stock_history(code, market, days)
            except Exception as e:  # noqa: BLE001
                hist = []
                print(f"        history_error {code}: {repr(e)[:60]}")
            n = len(hist)
            good = bool(q) and n > 0
            ok = ok and good
            price = f"{q.get('price')}({q.get('change_pct', 0):+.2f}%)" if q else "N/A"
            print(f"  [{'OK ' if good else 'FAIL'}] {name:<14}{code:<8} 实时 {price:<20} 历史{n}天")
        results[label] = ok
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--stocks", action="store_true", help="只测个股")
    args = ap.parse_args()

    results: dict[str, bool] = {}
    if not args.stocks:
        results["美股指数"] = check_market("美股 US 指数", US_INDICES, args.days)
        results["港股指数"] = check_market("港股 HK 指数", HK_INDICES, args.days)
        results["A股指数"] = check_market("A股 指数", A_INDICES, args.days)

    stock_res = check_stocks(args.days)
    results.update({f"{k}个股": v for k, v in stock_res.items()})

    print(f"\n{'='*72}\n汇总\n{'='*72}")
    for k, v in results.items():
        print(f"  {k}: {'✅ 正常' if v else '❌ 异常'}")
    print()


if __name__ == "__main__":
    main()
