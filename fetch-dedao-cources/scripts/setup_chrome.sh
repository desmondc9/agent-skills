#!/usr/bin/env bash
# 启动复用登录态的调试 Chrome。用法: setup_chrome.sh [port] [work_dir]
# 注意: 必须在单独的 Bash 调用中执行(与其它命令混用时后台进程会被回收)。
set -euo pipefail

PORT="${1:-9223}"
WORK="${2:-/tmp/dedao-fetch-work}"
PROFILE="$WORK/chrome-profile"

if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "chrome already running on port $PORT"
  exit 0
fi

mkdir -p "$PROFILE/Default"
cp ~/.config/google-chrome/Default/Cookies "$PROFILE/Default/Cookies"
cp ~/.config/google-chrome/"Local State" "$PROFILE/Local State"

setsid nohup google-chrome \
  --headless=new \
  --remote-debugging-port="$PORT" \
  --remote-allow-origins='*' \
  --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check --disable-gpu \
  --window-size=1280,900 \
  > "$WORK/chrome.log" 2>&1 < /dev/null &

for i in $(seq 1 10); do
  sleep 1
  if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    curl -s "http://127.0.0.1:$PORT/json/version" | head -c 200
    echo
    echo "OK port=$PORT work=$WORK"
    exit 0
  fi
done
echo "FAILED to start chrome, see $WORK/chrome.log" >&2
exit 1
