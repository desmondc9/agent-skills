#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "pillow"]
# ///
"""全局审计: 列表计数核对 + 内容收割完整性 + HTML图片引用完整性 + index链接 + 广告残留。
用法: uv run audit.py --config <config.json>
"""
import argparse
import hashlib
import html as html_mod
import json
import os
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    with open(args.config) as f:
        cfg = json.load(f)
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build_site import resolve_root
    root = resolve_root(cfg)
    work = cfg["work_dir"]

    problems = []

    # 1. 列表计数
    print("== 列表计数 ==")
    total = 0
    for fname in sorted(os.listdir(os.path.join(work, "lists"))):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(work, "lists", fname)) as f:
            d = json.load(f)
        n, m = len(d["articles"]), d["class_info"].get("current_article_count")
        total += n
        ok = "OK" if n == m else "*** MISMATCH ***"
        if n != m:
            problems.append(f"lists {fname}: {n} != claimed {m}")
        print(f"  {fname[:-5]}: {n} / claimed {m} {ok}")

    # 2. 收割完整性
    print("== 收割完整性 ==")
    n_content = 0
    for fname in sorted(os.listdir(os.path.join(work, "lists"))):
        if not fname.endswith(".json"):
            continue
        key = fname[:-5]
        with open(os.path.join(work, "lists", fname)) as f:
            d = json.load(f)
        for a in d["articles"]:
            p = os.path.join(work, "contents", key, a["enid"] + ".json")
            if not os.path.exists(p):
                problems.append(f"content missing: {key}/{a['enid']}")
            else:
                n_content += 1
    print(f"  内容文件: {n_content} / {total}")
    if n_content != total:
        problems.append(f"contents {n_content} != lists {total}, 重跑 harvest_contents.py 补收")

    # 3. HTML/图片引用
    print("== 站点完整性 ==")
    htmls = imgs = missing = dangling = 0
    for d in os.listdir(root):
        dp = os.path.join(root, d)
        if not os.path.isdir(dp):
            continue
        hp = None
        for f in os.listdir(dp):
            if f.endswith(".html"):
                hp = os.path.join(dp, f)
        if not hp:
            continue
        htmls += 1
        with open(hp) as f:
            c = f.read()
        refs = re.findall(r'src="(images/[^"]+)"', c)
        imgs += len(refs)
        for r in refs:
            if not os.path.exists(os.path.join(dp, r)):
                missing += 1
                problems.append(f"missing ref: {d}/{r}")
        on_disk = set(os.listdir(os.path.join(dp, "images"))) if os.path.isdir(os.path.join(dp, "images")) else set()
        for extra in on_disk - set(r.split("/")[-1] for r in refs):
            dangling += 1
            problems.append(f"dangling file: {d}/images/{extra}")
    print(f"  HTML {htmls}, 图片引用 {imgs}, 缺失 {missing}, 悬空 {dangling}")

    # 4. index 链接(注意反转义)
    idx_path = os.path.join(root, "index.html")
    if os.path.exists(idx_path):
        with open(idx_path) as f:
            idx = f.read()
        links = [html_mod.unescape(l) for l in re.findall(r'href="([^"#]+\.html)"', idx)
                 if not l.startswith("http") and "/" in l]
        bad = [l for l in links if not os.path.exists(os.path.join(root, l))]
        print(f"== index 链接: {len(links)}, 失效 {len(bad)} ==")
        for b in bad[:5]:
            problems.append(f"index bad link: {b}")

    # 5. 广告残留
    bl = set()
    assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "assets", "known_ads_blacklist.json")
    for cand in [assets, os.path.join(work, "ads_blacklist.json")]:
        if os.path.exists(cand):
            with open(cand) as f:
                data = json.load(f)
            items = data if isinstance(data, list) else data.values()
            for it in items:
                if isinstance(it, dict) and "md5" in it:
                    bl.add(it["md5"])
    if bl:
        left = 0
        for d in os.listdir(root):
            ip = os.path.join(root, d, "images")
            if not os.path.isdir(ip):
                continue
            for f in os.listdir(ip):
                if hashlib.md5(open(os.path.join(ip, f), "rb").read()).hexdigest() in bl:
                    left += 1
        print(f"== 广告黑名单残留: {left} ==")
        if left:
            problems.append(f"广告残留 {left} 张, 重跑 remove_ads.py")

    print()
    if problems:
        print(f"发现 {len(problems)} 个问题:")
        for p in problems[:20]:
            print(" -", p)
        raise SystemExit(1)
    print("AUDIT PASS ✓")


if __name__ == "__main__":
    main()
