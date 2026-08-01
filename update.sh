#!/bin/bash
# 医疗设备招投标数据 - 一键更新（省网单入口，覆盖全省18市）
# 用法:
#   bash update.sh              ← 日常增量(近1周)
#   bash update.sh today        ← 仅今日
#   bash update.sh month        ← 全量刷新(近1月)
#
# 看板: https://wtrade2026.github.io/henan-medical-procurement/

set -e
cd "$(dirname "$0")"

MODE="${1:-week}"
case "$MODE" in
  today) TT="0"; LABEL="今日" ;;
  week)  TT="1"; LABEL="近1周" ;;
  month) TT="2"; LABEL="近1月" ;;
  *)     TT="1"; LABEL="近1周" ;;
esac

echo "========================================"
echo "医疗设备招投标 - 更新"
echo "时间范围: $LABEL | 覆盖: 全省18市"
echo "========================================"

# 1. 爬取
echo ""
echo "[1/3] 爬取全省数据(省网单入口)..."
PYTHONUNBUFFERED=1 python3 crawler_province.py "$TT"

# 2. 生成看板
echo ""
echo "[2/3] 生成看板..."
python3 build_dashboard.py

# 3. 推送
echo ""
echo "[3/3] 推送 GitHub..."
git add henan_medical_full.json docs/index.html crawler_province.py build_dashboard.py update.sh
git commit -m "数据更新 $(date '+%Y-%m-%d %H:%M') [$LABEL]" 2>/dev/null || echo "  (无变更)"
git push 2>&1 | tail -1

echo ""
echo "========================================"
echo "完成! $(date '+%H:%M')"
echo "https://wtrade2026.github.io/henan-medical-procurement/"
echo "========================================"
