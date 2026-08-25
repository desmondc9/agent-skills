#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "pillow"]
# ///
"""阶段5b: 按 md5 黑名单从站点移除广告图(HTML 去掉对应 <figure> + 删除文件)。
黑名单文件格式(json): [{"md5": "...", "note": "..."}] 或 {"<key>": {"md5": "..."}}
自动并入本 skill assets/known_ads_blacklist.json。
用法: uv run remove_ads.py --config <config.json> [--blacklist <file>]
"""
import argparse
import hashlib
import json
import os
import re


def load_blacklist(path):
    md5s = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            for it in data:
                md5s[it["md5"]] = it.get("note", "")
        elif isinstance(data, dict):
            for k, it in data.items():
                if isinstance(it, dict) and "md5" in it:
                    md5s[it["md5"]] = it.get("note", k)
    return md5s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--blacklist")
    args = ap.parse_args()
    with open(args.config) as f:
        cfg = json.load(f)
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build_site import resolve_root
    root = resolve_root(cfg)

    assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "assets", "known_ads_blacklist.json")
    bl = load_blacklist(assets)
    if args.blacklist:
        bl.update(load_blacklist(args.blacklist))
    if not bl:
        print("empty blacklist, nothing to do")
        return
    print("blacklist md5:", len(bl))

    removed_files = edited_htmls = removed_figs = 0
    for d in os.listdir(root):
        dp = os.path.join(root, d)
        if not os.path.isdir(dp):
            continue
        imgdir = os.path.join(dp, "images")
        if not os.path.isdir(imgdir):
            continue
        hits = []
        for f in os.listdir(imgdir):
            p = os.path.join(imgdir, f)
            if hashlib.md5(open(p, "rb").read()).hexdigest() in bl:
                hits.append(f)
        if not hits:
            continue
        for f in os.listdir(dp):
            if not f.endswith(".html"):
                continue
            hp = os.path.join(dp, f)
            with open(hp) as fh:
                html = fh.read()
            orig = html
            for name in hits:
                pat = re.compile(
                    r'<figure>(?:(?!</figure>).)*?src="images/' + re.escape(name) +
                    r'"(?:(?!</figure>).)*?</figure>\s*', re.S)
                html, n = pat.subn("", html)
                removed_figs += n
            if html != orig:
                with open(hp, "w") as fh:
                    fh.write(html)
                edited_htmls += 1
        for name in hits:
            os.remove(os.path.join(imgdir, name))
            removed_files += 1

    print(f"edited_html={edited_htmls} removed_figures={removed_figs} removed_files={removed_files}")


if __name__ == "__main__":
    main()
