#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["websocket-client", "requests"]
# ///
"""阶段2: 逐篇导航文章页, 收割 article/info 与 ddarticle 正文响应。
多标签并行, 可断点续跑(已有 <work>/contents/<KEY>/<enid>.json 则跳过)。
用法: uv run harvest_contents.py --config <config.json>
"""
import argparse
import json
import os
import queue
import threading
import time

import requests
import websocket


def load_config(path):
    with open(path) as f:
        return json.load(f)


PAGE_TIMEOUT = 20


class Worker(threading.Thread):
    def __init__(self, wid, jobs, lock, port):
        super().__init__(daemon=True)
        self.wid = wid
        self.jobs = jobs
        self.lock = lock
        self.port = port
        self.count = 0
        self.pending = []

    def run(self):
        resp = requests.put(f"http://127.0.0.1:{self.port}/json/new?url=about:blank", timeout=10).json()
        self.ws = websocket.create_connection(
            resp["webSocketDebuggerUrl"].replace("127.0.0.1", "localhost"), timeout=90
        )
        self.msg_id = 0
        self.send("Page.enable")
        self.send("Network.enable")
        self.send("Page.navigate", url="https://www.dedao.cn/")
        time.sleep(6)
        print(f"[worker{self.wid}] ready", flush=True)
        while True:
            try:
                job = self.jobs.get_nowait()
            except queue.Empty:
                return
            try:
                self.process(job)
            except Exception as e:
                self.log({"key": job["key"], "enid": job["enid"],
                          "err": f"outer {type(e).__name__} {e}"})
                print(f"[worker{self.wid}] ERR {job['key']}/{job['enid'][:10]} {e}", flush=True)
            self.jobs.task_done()
            self.count += 1

    def send(self, method, **params):
        with self.lock:
            self.msg_id += 1
            mid = self.msg_id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            else:
                self.pending.append(msg)

    def log(self, obj):
        with self.lock:
            with open(self.status_file, "a") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def process(self, job):
        enid, key = job["enid"], job["key"]
        url = f"https://www.dedao.cn/course/article?id={enid}"
        info_body, content_body = None, None
        for attempt in range(2):
            self.pending = []
            self.ws.settimeout(0.2)
            try:
                while True:
                    self.ws.recv()
            except Exception:
                pass
            req_map = {}
            self.ws.settimeout(1.0)
            self.send("Page.navigate", url=url)
            deadline = time.time() + PAGE_TIMEOUT
            got_info = got_content = False
            while time.time() < deadline and not (got_info and got_content):
                if self.pending:
                    msg = self.pending.pop(0)
                else:
                    try:
                        msg = json.loads(self.ws.recv())
                    except Exception:
                        continue
                m, p = msg.get("method"), msg.get("params", {})
                if m == "Network.requestWillBeSent":
                    u = p["request"]["url"]
                    if "bauhinia/pc/article/info" in u:
                        req_map[p["requestId"]] = "info"
                    elif "ddarticle/v1/article/get" in u:
                        req_map[p["requestId"]] = "content"
                elif m == "Network.loadingFinished":
                    tag = req_map.get(p.get("requestId"))
                    try:
                        if tag == "info" and not got_info:
                            info_body = self.send("Network.getResponseBody", requestId=p["requestId"]).get("body")
                            got_info = True
                        elif tag == "content" and not got_content:
                            content_body = self.send("Network.getResponseBody", requestId=p["requestId"]).get("body")
                            got_content = True
                    except Exception:
                        pass
            if got_info and got_content:
                break
            if got_info and attempt == 0:
                self.ws.settimeout(1.0)
                deadline2 = time.time() + 3
                while time.time() < deadline2:
                    if self.pending:
                        msg = self.pending.pop(0)
                    else:
                        try:
                            msg = json.loads(self.ws.recv())
                        except Exception:
                            continue
                    if msg.get("method") == "Network.loadingFinished":
                        if req_map.get(msg["params"].get("requestId")) == "content":
                            try:
                                content_body = self.send("Network.getResponseBody",
                                                         requestId=msg["params"]["requestId"]).get("body")
                                got_content = True
                            except Exception:
                                pass
                if got_content:
                    break
            time.sleep(1)

        out = {"list_item": job["list_item"], "harvested_at": time.time()}
        if info_body:
            try:
                out["info"] = json.loads(info_body).get("c")
            except Exception:
                out["info_raw"] = info_body[:500]
        else:
            self.log({"key": key, "enid": enid, "err": "no article/info response"})
            print(f"[worker{self.wid}] NO-INFO {key}/{enid[:10]}", flush=True)
            return
        if content_body:
            try:
                out["content"] = json.loads(content_body).get("c")
            except Exception:
                out["content_raw"] = content_body[:500]
        raw = (out.get("content") or {}).get("content", "")
        if raw == "":
            self.log({"key": key, "enid": enid, "note": "empty content",
                      "title": job["list_item"].get("title", "")})
        with open(job["out_path"], "w") as f:
            json.dump(out, f, ensure_ascii=False)
        if self.count % 20 == 0:
            print(f"[worker{self.wid}] done {self.count} latest={key}/{enid[:10]}", flush=True)
        time.sleep(0.3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    port = cfg.get("chrome_port", 9223)
    n_tabs = cfg.get("tabs", 5)
    work = cfg["work_dir"]

    jobs = queue.Queue()
    total = 0
    for fname in sorted(os.listdir(os.path.join(work, "lists"))):
        if not fname.endswith(".json"):
            continue
        key = fname[:-5]
        os.makedirs(os.path.join(work, "contents", key), exist_ok=True)
        with open(os.path.join(work, "lists", fname)) as f:
            course = json.load(f)
        arts = sorted(course["articles"],
                      key=lambda a: (a.get("order_num") or 0, a.get("publish_time") or 0))
        for a in arts:
            out_path = os.path.join(work, "contents", key, f"{a['enid']}.json")
            if os.path.exists(out_path):
                continue
            jobs.put({"key": key, "enid": a["enid"], "list_item": a, "out_path": out_path})
            total += 1
    print(f"jobs queued: {total}", flush=True)
    if total == 0:
        print("NOTHING TO DO")
        return

    lock = threading.Lock()
    status_file = os.path.join(work, "harvest.status.jsonl")
    workers = []
    for i in range(n_tabs):
        w = Worker(i, jobs, lock, port)
        w.status_file = status_file
        w.start()
        workers.append(w)
    for w in workers:
        w.join()
    print("ALL HARVEST DONE", flush=True)


if __name__ == "__main__":
    main()
