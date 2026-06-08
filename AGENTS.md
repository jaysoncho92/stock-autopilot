# AGENTS.md

本仓库是 A股 / 港股「当日主线行情」分析技能（详见 `SKILL.md`）。核心命令：

```bash
pip install -r requirements.txt
python scripts/check_data.py --days 5         # 数据获取自检（指数+个股，三市场）
python scripts/run_daily.py                   # 交易日生成《主线报告》到 reports/
python scripts/run_daily.py --force           # 忽略交易日判断强制执行
```

- 仅依赖 `requests`。A股范围仅沪深两市，**不分析北交所**。
- `reports/` 为运行产物，已被 `.gitignore` 忽略。

## Cursor Cloud specific instructions

在 Cloud Agent / Automations 环境中执行本仓库定时任务时：

1. 依赖由 `.cursor/environment.json` 的 `install`（`pip install -r requirements.txt`）自动安装。
2. 若数据源需要凭证（本项目当前全部用公开零鉴权接口，无需 key），在 Dashboard → Cloud Agents → Secrets 配置后会注入为环境变量。
3. 执行入口固定为 `python scripts/run_daily.py`（内部已做交易日判断，非交易日会自动跳过、不产出报告）。
4. 报告生成在 `reports/主线报告_YYYYMMDD.md`；该目录被 gitignore，如需提交/开 PR，用 `git add -f` 强制加入对应报告文件。
5. 公开接口偶发风控/空响应，脚本已内置重试；如整段失败可重跑。

### 用于 Automation 的 Prompt（可直接粘贴）

> 在仓库根目录运行 `python scripts/run_daily.py`。
> - 若脚本日志显示「非交易日」，则今天不做任何事，直接结束。
> - 若成功生成 `reports/主线报告_YYYYMMDD.md`：用 `git add -f` 把该报告文件加入，提交到新分支并开一个 PR，标题为「主线报告 YYYY-MM-DD」，PR 描述里附上报告全文。
> - 若脚本报错：把关键错误日志贴出来，不要开 PR。
> 注意：A股只分析沪深两市，不涉及北交所；输出不构成投资建议。

### 调度（cron）

- 北京时间周一至周五 12:00。
- 若 Automation 调度界面可选时区 → 选 `Asia/Shanghai`，cron 填 `0 12 * * 1-5`。
- 若按 UTC → 填 `0 4 * * 1-5`（= 北京 12:00，工作日不错位）。
- cron 无法识别中国法定节假日，由 `run_daily.py` 的交易日判断兜底跳过。
