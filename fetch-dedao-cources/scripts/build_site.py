#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "pillow"]
# ///
"""阶段3: 生成本地 HTML 站点(命名模板 + 图片本地化 + 宽幅广告过滤 + 题图插入)。
用法: uv run build_site.py --config <config.json>
"""
import argparse
import hashlib
import html as html_mod
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

import requests

TZ = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"

EXT_FAMILY = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".gif": ".gif",
              ".webp": ".webp", ".svg": ".svg"}
IMAGE_MIME_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
                  "image/webp": ".webp", "image/svg+xml": ".svg"}

CSS = """
:root { --ink:#1f2329; --sub:#6b7280; --line:#e5e7eb; --bg:#f7f8fa; --card:#ffffff; --accent:#b45309; }
* { box-sizing: border-box; }
body { margin:0; font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif; color:var(--ink); background:var(--bg); line-height:1.9; }
.page { max-width: 820px; margin: 0 auto; padding: 32px 20px 80px; }
.crumb { font-size: 14px; color: var(--sub); margin-bottom: 6px; }
.crumb a { color: var(--sub); text-decoration: none; }
.crumb a:hover { color: var(--accent); }
h1.title { font-size: 28px; line-height: 1.5; margin: 8px 0 4px; }
.meta { color: var(--sub); font-size: 14px; margin-bottom: 10px; }
.audio-note { background:#fdf6ec; border:1px solid #f3e0bd; border-radius:8px; padding:8px 14px; font-size:14px; color:#8a6d3b; margin: 14px 0; }
.summary { color:var(--sub); border-left:3px solid var(--accent); padding:4px 12px; margin:14px 0; background:#fffdf8; border-radius:4px; }
.content { background:var(--card); border:1px solid var(--line); border-radius:12px; padding: 28px 34px; margin-top:16px; }
.content p { margin: 12px 0; font-size:17px; text-align: justify; }
.content h2,.content h3,.content h4 { margin: 22px 0 10px; }
.content h2 { font-size:20px; } .content h3 { font-size:18px; } .content h4 { font-size:17px; }
.content img { max-width: 100%; height:auto; border-radius:8px; margin: 14px auto; display:block; box-shadow: 0 1px 6px rgba(0,0,0,.12); }
.headimg { margin: 0 0 18px; }
.headimg img { margin: 0 auto; }
.figcap { text-align:center; color:var(--sub); font-size:13px; margin-top:-6px; }
.content blockquote { margin:16px 0; padding: 10px 18px; border-left: 4px solid #d8b36a; background: #fbf7ee; color:#57534e; border-radius: 4px; }
.elite { margin: 18px 0; padding: 12px 18px; background: #f2f7f2; border: 1px solid #cfe3cf; border-radius: 8px; }
.elite .elite-tag { font-weight: 700; color:#2f6b3a; font-size:14px; display:block; margin-bottom:4px; }
.tip { margin: 16px 0; padding: 10px 18px; background: #eef4fb; border: 1px solid #c9dcf1; border-radius: 8px; }
.tip .tip-tag { font-weight:700; color:#2b5c9a; font-size:14px; display:block; margin-bottom:4px;}
.content ul,.content ol { margin: 10px 0; padding-left: 28px; font-size:17px; }
.content hr { border:none; border-top:1px dashed #d1d5db; margin: 22px 0; }
.footer { margin-top: 26px; color: var(--sub); font-size: 13px; text-align:center; }
.footer a { color: var(--sub); }
"""


def sanitize_component(s):
    s = (s or "").strip()
    s = re.sub(r'[\\/:*?"<>|：｜丨，,\s\x00-\x1f]', "_", s)
    return re.sub(r"_{2,}", "_", s).strip("_ .")


def clean_module_name(chapter_name):
    n = re.sub(r"[（(]\s*\d+\s*讲\s*[)）]$", "", chapter_name or "").strip()
    return re.sub(r"^《(.+)》$", r"\1", n)


def norm_for_match(s):
    return re.sub(r"[《》\s:：.。,，!！?？'‘’\"“”\-—_]", "", s or "")


def strip_module_prefix(title, chapter_name):
    m = re.match(r"^《([^》]+)》", title or "")
    if m and norm_for_match(m.group(1)) == norm_for_match(clean_module_name(chapter_name)):
        return title[m.end():]
    return title


def split_number(title):
    m = re.match(r"^\s*(\d{1,4})\s*[|｜丨:：]\s*(.+)$", title or "", re.S)
    if m:
        return m.group(1).zfill(3), m.group(2).strip()
    return None, (title or "").strip()


