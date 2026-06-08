#!/usr/bin/env bash
# 安装/更新定时任务：每个交易日（周一至周五）中午 12:00 执行主线分析。
# 节假日由 run_daily.py 内部的交易日判断自动跳过。
#
# 用法：
#   bash scripts/install_cron.sh            # 安装（默认 12:00）
#   HOUR=12 MINUTE=0 bash scripts/install_cron.sh
#   bash scripts/install_cron.sh --remove   # 卸载
#
# 说明：定时使用本机时区。若服务器为 UTC，请把 HOUR 设为 4（=北京12点）。

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
HOUR="${HOUR:-12}"
MINUTE="${MINUTE:-0}"
TAG="# stock-autopilot-daily"
RUNNER="$REPO_DIR/scripts/run_daily.py"

if [[ "${1:-}" == "--remove" ]]; then
  crontab -l 2>/dev/null | grep -v "$TAG" | crontab - || true
  echo "已移除定时任务。"
  exit 0
fi

# 周一至周五 HOUR:MINUTE 执行；cd 到仓库的 scripts 目录以保证相对导入与输出路径正确
CRON_LINE="$MINUTE $HOUR * * 1-5 cd '$REPO_DIR/scripts' && '$PY' run_daily.py >> '$REPO_DIR/reports/cron.out' 2>&1 $TAG"

# 幂等：先删旧的同 tag 行，再写入
( crontab -l 2>/dev/null | grep -v "$TAG" || true; echo "$CRON_LINE" ) | crontab -

echo "已安装定时任务（周一至周五 $HOUR:$(printf '%02d' "$MINUTE")，本机时区）："
crontab -l | grep "$TAG"
echo "提示：节假日会被 run_daily.py 自动跳过；报告输出到 $REPO_DIR/reports/。"
