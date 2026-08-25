#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["websocket-client", "requests"]
# ///
"""阶段1: 爬取 config 中全部课程的文章列表(全局翻页 + 逐章节全量, 双保险去重)。
输出 <work>/lists/<KEY>.json。用法: uv run crawl_lists.py --config <config.json>
"""
import argparse
import json
import os
import re
import time
from urllib.parse import urlparse, parse_qs

import requests
import websocket


def load_config(path):
    with open(path) as f:
        cfg = json.load(f)
    for i, c in enumerate(cfg.get("courses", []), 1):
        if not c.get("key"):
            c["key"] = f"C{i:02d}"
        q = parse_qs(urlparse(c["url"]).query)
        c["detail_id"] = q["id"][0]
    return cfg


class Tab:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=90)
        self.msg_id = 0

    def send(self, method, **params):
        self.msg_id += 1
        self.ws.send(json.dumps({"id": self.msg_id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.msg_id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def eval(self, expr):
        r = self.send(
            "Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True, timeout=60000,
        )
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:800])
        return r.get("result", {}).get("value")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    port = cfg.get("chrome_port", 9223)
    out_dir = os.path.join(cfg["work_dir"], "lists")
    os.makedirs(out_dir, exist_ok=True)

    resp = requests.put(f"http://127.0.0.1:{port}/json/new?url=about:blank", timeout=10).json()
    tab = Tab(resp["webSocketDebuggerUrl"].replace("127.0.0.1", "localhost"))
    tab.send("Page.enable")
    tab.send("Page.navigate", url="https://www.dedao.cn/")
    time.sleep(6)
    print("PAGE:", tab.eval("document.title"), flush=True)

    tab.eval("""
      window.__ddFetch = async function(url, body) {
        const r = await fetch(url, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          credentials: 'include',
          body: JSON.stringify(body)
        });
        const j = await r.json();
        if (!j || !j.h || j.h.c !== 0) return {err: JSON.stringify(j && j.h).slice(0, 200)};
        return {data: j.c};
      };
      'ok';
    """)

    for course in cfg["courses"]:
        did = course["detail_id"]
        for attempt in range(3):
            res = tab.eval(f"window.__ddFetch('/pc/bauhinia/pc/class/info', {{detail_id:{json.dumps(did)}, is_login:1}})")
            if "data" in res:
                break
            time.sleep(2)
        else:
            print(f"[{course['key']}] class/info FAILED: {res}", flush=True)
            continue
        c = res["data"]
        ci = c.get("class_info", {})
        chapters = [{"id": ch.get("id"), "name": ch.get("name"), "order": ch.get("order_num")}
                    for ch in c.get("chapter_list", []) or []]
        print(f"[{course['key']}] {ci.get('name')} phase={ci.get('phase_num')} "
              f"current={ci.get('current_article_count')} chapters={len(chapters)}", flush=True)

        articles = {}

        def absorb(lst):
            for a in lst or []:
                enid = a.get("enid")
                if not enid:
                    continue
                old = articles.get(enid)
                if old is None or (a.get("order_num") or 0) < (old.get("order_num") or 0):
                    articles[enid] = a
                else:
                    for k, v in a.items():
                        if old.get(k) in (None, "", 0) and v:
                            old[k] = v

        # 1) 全局翻页(正序+倒序, 含/不含 edge)
        for reverse in (False, True):
            for edge in (False, True):
                max_id = since_id = 0
                for page in range(80):
                    body = {
                        "chapter_id": "", "count": 50, "detail_id": did,
                        "include_edge": edge, "is_unlearn": False,
                        "max_id": max_id if not reverse else 0,
                        "max_order_num": 0, "reverse": reverse,
                        "since_id": since_id if reverse else 0,
                        "since_order_num": 0, "unlearn_switch": False,
                    }
                    res = tab.eval(f"window.__ddFetch('/api/pc/bauhinia/pc/class/purchase/article_list', {json.dumps(body, ensure_ascii=False)})")
                    if "err" in res:
                        time.sleep(2)
                        res = tab.eval(f"window.__ddFetch('/api/pc/bauhinia/pc/class/purchase/article_list', {json.dumps(body, ensure_ascii=False)})")
                        if "err" in res:
                            break
                    lst = res["data"].get("article_list", [])
                    absorb(lst)
                    if not lst:
                        break
                    if reverse:
                        since_id = lst[-1]["id"]
                    else:
                        max_id = lst[-1]["id"]
                    time.sleep(0.25)

        # 2) 每章节 count=0 全量
        for ch in chapters:
            body = {
                "chapter_id": str(ch["id"]), "count": 0, "detail_id": did,
                "include_edge": True, "is_unlearn": False,
                "max_id": 0, "max_order_num": 0, "reverse": False,
                "since_id": 0, "since_order_num": 0, "unlearn_switch": False,
            }
            for attempt in range(3):
                res = tab.eval(f"window.__ddFetch('/api/pc/bauhinia/pc/class/purchase/article_list', {json.dumps(body)})")
                if "data" in res:
                    break
                time.sleep(2)
            if "data" in res:
                absorb(res["data"].get("article_list", []))
            else:
                print(f"  chapter {ch['id']} err: {res}", flush=True)
            time.sleep(0.2)

        out = {
            "course": course,
            "class_info": {
                "name": ci.get("name"), "intro": ci.get("intro"),
                "phase_num": ci.get("phase_num"),
                "current_article_count": ci.get("current_article_count"),
                "has_chapter": ci.get("has_chapter"),
            },
            "chapters": chapters,
            "articles": list(articles.values()),
        }
        with open(f"{out_dir}/{course['key']}.json", "w") as f:
            json.dump(out, f, ensure_ascii=False)
        n, m = len(articles), ci.get("current_article_count")
        flag = "OK" if n == m else "*** MISMATCH, RERUN ***"
        print(f"[{course['key']}] SAVED {n} (claimed {m}) {flag}", flush=True)

    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
