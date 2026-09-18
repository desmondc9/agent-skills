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

# 选浏览器二进制: 优先 google-chrome; 没有则回退 Playwright Chromium(如 WSL 无桌面 Chrome)。
CHROME_BIN=""
if command -v google-chrome >/dev/null 2>&1; then
  CHROME_BIN="google-chrome"
else
  CHROME_BIN="$(ls -1 ~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | sort -V | tail -1 || true)"
fi
if [ -z "$CHROME_BIN" ]; then
  echo "FAILED: 未找到 google-chrome 或 Playwright Chromium(~/.cache/ms-playwright/)" >&2
  exit 1
fi

# 复制本机 Chrome 登录态; 源 Cookies 不存在(本机无已登录 Chrome)则启动空白 profile,
# 登录态改用 scripts/inject_cookies.py 注入(Get cookies.txt LOCALLY 导出的 cookies.txt)。
if [ -f ~/.config/google-chrome/Default/Cookies ]; then
  mkdir -p "$PROFILE/Default"
  cp ~/.config/google-chrome/Default/Cookies "$PROFILE/Default/Cookies"
  cp ~/.config/google-chrome/"Local State" "$PROFILE/Local State"
else
  mkdir -p "$PROFILE"
  echo "WARN: 无本机 Chrome 登录态可复制, 已启动空白 profile; 请用 uv run scripts/inject_cookies.py 注入登录态" >&2
fi

EXTRA_FLAGS=""
if [ "$CHROME_BIN" != "google-chrome" ]; then
  EXTRA_FLAGS="--no-sandbox"   # Playwright Chromium 需要
  echo "using playwright chromium: $CHROME_BIN"
fi

setsid nohup "$CHROME_BIN" \
  --headless=new \
  --remote-debugging-port="$PORT" \
  --remote-allow-origins='*' \
  --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check --disable-gpu \
  --window-size=1280,900 \
  $EXTRA_FLAGS \
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
