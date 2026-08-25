#!/usr/bin/env bash
# 收尾: 停止调试 Chrome 并删除含登录 Cookie 的 profile 副本。用法: teardown_chrome.sh [work_dir]
set -uo pipefail
WORK="${1:-/tmp/dedao-fetch-work}"

for p in $(pgrep -f "user-data-dir=$WORK/chrome-profile" 2>/dev/null); do
  kill -9 "$p" 2>/dev/null || true
done
sleep 1
rm -rf "$WORK/chrome-profile"
if pgrep -f "user-data-dir=$WORK/chrome-profile" >/dev/null 2>&1; then
  echo "WARN: chrome process still alive, kill manually"
  exit 1
fi
echo "chrome stopped, profile removed"
