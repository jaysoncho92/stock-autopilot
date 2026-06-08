"""主线题材 → 个股下钻。

把某条主线（如「机器人/具身智能」）下钻到成分龙头个股，并拉取每只个股的
实时行情、近 N 日累计涨跌、主力资金流，整理成 Markdown 表，供分析报告引用。

用法：
    python scripts/stock_drilldown.py --theme 机器人
    python scripts/stock_drilldown.py --theme 机器人,具身智能,人形机器人 --top 8 --days 5
    python scripts/stock_drilldown.py --theme AI --date 20260608 --out drill.md
"""

from __future__ import annotations

import argparse

from market_data import theme_stocks, stock_quote, stock_history, stock_fundflow


def _cum_pct(hist: list[dict]) -> float | None:
    """近 N 日累计涨跌幅（首日开口 → 末日收盘）。"""
    if len(hist) < 2:
        return None
    first, last = hist[0]["close"], hist[-1]["close"]
    return round((last / first - 1) * 100, 2) if first else None


def collect_theme(keywords: list[str], date: str | None, days: int, top: int) -> list[dict]:
    """按多个关键词并集定位个股，逐只补充实时/历史/资金流，按当日涨幅取前 top 只。"""
    seen: dict[str, dict] = {}
    for kw in keywords:
        for s in theme_stocks(kw, date):
            seen.setdefault(s["code"], s)

    enriched = []
    for s in seen.values():
        code = s["code"]
        q = stock_quote(code, "a")
        hist, ff = [], {}
        try:
            hist = stock_history(code, "a", days)
        except Exception:  # noqa: BLE001
            pass
        try:
            ff = stock_fundflow(code, days)
        except Exception:  # noqa: BLE001
            ff = {}
        enriched.append({
            "code": code, "name": s["name"],
            "price": q.get("price"),
            "change_pct": q.get("change_pct"),
            "cum_pct": _cum_pct(hist),
            "main_sum_yi": ff.get("main_sum_yi"),
            "reason": s["reason"],
        })

    enriched.sort(key=lambda r: r["change_pct"] if r["change_pct"] is not None else -999,
                  reverse=True)
    return enriched[:top]


def build_md(keywords: list[str], rows: list[dict], days: int) -> str:
    md = [f"# 主线个股下钻：{' / '.join(keywords)}\n"]
    if not rows:
        md.append("> 当日强势股中未匹配到该题材个股。\n")
        return "\n".join(md)
    md.append(f"| 代码 | 名称 | 现价 | 当日% | 近{days}日累计% | 近{days}日主力净流入(亿) | 题材归因 |")
    md.append("|------|------|------|-------|-----------|------------------|----------|")
    for r in rows:
        cp = f"{r['change_pct']:+.2f}%" if r["change_pct"] is not None else "—"
        cum = f"{r['cum_pct']:+.2f}%" if r["cum_pct"] is not None else "—"
        ms = f"{r['main_sum_yi']:+.2f}" if r["main_sum_yi"] is not None else "—"
        md.append(f"| {r['code']} | {r['name']} | {r['price']} | {cp} | {cum} | {ms} | {r['reason']} |")
    md.append("\n> 主力净流入为正且涨幅居前 = 资金共振、强度高；涨幅高但主力净流出 = 谨防分歧。")
    md.append("\n> 个股历史/资金流仅沪深A股；更深维度(龙虎榜/研报/股东户数)见 a-stock-data 工具包。")
    md.append("\n*仅为数据汇总，不构成投资建议。*\n")
    return "\n".join(md)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True, help="题材关键词，逗号分隔可多选")
    ap.add_argument("--date", default=None, help="YYYYMMDD，默认今天")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    keywords = [k.strip() for k in args.theme.split(",") if k.strip()]
    date = args.date if not args.date else f"{args.date[:4]}-{args.date[4:6]}-{args.date[6:8]}"
    rows = collect_theme(keywords, date, args.days, args.top)
    md = build_md(keywords, rows, args.days)
    print(md)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n[已写入 {args.out}]")


if __name__ == "__main__":
    main()
