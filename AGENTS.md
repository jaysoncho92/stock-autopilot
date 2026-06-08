# AGENTS.md

## Cursor Cloud specific instructions

### 仓库现状

`stock-autopilot` 目前是一个**空脚手架仓库**：除 `README.md`（仅含标题）外，没有应用源码、依赖清单、Docker/CI 配置或启动脚本。

### 服务与运行

| 服务 | 状态 |
|------|------|
| 应用 / API / 前端 | 未定义，无法启动 |
| 数据库 / 缓存 / 队列 | 未定义 |

在添加 `package.json`、`pyproject.toml`、`docker-compose.yml` 等之前，**无法**执行 lint、测试或 dev server。

### VM 已具备的工具

云 VM 已预装常用开发工具，例如：

- Node.js（nvm，`pnpm` / `npm` 可用）
- Python 3.12（`pip` 可用）

具体版本以当前 VM 为准：`node --version`、`python3 --version`。

### 有代码后的典型流程（待项目定义）

README 或贡献指南出现依赖说明后，按项目约定执行，例如：

- Node：`pnpm install` → `pnpm dev` / `pnpm lint` / `pnpm test`
- Python：`pip install -r requirements.txt` 或 `uv sync` → 按 README 启动

**不要**在 update 脚本中加入 `docker compose up`、`pnpm dev` 等服务启动命令；服务应在每次会话中按需手动启动。

### 分支与远程

默认分支为 `main`，远程：`https://github.com/jaysoncho92/stock-autopilot`。
