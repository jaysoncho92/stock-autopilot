"""把采集到的多市场数据整理成一份结构化「数据简报」(Markdown)。

这是分析报告的【确定性数据层】：脚本只负责客观取数与排版，
主线研判 / 操作意见由 SKILL.md 指导上层 AI 基于本简报完成。

用法：
    python scripts/daily_briefing.py                 # 今天，过去5天
    python scripts/daily_briefing.py --days 5 --date 20260608
    python scripts/daily_briefing.py --out brief.md   # 同时写入文件
"""

from __future__ import annotations

import argparse

from market_data import collect


def _trend_line(hist: list[dict]) -> str:
    if not hist:
        return "—"
    return " → ".join(f"{h.get('change_pct', 0):+.2f}%" for h in hist)


def _index_table(block: list[dict]) -> str:
    if isinstance(block, dict) and block.get("error"):
        return f"> 取数失败：{block['error']}\n"
    lines = ["| 指数 | 最新 | 当日% | 近N日涨跌幅(每日) |",
             "|------|------|-------|------------------|"]
    for rec in block:
        rt = rec.get("realtime") or {}
        price = rt.get("price", "—")
        chg = f"{rt.get('change_pct', 0):+.2f}%" if rt else "—"
        # 若无实时（如金龙中国代理），用历史最后一日补位
        hist = rec.get("history") or []
        if not rt and hist:
            price = hist[-1]["close"]
            chg = f"{hist[-1].get('change_pct', 0):+.2f}%"
        lines.append(f"| {rec['name']} | {price} | {chg} | {_trend_line(hist)} |")
    return "\n".join(lines) + "\n"


def _boards_section(title: str, boards: dict) -> str:
    if isinstance(boards, dict) and boards.get("error"):
        return f"### {title}\n> 取数失败：{boards['error']}\n"
    top = "、".join(f"{b['name']}({b['change_pct']:+.2f}%)" for b in boards.get("top", [])[:8])
    bot = "、".join(f"{b['name']}({b['change_pct']:+.2f}%)" for b in boards.get("bottom", [])[:5])
    return (f"### {title}（共{boards.get('total', 0)}个）\n"
            f"- 领涨：{top}\n"
            f"- 领跌：{bot}\n")


def build_brief(data: dict) -> str:
    days = data.get("lookback_days", 5)
    md: list[str] = []
    md.append(f"# 多市场行情数据简报\n")
    md.append(f"> 生成时间：{data.get('generated_at')} ｜ 回看窗口：近 {days} 个交易日\n")
    md.append("> 数据源：腾讯财经 / 东方财富 / 同花顺 / Yahoo Finance（公开接口，可能有延时）\n")

    md.append("\n## 一、隔夜外盘（美股）\n")
    md.append(_index_table(data.get("us", [])))
    md.append("\n## 二、港股\n")
    md.append(_index_table(data.get("hk", [])))
    md.append("\n## 三、A股大盘\n")
    md.append(_index_table(data.get("a", [])))

    md.append("\n## 四、A股板块表现（当日）\n")
    md.append(_boards_section("行业板块", data.get("industry_boards", {})))
    md.append(_boards_section("概念板块", data.get("concept_boards", {})))

    md.append("\n## 五、市场情绪（涨停 / 跌停）\n")
    lp = data.get("limit_pool", {})
    if lp.get("error"):
        md.append(f"> 取数失败：{lp['error']}\n")
    else:
        md.append(f"- 交易日：{lp.get('date')}｜涨停 **{lp.get('zt_count')}** 家 / 跌停 **{lp.get('dt_count')}** 家"
                  f"｜最高连板 **{lp.get('max_lb')}** 板\n")
        lb = "、".join(f"{k}板×{v}" for k, v in (lp.get("lb_dist") or {}).items())
        md.append(f"- 连板分布：{lb}\n")
        ind = "、".join(f"{k}({v})" for k, v in (lp.get("industry_dist") or {}).items())
        md.append(f"- 涨停行业分布：{ind}\n")
        dragons = "、".join(f"{d['name']}({d['lbc']}板/{d['industry']})" for d in (lp.get("dragons") or []))
        md.append(f"- 高度板梯队：{dragons}\n")

    md.append("\n## 六、当日主线题材（同花顺强势股归因词频）\n")
    tt = data.get("theme_tags", {})
    if tt.get("error"):
        md.append(f"> 取数失败：{tt['error']}\n")
    else:
        md.append(f"- 强势股样本：{tt.get('count')} 只\n")
        tags = "、".join(f"{t}×{n}" for t, n in (tt.get("tags") or []))
        md.append(f"- 题材热度TOP：{tags}\n")

    md.append("\n## 七、北向资金（同花顺口径，当日累计净买入，单位亿元）\n")
    nb = data.get("northbound", {})
    if nb.get("error"):
        md.append(f"> 取数失败：{nb['error']}\n")
    else:
        hgt = nb.get("hgt_yi")
        sgt = nb.get("sgt_yi")
        total = nb.get("total_yi")
        hgt_s = f"{hgt}" if hgt is not None else "数据异常"
        sgt_s = f"{sgt}" if sgt is not None else "数据异常"
        total_s = f"**{total}**" if total is not None else "（单腿缺失，不汇总）"
        if hgt is None and sgt is None:
            md.append("> 当日暂无有效北向数据（上游可能未更新或停止披露净额）\n")
        else:
            md.append(f"- 沪股通 {hgt_s} ｜ 深股通 {sgt_s} ｜ 合计 {total_s}\n")
            md.append("> 注：北向净额由同花顺口径分钟序列收盘值估算；某腿显示「数据异常」表示上游序列残缺，已自动剔除。\n")

    md.append("\n---\n*本简报仅为客观数据汇总，不构成投资建议。主线研判与操作意见见分析报告。*\n")
    return "\n".join(md)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--date", default=None, help="YYYYMMDD，默认今天")
    ap.add_argument("--out", default=None, help="额外写入的 Markdown 文件路径")
    args = ap.parse_args()

    data = collect(days=args.days, date=args.date)
    brief = build_brief(data)
    print(brief)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(brief)
        print(f"\n[已写入 {args.out}]")


if __name__ == "__main__":
    main()
