"""行情数据获取自检：A股 / 港股 / 美股 过去 N 天数据是否正常。

用法：
    python scripts/check_data.py            # 默认过去 5 天
    python scripts/check_data.py --days 5
"""

from __future__ import annotations

import argparse

from market_data import index_block, A_INDICES, HK_INDICES, US_INDICES


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=5)
    args = ap.parse_args()

    results = {
        "美股": check_market("美股 US", US_INDICES, args.days),
        "港股": check_market("港股 HK", HK_INDICES, args.days),
        "A股": check_market("A股 A-Share", A_INDICES, args.days),
    }
    print(f"\n{'='*72}\n汇总\n{'='*72}")
    for k, v in results.items():
        print(f"  {k}: {'✅ 正常' if v else '❌ 异常'}")
    print()


if __name__ == "__main__":
    main()
