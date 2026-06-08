"""定时任务运行器：每个交易日中午执行，输出当日 A股/港股主线数据报告。

流程：
  1. 判断今日是否交易日（非交易日直接跳过，自动避开周末/节假日）。
  2. 采集多市场数据，生成《数据简报》。
  3. 从题材词频自动识别当日主线题材，逐一下钻到个股层面。
  4. 写入 reports/主线报告_YYYYMMDD.md，并记录运行日志。

供 cron 调用（见 scripts/install_cron.sh）。也可手动运行：
    python scripts/run_daily.py            # 仅交易日执行
    python scripts/run_daily.py --force    # 忽略交易日判断，强制执行
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from market_data import collect, is_trading_day, beijing_today
from daily_briefing import build_brief
from stock_drilldown import collect_theme, build_md

# 题材词频里的「风格/复盘」噪声标签，不作为主线题材下钻
_STOP_TAGS = {
    "昨日涨停", "昨日连板", "昨日首板", "昨日涨停_含一字", "昨日连板_含一字",
    "昨日打二板以上表现", "炸板", "首板", "连板", "涨停", "打板",
    "央企", "国企", "高分红", "一季报增长", "一季报营收增长", "业绩增长",
    "ST板块", "ST", "次新股", "并购重组",
}

REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")


def pick_themes(theme_tags: dict, max_themes: int = 3) -> list[str]:
    """从题材词频中挑选实质性主线题材（过滤风格/复盘类噪声）。"""
    out = []
    for tag, _n in theme_tags.get("tags", []):
        if tag in _STOP_TAGS:
            continue
        out.append(tag)
        if len(out) >= max_themes:
            break
    return out


def log(msg: str) -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}] {msg}"
    print(line)
    with open(os.path.join(REPORT_DIR, "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--force", action="store_true", help="忽略交易日判断")
    ap.add_argument("--top", type=int, default=8, help="每个主线下钻个股数")
    args = ap.parse_args()

    day = beijing_today()
    if not args.force and not is_trading_day():
        log(f"{day} 非交易日（周末/节假日），跳过。")
        return 0

    log(f"{day} 开始执行：采集数据 + 主线下钻 …")
    data = collect(days=args.days)
    brief = build_brief(data)

    themes = pick_themes(data.get("theme_tags", {}))
    log(f"识别当日主线题材：{themes or '（无显著题材）'}")

    parts = [brief]
    if not themes:
        parts.append("\n\n# 主线个股下钻\n> 当日题材词频无显著主线。\n")
    for kw in themes:
        rows = collect_theme([kw], None, args.days, args.top)
        parts.append("\n\n" + build_md([kw], rows, args.days))

    parts.append("\n---\n*本报告为定时任务自动生成的数据底稿，主线研判与操作意见请结合 SKILL.md。"
                 "不构成投资建议。*\n")

    os.makedirs(REPORT_DIR, exist_ok=True)
    out_path = os.path.join(REPORT_DIR, f"主线报告_{day.replace('-', '')}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    log(f"完成，报告写入：{out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