def runs_to_html(runs):
    out = []
    for run in runs or []:
        if run.get("type") != "text":
            continue
        txt = html_mod.escape((run.get("text") or {}).get("content", ""))
        if run.get("bold"):
            txt = f"<strong>{txt}</strong>"
        if run.get("italic"):
            txt = f"<em>{txt}</em>"
        out.append(txt)
    return "".join(out).replace("\n", "<br>")


def img_name_from_url(url):
    seg = url.split("?")[0].rstrip("/").split("/")[-1]
    return seg + ".jpg" if "." not in seg else seg


def unique_names(urls):
    bases = [img_name_from_url(u) for u in urls]
    dup = {b for b in bases if bases.count(b) > 1}
    out = {}
    for u, b in zip(urls, bases):
        if b in dup:
            stem, ext = os.path.splitext(b)
            out[u] = f"{stem}_{hashlib.md5(u.encode()).hexdigest()[:8]}{ext}"
        else:
            out[u] = b
    seen = {}
    for u, n in out.items():
        if n in seen.values():
            stem, ext = os.path.splitext(out[u])
            k = 2
            while f"{stem}_{k}{ext}" in seen.values():
                k += 1
            out[u] = f"{stem}_{k}{ext}"
        seen[u] = out[u]
    return out


class ImageDownloader:
    def __init__(self):
        self.sess = requests.Session()
        self.sess.headers.update({"User-Agent": UA, "Referer": "https://www.dedao.cn/"})
        self.cache = {}
        self.dims = {}
        self.promo_skipped = 0
        self.n_images = 0

    def probe_dims(self, url):
        if url in self.dims:
            return self.dims[url]
        try:
            from PIL import Image
            import io
            r = self.sess.get(url, timeout=30)
            if r.status_code == 200:
                im = Image.open(io.BytesIO(r.content))
                self.dims[url] = (im.width, im.height)
                return self.dims[url]
        except Exception:
            pass
        self.dims[url] = (None, None)
        return (None, None)

    def download(self, url, folder, force_name=None):
        key = (url, force_name)
        if key in self.cache:
            return self.cache[key]
        os.makedirs(os.path.join(folder, "images"), exist_ok=True)
        name = force_name or img_name_from_url(url)
        path = os.path.join(folder, "images", name)
        if not os.path.exists(path):
            ok = False
            for _ in range(3):
                try:
                    r = self.sess.get(url, timeout=30)
                    if r.status_code == 200 and r.content[:20] != b"":
                        ct = r.headers.get("Content-Type", "").split(";")[0].strip()
                        want = IMAGE_MIME_EXT.get(ct)
                        cur = EXT_FAMILY.get(os.path.splitext(name)[1].lower())
                        if want and cur and EXT_FAMILY[want] != cur:
                            name += want
                            path = os.path.join(folder, "images", name)
                        with open(path, "wb") as f:
                            f.write(r.content)
                        ok = True
                        break
                except Exception:
                    time.sleep(1.5)
            if not ok:
                self.cache[key] = None
                return None
        self.cache[key] = f"images/{name}"
        self.n_images += 1
        return f"images/{name}"

    def is_promo(self, url, block_w, block_h, legend):
        """广告判定: 无图注 且 宽高比>=3 (块无尺寸时下载实测)。带图注的宽图是内容图表, 保留。"""
        if (legend or "").strip():
            return False
        w, h = block_w, block_h
        try:
            if w and h:
                w, h = float(w), float(h)
            else:
                w, h = self.probe_dims(url)
        except (TypeError, ValueError):
            return False
        if w and h and w / h >= 3:
            self.promo_skipped += 1
            return True
        return False


