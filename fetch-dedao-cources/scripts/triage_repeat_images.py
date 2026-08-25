#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "pyzbar", "requests"]
# ///
"""阶段5a: 扫描已建站点的跨文章重复图片, OCR+二维码自动初判, 导出复核材料。
输出: <work>/triage/report.json + <work>/triage/gNNN.jpg
用法: uv run triage_repeat_images.py --config <config.json>
说明: tesseract(含 ~/.tessdata/chi_sim) 缺失时自动降级为仅二维码判定, 大组必须人工看图复核。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import defaultdict

from PIL import Image, ImageOps

AD_KEYWORDS = ["订阅", "扫码", "扫描", "二维码", "立即购买", "重磅首发", "版权归", "未经许可", "商务合作",
               "礼品卡", "归队", "已上线", "小剧场", "长按识别", "朋友圈", "获取更多", "敬请关注", "上新",
               "免费领", "领取", "购买", "现已上线", "加入", "收听", "公众号"]


def have_tesseract_chinese():
    if not shutil.which("tesseract"):
        return False
    d = os.path.expanduser("~/.tessdata")
    return os.path.exists(os.path.join(d, "chi_sim.traineddata"))


def ocr(p):
    im = Image.open(p).convert("L")
    w, h = im.size
    im = im.resize((w * 2, h * 2), Image.LANCZOS)
    im = ImageOps.autocontrast(im)
    im.save("/tmp/_dedao_ocr_tmp.png")
    env = {**os.environ, "TESSDATA_PREFIX": os.path.expanduser("~/.tessdata")}
    r = subprocess.run(["tesseract", "/tmp/_dedao_ocr_tmp.png", "stdout", "-l", "chi_sim+eng", "--psm", "3"],
                       capture_output=True, text=True, timeout=40, env=env)
    return r.stdout


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

    groups = defaultdict(list)
    for d in os.listdir(root):
        dp = os.path.join(root, d, "images")
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            p = os.path.join(dp, f)
            h = hashlib.md5(open(p, "rb").read()).hexdigest()
            groups[h].append((d, f))

    multi = {h: v for h, v in groups.items() if len(set(x for x, _ in v)) > 1}
    non_header = {h: v for h, v in multi.items() if not all(f.startswith("header_") for _, f in v)}
    print(f"总图 {sum(len(v) for v in groups.values())}, 跨文章重复组 {len(multi)}, 非header组 {len(non_header)}")

    items = sorted(non_header.items(), key=lambda x: -len(set(y for y, _ in x[1])))
    triage_dir = os.path.join(cfg["work_dir"], "triage")
    os.makedirs(triage_dir, exist_ok=True)

    from pyzbar import pyzbar
    use_ocr = have_tesseract_chinese()
    if not use_ocr:
        print("WARN: tesseract/chi_sim 不可用, 仅二维码判定; 大重复组务必人工看图复核")

    report = {}
    for i, (h, v) in enumerate(items):
        folder, fname = v[0]
        p = os.path.join(root, folder, "images", fname)
        verdict, hits = "CONTENT", []
        try:
            qr = len(pyzbar.decode(Image.open(p))) > 0
        except Exception:
            qr = False
        if qr:
            verdict, _ = "AD", hits.append("QR码")
        if use_ocr and verdict != "AD":
            try:
                text = ocr(p)
                found = [k for k in AD_KEYWORDS if k in text]
                if found:
                    verdict = "AD"
                    hits.append("文字:" + ",".join(found[:6]))
            except Exception:
                hits.append("ocr_err")
        # 导出代表图供人工复核
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail((700, 700))
            im.save(os.path.join(triage_dir, f"g{i:03d}.jpg"), quality=70)
        except Exception:
            pass
        report[i] = {"md5": h, "n_articles": len(set(x for x, _ in v)),
                     "verdict_auto": verdict, "hits": hits,
                     "example": f"{folder}/images/{fname}",
                     "thumb": f"g{i:03d}.jpg"}

    with open(os.path.join(triage_dir, "report.json"), "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    ads = {i: r for i, r in report.items() if r["verdict_auto"] == "AD"}
    print(f"自动判定 AD: {len(ads)} 组; 待人工复核: {len(report) - len(ads)} 组")
    print("下一步: 1) 采信自动 AD; 2) n>=3 的 CONTENT 组与可疑组逐张看图复核(推广特征=二维码/订阅/立即购买/版权声明等);")
    print("       3) 确认的 md5 写入 <work>/ads_blacklist.json 后运行 remove_ads.py")
    big = [f"g{i:03d}(n={r['n_articles']})" for i, r in report.items() if r["n_articles"] >= 3]
    if big:
        print("大重复组(优先复核):", " ".join(big))


if __name__ == "__main__":
    main()
