# stock-autopilot

A股 / 港股「当日主线行情」分析技能（AI Skill）。结合过去数日 **美股、港股、A股** 的走势，研判当日 A股与港股的主线题材与大盘方向，产出一份**具备可操作性的分析报告**（含趋势判断、主线归因、市场情绪、北向资金，以及明确的仓位 / 方向 / 风控操作意见）。

> ⚠️ 本项目仅做公开数据整理与逻辑推演，**不构成投资建议**，据此操作盈亏自负。

## 组成

| 文件 | 作用 |
|------|------|
| `SKILL.md` | 技能主体：何时激活、数据源、**分析方法论**、报告模板、操作意见框架、免责声明 |
| `scripts/market_data.py` | 自包含数据采集模块（指数 / 个股 / 板块 / 涨停池 / 题材 / 北向），仅依赖 `requests` |
| `scripts/daily_briefing.py` | 把采集数据整理成《多市场行情数据简报》(Markdown) |
| `scripts/stock_drilldown.py` | 主线题材 → 个股下钻（成分龙头 + 实时/近N日/主力资金流） |
| `scripts/run_daily.py` | 定时任务运行器（交易日自动取数+识别主线+下钻，输出 `reports/`） |
| `scripts/install_cron.sh` | 安装/卸载定时任务（每个交易日 12:00） |
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

# 主线 → 个股下钻
python scripts/stock_drilldown.py --theme 机器人,具身智能 --top 8

# 定时任务（方式一：本机 cron）：每个交易日 12:00 自动执行（节假日自动跳过）
bash scripts/install_cron.sh            # 本机时区 12:00
HOUR=4 bash scripts/install_cron.sh     # 服务器为 UTC 时设为 4（=北京12点）
python scripts/run_daily.py --force     # 手动跑一次
```

拿到《数据简报》/《主线报告》后，AI 按 `SKILL.md` 的方法论研判主线、套用报告模板，产出最终分析报告与操作意见。

## 定时任务（方式二：Cursor Automations）

[Cursor Automations](https://cursor.com/docs/cloud-agent/automations) 本质是「定时拉起一个 Cloud Agent，按 prompt 干活」，运行在会读取本仓库 `.cursor/environment.json` 的 Cloud VM 上。本仓库已内置 `.cursor/environment.json`（自动 `pip install -r requirements.txt`）与 `AGENTS.md`（含云端运行说明 + 可直接粘贴的 prompt）。

配置步骤：

1. 打开 [cursor.com/automations](https://cursor.com/automations) 新建 Automation。
2. **Trigger** 选 Scheduled，填 cron：
   - 界面可选时区 → 选 `Asia/Shanghai`，cron `0 12 * * 1-5`（周一至周五12:00）。
   - 按 UTC → 填 `0 4 * * 1-5`（= 北京12:00，工作日不错位）。
3. **Repository** 选本仓库 + 目标分支。
4. **Prompt** 粘贴 `AGENTS.md` 里「用于 Automation 的 Prompt」。
5. **Tools** 启用 `Open pull request`（产出报告开 PR）；如需推送可启用 `Send to Slack`。
6. 创建后手动触发一次，确认时区与脚本正常。

> 说明：① cron 只能做到「工作日」，中国法定节假日由 `run_daily.py` 的交易日判断自动跳过；② Automation 以 Cloud Agent（Max Mode）运行，按用量计费；若只想确定性跑脚本，本机 cron / GitHub Actions 更轻量。

## 数据源（全部公开、零鉴权）

| 维度 | 数据源 |
|------|--------|
| 三市场指数 / 个股 实时 | 腾讯财经 `qt.gtimg.cn` |
| 指数 / 个股 N 日日K | 腾讯日K(A/港) · Yahoo(美) |
| 行业 / 概念板块排名 | 东方财富 push2 `clist` |
| 涨停 / 跌停池 | 东方财富 `push2ex` |
| 当日题材归因 | 同花顺 `getharden` |
| 北向资金 | 同花顺 `hsgtApi` |

### 范围与数据局限

- **不覆盖北交所**：A股仅分析沪深两市（主板 / 创业板 / 科创板），不纳入北交所指数与个股。
- 北向资金某腿偶发上游断供，脚本会自动剔除并标记「数据异常」。
- 公开接口可能延时 / 偶发风控（连接重置），脚本已内置重试。
