# stock-autopilot

基于 **Python + FastAPI** 的定时行情分析与 Slack 推送服务。自动拉取**美股、A 股、港股**行情，生成技术分析报告与投资意见，并按计划推送到 Slack。

## 功能

- 定时任务（APScheduler + Cron）拉取多市场行情
- 简单技术分析：MA5/MA20、RSI、涨跌幅
- 生成买入 / 持有 / 卖出建议
- 通过 Slack Incoming Webhook 推送报告
- HTTP API：健康检查、手动触发、查看最新报告

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 SLACK_WEBHOOK_URL（可选）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook | 空（不推送） |
| `SCHEDULE_CRON` | Cron 五段表达式（UTC） | `0 18 * * 1-5` |
| `WATCHLIST_US` | 美股代码，逗号分隔 | `AAPL,MSFT,NVDA` |
| `WATCHLIST_CN` | A 股代码（6 位） | `600519,000001,300750` |
| `WATCHLIST_HK` | 港股代码 | `0700.HK,9988.HK,3690.HK` |

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/jobs/status` | 定时任务状态 |
| POST | `/jobs/run` | 立即执行一次分析任务 |
| GET | `/report/latest` | 最近一次报告 |

交互文档：http://localhost:8000/docs

## 测试

```bash
pytest -q
```

## 数据来源

- 美股 / 港股：[yfinance](https://github.com/ranaroussi/yfinance)
- A 股：[AKShare](https://github.com/akfamily/akshare)

> **免责声明**：本工具生成的分析仅供参考，不构成任何投资建议。
