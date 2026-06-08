# AGENTS.md

## Cursor Cloud specific instructions

### 服务概览

单进程 **FastAPI** 应用，内置 **APScheduler** 定时任务，无需额外数据库或 Redis。

| 服务 | 端口 | 启动命令 |
|------|------|----------|
| API + 调度器 | 8000 | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |

开发模式加 `--reload`。服务启动后调度器自动运行；也可 `POST /jobs/run` 手动触发。

### 依赖安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 环境变量

复制 `.env.example` 为 `.env`。`SLACK_WEBHOOK_URL` 未配置时任务仍会拉取行情并生成报告，但不会推送 Slack。

### 测试与 lint

```bash
source .venv/bin/activate
pytest -q
```

项目未配置 ruff/mypy；以 pytest 为准。

### 注意事项

- 行情拉取依赖外网（yfinance、AKShare）；Cloud VM 需能访问相关数据源。
- A 股名称查询会调用 `ak.stock_zh_a_spot_em()`，首次较慢。
- Cron 表达式使用 **UTC** 时区。
- **不要**在 VM update 脚本中启动 uvicorn；每次会话按需手动启动。
