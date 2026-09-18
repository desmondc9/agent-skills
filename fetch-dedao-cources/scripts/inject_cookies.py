#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["websocket-client", "requests"]
# ///
"""登录态兜底: 注入 Netscape cookies.txt(如 Chrome 扩展 Get cookies.txt LOCALLY 导出)中的
得到相关 cookie 到调试 Chrome, 并验证登录成功。适用于本机无已登录 Chrome / 扫码二维码无法
展示(WSL 无图片查看器等)的场景。

用法: uv run inject_cookies.py [--cookies ~/.cookie_contexts/cookies.txt] [--port 9223]
"""
import argparse
import json
import time

import requests
import websocket

DEFAULT_COOKIE_FILE = "~/.cookie_contexts/cookies.txt"
DOMAIN_PAT = ("dedao", "umiwi", "luojisiwei")


def load_cookies(path, domains):
    """解析 Netscape cookies.txt, 按 (domain, path, name) 去重, 只保留 domains 匹配条目。"""
    import os
    path = os.path.expanduser(path)
    out, seen = [], set()
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 7:  # 空格分隔的导出变体
                parts = line.split()
                if len(parts) < 7:
                    continue
                parts = parts[:6] + [" ".join(parts[6:])]
            domain, flag, cookie_path, secure, expiry, name, value = parts
            if not any(d in domain for d in domains):
                continue
            key = (domain, cookie_path, name)
            if key in seen:
                continue
            seen.add(key)
            out.append({"domain": domain, "flag": flag.upper() == "TRUE",
                        "path": cookie_path, "secure": secure.upper() == "TRUE",
                        "expiry": expiry, "name": name, "value": value})
    return path, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cookies", default=DEFAULT_COOKIE_FILE,
                    help=f"Netscape cookies.txt 路径 (默认 {DEFAULT_COOKIE_FILE})")
    ap.add_argument("--port", type=int, default=9223)
    ap.add_argument("--domains", default=",".join(DOMAIN_PAT),
                    help="逗号分隔的域名过滤关键字 (默认 dedao,umiwi,luojisiwei)")
    args = ap.parse_args()

    path, cookies = load_cookies(args.cookies, args.domains.split(","))
    names = sorted({c["name"] for c in cookies})
    print(f"loaded {len(cookies)} cookies from {path}: {names}")
    if not any("token" == n for n in names):
        print("WARN: 未发现 token cookie, 导出前请确认已在浏览器登录 www.dedao.cn")

    resp = requests.put(f"http://127.0.0.1:{args.port}/json/new?url=about:blank", timeout=10).json()
    ws = websocket.create_connection(
        resp["webSocketDebuggerUrl"].replace("127.0.0.1", "localhost"), timeout=60
    )
    mid = 0

    def send(method, **params):
        nonlocal mid
        mid += 1
        ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    send("Network.enable")
    ok = 0
    for c in cookies:
        params = {"name": c["name"], "value": c["value"], "path": c["path"] or "/"}
        if c["domain"].startswith("."):
            params["domain"] = c["domain"]
        else:
            params["url"] = f"https://{c['domain']}/"
        if c["secure"]:
            params["secure"] = True
        try:
            exp = int(c["expiry"]) if c["expiry"].lstrip("-").isdigit() else 0
            if exp > 0:
                params["expires"] = exp
        except ValueError:
            pass
        if send("Network.setCookie", **params).get("success"):
            ok += 1
    print(f"set {ok}/{len(cookies)}")

    ws.settimeout(3.0)
    send("Page.enable")
    send("Page.navigate", url="https://www.dedao.cn/")
    time.sleep(8)
    r = send("Runtime.evaluate", expression="""JSON.stringify({
        logged_out: !!([...document.querySelectorAll('a,span,div')].find(
            e => e.offsetParent && e.innerText && e.innerText.trim() === '登录')),
        head: document.body ? document.body.innerText.slice(0, 80) : ''
    })""", returnByValue=True)
    state = json.loads(r.get("result", {}).get("value") or "{}")
    print(f"STATE: {state}")
    if not state.get("logged_out"):
        print("LOGIN OK (cookie 注入成功)")
        return 0
    print("LOGIN MISSING: cookie 无效或已过期, 让用户在浏览器重新登录得到后重新导出")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
