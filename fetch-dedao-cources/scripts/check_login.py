#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["websocket-client", "requests"]
# ///
"""验证调试 Chrome 中的得到登录态。用法: uv run check_login.py --work /tmp/dedao-fetch-work [--port 9223]"""
import argparse
import json
import time

import requests
import websocket


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/tmp/dedao-fetch-work")
    ap.add_argument("--port", type=int, default=9223)
    args = ap.parse_args()

    resp = requests.put(f"http://127.0.0.1:{args.port}/json/new?url=about:blank", timeout=10).json()
    ws = websocket.create_connection(
        resp["webSocketDebuggerUrl"].replace("127.0.0.1", "localhost"), timeout=30
    )
    mid = [0]

    def send(method, **params):
        mid[0] += 1
        ws.send(json.dumps({"id": mid[0], "method": method, "params": params}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == mid[0]:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    send("Page.enable")
    send("Page.navigate", url="https://www.dedao.cn/")
    time.sleep(6)
    r = send("Runtime.evaluate", expression="document.cookie", returnByValue=True)
    cookie = r.get("result", {}).get("value") or ""
    names = [c.split("=")[0].strip() for c in cookie.split(";") if "=" in c]
    print("cookie names:", names)
    if "token" in names and "csrfToken" in names:
        print("LOGIN OK")
        return 0
    print("LOGIN MISSING: 让用户先在本机 Chrome 登录 dedao.cn, 然后重新 setup_chrome.sh")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