def blocks_to_html(blocks, dl, folder, names):
    parts = []
    for b in blocks:
        t = b.get("type")
        if t == "audio":
            try:
                dur = int(b.get("duration") or 0)
            except (TypeError, ValueError):
                dur = 0
            desc = (b.get("desc") or "").strip("｜| ")
            note = f"🔊 本讲配有音频 · 约 {dur // 60} 分 {dur % 60} 秒"
            if desc:
                note += f" · {html_mod.escape(desc)}"
            parts.append(f'<div class="audio-note">{note}</div>')
        elif t == "paragraph":
            inner = runs_to_html(b.get("contents"))
            if inner.strip():
                jf = b.get("justify")
                style = f' style="text-align:{html_mod.escape(jf)}"' if jf and jf != "left" else ""
                parts.append(f"<p{style}>{inner}</p>")
        elif t == "header":
            lvl = min(max(int(b.get("level") or 2), 2), 4)
            inner = runs_to_html(b.get("contents")) or html_mod.escape(b.get("text") or "")
            parts.append(f"<h{lvl}>{inner}</h{lvl}>")
        elif t == "image":
            url = b.get("url") or ""
            legend = html_mod.escape(b.get("legend") or "").strip()
            if not url:
                continue
            if dl.is_promo(url, b.get("width"), b.get("height"), legend):
                continue
            rel = dl.download(url, folder, force_name=names.get(url))
            if rel:
                dim = ""
                if b.get("width"):
                    try:
                        dim = f' width="{int(b["width"])}"'
                    except (TypeError, ValueError):
                        dim = ""
                img = f'<img src="{rel}" alt="{legend or "插图"}" loading="lazy"{dim}>'
                cap = f'<div class="figcap">{legend}</div>' if legend else ""
                parts.append(f"<figure>{img}{cap}</figure>")
            else:
                parts.append(f'<figure><div class="figcap">[图片未能下载: {html_mod.escape(url)}]</div></figure>')
        elif t == "blockquote":
            parts.append(f"<blockquote>{runs_to_html(b.get('contents'))}</blockquote>")
        elif t == "elite":
            parts.append(f'<div class="elite"><span class="elite-tag">📌 划重点</span>{runs_to_html(b.get("contents"))}</div>')
        elif t == "tip":
            parts.append(f'<div class="tip"><span class="tip-tag">💡 提示</span>{runs_to_html(b.get("contents"))}</div>')
        elif t == "list":
            tag = "ol" if b.get("ordered") else "ul"
            items = [f"<li>{runs_to_html(li)}</li>" for li in b.get("contents") or []]
            parts.append(f"<{tag}>{''.join(items)}</{tag}>")
        elif t == "hr":
            parts.append("<hr>")
        else:
            txt = b.get("text") or ""
            if txt:
                parts.append(f"<p>{html_mod.escape(txt)}</p>")
    return "\n".join(parts)


def render_folder(template, values):
    """按模板组装文件夹名; 模板中的分隔符原样保留, 变量值各自 sanitize。"""
    out = template
    for k, v in values.items():
        out = out.replace("{" + k + "}", sanitize_component(v) if v is not None else "")
    out = re.sub(r"-{2,}|_{2,}", lambda m: m.group(0)[0], out)
    return out.strip("-_.")


