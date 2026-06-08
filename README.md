# stock-autopilot

A股 / 港股「当日主线行情」分析技能（AI Skill）。结合过去数日 **美股、港股、A股** 的走势，研判当日 A股与港股的主线题材与大盘方向，产出一份**具备可操作性的分析报告**（含趋势判断、主线归因、市场情绪、北向资金，以及明确的仓位 / 方向 / 风控操作意见）。

> ⚠️ 本项目仅做公开数据整理与逻辑推演，**不构成投资建议**，据此操作盈亏自负。

## 组成

| 文件 | 作用 |
|------|------|
| `SKILL.md` | 技能主体：何时激活、数据源、**分析方法论**、报告模板、操作意见框架、免责声明 |
| `scripts/market_data.py` | 自包含数据采集模块（指数 / 个股 / 板块 / 涨停池 / 题材 / 北向），仅依赖 `requests` |
| `scripts/daily_briefing.py` | 把采集数据整理成《多市场行情数据简报》(Markdown) |
| `scripts/check_data.py` | 数据获取自检（指数 + 个股，A/港/美 三市场） |

数据获取方案参考：
[a-stock-data](https://github.com/simonlin1212/a-stock-data) ·
[global-stock-data](https://github.com/simonlin1212/global-stock-data)

## 安装

```bash
pip install requests          # 唯一硬依赖
```

将 `SKILL.md` 放入 AI 助手的技能目录（如 `~/.claude/skills/a-hk-daily-briefing/SKILL.md`），即可在 A股 / 港股相关对话中自动激活。

## 用法

```bash
# 数据获取自检（指数 + 个股，三市场，近5个交易日）
python scripts/check_data.py --days 5
python scripts/check_data.py --stocks            # 只测个股

# 生成当日多市场数据简报（分析报告的数据底稿）
python scripts/daily_briefing.py --days 5
python scripts/daily_briefing.py --days 5 --date 20260608 --out brief.md
```

拿到《数据简报》后，AI 按 `SKILL.md` 的方法论研判主线、套用报告模板，产出最终分析报告与操作意见。

## 数据源（全部公开、零鉴权）

| 维度 | 数据源 |
|------|--------|
| 三市场指数 / 个股 实时 | 腾讯财经 `qt.gtimg.cn` |
| 指数 / 个股 N 日日K | 腾讯日K(A/港) · Yahoo(美) · 东财(北证50) |
| 行业 / 概念板块排名 | 东方财富 push2 `clist` |
| 涨停 / 跌停池 | 东方财富 `push2ex` |
| 当日题材归因 | 同花顺 `getharden` |
| 北向资金 | 同花顺 `hsgtApi` |

### 已知数据局限

- 北交所**个股历史K线**在免费接口缺失（实时正常）。
- 北向资金某腿偶发上游断供，脚本会自动剔除并标记「数据异常」。
- 公开接口可能延时 / 偶发风控（连接重置），重试或更换网络即可。