def build_article_html(cfg, course, chapter_name, meta, body_html, head_img_rel):
    author = cfg.get("author", "")
    enid = meta["enid"]
    title = html_mod.escape(meta["title"])
    crumb = (f'<div class="crumb"><a href="../index.html">{html_mod.escape(author)}·得到课程合集</a> › '
             f'{html_mod.escape(course["name"])}</div>')
    chapter_html = f" ｜ 栏目：{html_mod.escape(chapter_name)}" if chapter_name else ""
    summary_html = (f'<div class="summary"><b>摘要：</b>{html_mod.escape(meta["summary"])}</div>'
                    if meta.get("summary") else "")
    head_html = f'<figure class="headimg"><img src="{head_img_rel}" alt="题图"></figure>' if head_img_rel else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - {html_mod.escape(course['name'])}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">
{crumb}
<h1 class="title">{title}</h1>
<div class="meta">发布时间：{meta['datetime']}{chapter_html}</div>
{summary_html}
<div class="content">
{head_html}
{body_html}
</div>
<div class="footer">原文：<a href="https://www.dedao.cn/course/article?id={enid}">得到 · {title}</a></div>
</div>
</body>
</html>
"""


def resolve_root(cfg):
    root = cfg["root_dir"]
    if os.path.isabs(root):
        return root
    tpl_vars = {
        "{date}": datetime.now(TZ).strftime("%Y-%m-%d"),
        "{year}": datetime.now(TZ).strftime("%Y"),
        "{month}": datetime.now(TZ).strftime("%m"),
        "{author}": cfg.get("author", ""),
    }
    for k, v in tpl_vars.items():
        root = root.replace(k, v)
    root = sanitize_component(root)
    return os.path.join(cfg.get("base_dir", os.path.expanduser("~")), root)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    with open(args.config) as f:
        cfg = json.load(f)

    root = resolve_root(cfg)
    os.makedirs(root, exist_ok=True)
    template = cfg.get("folder_template", "{course}-{module}-{date}-{title}")
    strip_module = cfg.get("strip_module_prefix", "{module}" in template)
    strip_number = cfg.get("strip_number_prefix", "{number}" in template)

    dl = ImageDownloader()
    manifest = {"courses": [], "generated_at": datetime.now(TZ).isoformat(),
                "root": root, "folder_template": template}

    for fname in sorted(os.listdir(os.path.join(cfg["work_dir"], "lists"))):
        if not fname.endswith(".json"):
            continue
        key = fname[:-5]
        with open(os.path.join(cfg["work_dir"], "lists", fname)) as f:
            course_data = json.load(f)
        course = course_data["course"]
        chapters = {c["id"]: c for c in course_data["chapters"]}
        arts = sorted(course_data["articles"],
                      key=lambda a: (a.get("order_num") or 0, a.get("publish_time") or 0))
        course_has_numbers = any(split_number(x.get("title") or "")[0] is not None for x in arts)

        course_entry = {"key": key, "name": course["name"], "detail_id": course.get("detail_id"),
                        "url": course.get("url") or f"https://www.dedao.cn/course/detail?id={course.get('detail_id')}",
                        "intro": (course_data["class_info"] or {}).get("intro", ""), "chapters": []}
        used_folders = set()
        chap_entries = {}

        for seq, a in enumerate(arts, 1):
            enid = a["enid"]
            info, blocks = {}, []
            cfn = os.path.join(cfg["work_dir"], "contents", key, f"{enid}.json")
            if os.path.exists(cfn):
                with open(cfn) as f:
                    d = json.load(f)
                info = d.get("info") or {}
                raw = (d.get("content") or {}).get("content", "")
                try:
                    blocks = json.loads(raw) if raw else []
                except Exception:
                    blocks = []

            ai = info.get("article_info") or {}
            chapter_id = ai.get("chapter_id") or a.get("chapter_id")
            ch = chapters.get(chapter_id, {})
            chapter_name = clean_module_name(ch.get("name") or "")
            pt = ai.get("publish_time") or a.get("publish_time")
            dt = datetime.fromtimestamp(int(pt), TZ) if pt else None
            title = ai.get("title") or a.get("title") or enid

            disp_title = title
            number = None
            if strip_number:
                number, disp_title = split_number(disp_title)
                if number is None:
                    number = "000" if course_has_numbers else str(seq).zfill(3)
            if strip_module:
                disp_title = strip_module_prefix(disp_title, ch.get("name") or "")

            values = {
                "course": course["name"],
                "module": chapter_name,
                "date": dt.strftime("%Y-%m-%d") if dt else "0000-00-00",
                "number": number,
                "title": disp_title,
            }
            folder = render_folder(template, values)
            n = 1
            while folder in used_folders:
                n += 1
                folder = f"{folder}-{n}"
            used_folders.add(folder)
            folder_path = os.path.join(root, folder)
            os.makedirs(folder_path, exist_ok=True)

            logo = ai.get("logo") or a.get("logo") or ""
            content_urls = [b.get("url") for b in blocks if b.get("type") == "image" and b.get("url")]
            all_urls = ([logo] if logo else []) + content_urls
            names = unique_names(all_urls)
            if logo and names.get(logo):
                stem, ext = os.path.splitext(names[logo])
                names[logo] = f"header_{stem}{ext}"

            body_html = blocks_to_html(blocks, dl, folder_path, names)
            head_img_rel = dl.download(logo, folder_path, force_name=names.get(logo)) if logo else None

            meta = {
                "enid": enid, "title": title, "display_title": disp_title, "number": number,
                "datetime": dt.strftime("%Y-%m-%d %H:%M") if dt else "",
                "date": dt.strftime("%Y-%m-%d") if dt else "",
                "summary": ai.get("summary") or a.get("summary") or "",
                "order_num": a.get("order_num"), "chapter_id": chapter_id,
                "chapter": chapter_name,
                "url": f"https://www.dedao.cn/course/article?id={enid}",
                "folder": folder, "local": f"{folder}/{folder}.html",
            }
            with open(os.path.join(folder_path, f"{folder}.html"), "w") as f:
                f.write(build_article_html(cfg, course, chapter_name, meta, body_html, head_img_rel))

            ce = chap_entries.get(chapter_id)
            if ce is None:
                ce = {"id": chapter_id, "name": chapter_name or "未分类", "articles": []}
                chap_entries[chapter_id] = ce
                course_entry["chapters"].append(ce)
            ce["articles"].append(meta)

        manifest["courses"].append(course_entry)
        print(f"[{key}] built {len(arts)} articles", flush=True)

    with open(os.path.join(root, "_manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"MANIFEST SAVED root={root} images={dl.n_images} promo_skipped={dl.promo_skipped}", flush=True)


if __name__ == "__main__":
    main()
