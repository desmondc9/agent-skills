#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "pillow"]
# ///
"""阶段4: 生成 index.html 总目录(基于 <root>/_manifest.json)。
用法: uv run build_index.py --config <config.json>
"""
import argparse
import html as html_mod
import json
import os
import re

CSS = """
:root { --ink:#1f2329; --sub:#6b7280; --line:#e5e7eb; --bg:#f7f8fa; --card:#fff; --accent:#b45309; }
* { box-sizing:border-box; }
body { margin:0; font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif; color:var(--ink); background:var(--bg); }
.topbar { background:linear-gradient(135deg,#1f2a44,#31435f); color:#fff; padding:36px 20px 30px; }
.topbar .inner { max-width:1000px; margin:0 auto; }
.topbar h1 { margin:0 0 6px; font-size:26px; }
.topbar p { margin:4px 0; color:#c9d4e8; font-size:14px; }
.topbar a { color:#ffd98a; text-decoration:none; }
.stats { display:flex; gap:28px; margin-top:14px; flex-wrap:wrap; }
.stat { background:rgba(255,255,255,.08); border-radius:10px; padding:10px 18px; }
.stat b { font-size:22px; display:block; }
.stat span { font-size:12px; color:#c9d4e8; }
.toolbar { position:sticky; top:0; z-index:10; background:#fffdf8; border-bottom:1px solid var(--line); padding:10px 20px; }
.toolbar .inner { max-width:1000px; margin:0 auto; display:flex; gap:12px; align-items:center; flex-wrap:wrap;}
#q { flex:1; min-width:220px; padding:9px 14px; border:1px solid var(--line); border-radius:8px; font-size:14px; outline:none; }
#q:focus { border-color:var(--accent); }
.toolbar select { padding:8px 10px; border:1px solid var(--line); border-radius:8px; font-size:14px; background:#fff; }
.toolbar .count { color:var(--sub); font-size:13px; }
.wrap { max-width:1000px; margin:0 auto; padding:20px; }
.course { background:var(--card); border:1px solid var(--line); border-radius:14px; margin:22px 0; overflow:hidden; }
.course > header { padding:16px 22px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; background:#fbfaf7;}
.course h2 { margin:0; font-size:19px; }
.course .meta { color:var(--sub); font-size:13px; margin-top:2px; }
.course .meta a { color:var(--accent); text-decoration:none; }
.chap { border-bottom:1px dashed var(--line); }
.chap:last-child { border-bottom:none; }
.chap > .ch { padding:10px 22px; font-weight:600; background:#fafbfc; color:#374151; display:flex; justify-content:space-between; }
.chap > .ch .n { color:var(--sub); font-weight:400; font-size:12px; }
.chap > .list { display:grid; grid-template-columns:1fr 1fr; gap:0; }
.art { padding:10px 22px; border-top:1px solid #f0f1f3; display:block; text-decoration:none; color:var(--ink); }
.art:hover { background:#fff8ec; }
.art .t { font-size:14.5px; line-height:1.55; }
.art .d { color:var(--sub); font-size:12px; margin-top:2px; }
.art .s { color:#9ca3af; font-size:12px; margin-top:2px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
@media (max-width:760px){ .chap > .list { grid-template-columns:1fr; } }
.hidden { display:none !important; }
.foot { text-align:center; color:var(--sub); font-size:12px; padding:30px 0 40px; }
"""


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
    author = cfg.get("author", "")
    with open(os.path.join(root, "_manifest.json")) as f:
        m = json.load(f)

    courses_html = []
    total_art = 0
    for c in m["courses"]:
        n_arts = sum(len(ch["articles"]) for ch in c["chapters"])
        total_art += n_arts
        chap_html = []
        for ch in c["chapters"]:
            items = []
            for a in ch["articles"]:
                summ = html_mod.escape(a.get("summary") or "")
                search_key = html_mod.escape((a["title"] + " " + (a.get("summary") or "") + " " + (ch.get("name") or "")).lower())
                items.append(
                    f'<a class="art" href="{html_mod.escape(a["local"])}" data-search="{search_key}" '
                    f'data-course="{html_mod.escape(c["name"])}">'
                    f'<div class="t">{html_mod.escape(a["display_title"] or a["title"])}</div>'
                    f'<div class="d">📅 {html_mod.escape(a["datetime"])}</div>'
                    f'<div class="s">{summ}</div></a>'
                )
            chap_html.append(
                f'<div class="chap" data-chapter>'
                f'<div class="ch"><span>{html_mod.escape(ch["name"])}</span><span class="n">{len(ch["articles"])} 讲</span></div>'
                f'<div class="list">{"".join(items)}</div></div>'
            )
        courses_html.append(
            f'<section class="course" data-course-sec data-cname="{html_mod.escape(c["name"])}">'
            f'<header><div><h2>{html_mod.escape(c["name"])}</h2>'
            f'<div class="meta">{len(c["chapters"])} 个模块 · {n_arts} 讲 ｜ <a href="{html_mod.escape(c.get("url",""))}" target="_blank">得到原课程 ↗</a></div></div></header>'
            f'{"".join(chap_html)}</section>'
        )

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_mod.escape(author)}·得到课程合集 - 总目录</title>
<style>{CSS}</style>
</head>
<body>
<div class="topbar"><div class="inner">
<h1>{html_mod.escape(author)} · 得到课程合集</h1>
<p>{len(m['courses'])} 门课程 ｜ 共 {total_art} 讲 ｜ 抓取日期 {m.get("generated_at","")[:10]}</p>
<div class="stats">
<div class="stat"><b>{total_art}</b><span>文章总数</span></div>
<div class="stat"><b>{sum(len(c['chapters']) for c in m['courses'])}</b><span>模块总数</span></div>
<div class="stat"><b>{len(m['courses'])}</b><span>门课程</span></div>
</div>
</div></div>
<div class="toolbar"><div class="inner">
<input id="q" type="search" placeholder="🔍 搜索标题 / 摘要 / 模块…">
<select id="courseSel"><option value="">全部课程</option>{''.join(f'<option value="{html_mod.escape(c["name"])}">{html_mod.escape(c["name"])}</option>' for c in m['courses'])}</select>
<span class="count" id="count"></span>
</div></div>
<div class="wrap">
{''.join(courses_html)}
<div class="foot">仅供个人学习使用 · 内容版权归原作者与得到APP所有</div>
</div>
<script>
const q = document.getElementById('q'), sel = document.getElementById('courseSel'), cnt = document.getElementById('count');
function apply() {{
  const kw = q.value.trim().toLowerCase(), cv = sel.value;
  let n = 0;
  document.querySelectorAll('.art').forEach(a => {{
    const show = (!kw || a.dataset.search.includes(kw)) && (!cv || a.dataset.course === cv);
    a.classList.toggle('hidden', !show);
    if (show) n++;
  }});
  document.querySelectorAll('[data-chapter]').forEach(ch => {{
    ch.classList.toggle('hidden', ch.querySelectorAll('.art:not(.hidden)').length === 0);
  }});
  document.querySelectorAll('[data-course-sec]').forEach(sec => {{
    sec.classList.toggle('hidden', sec.querySelectorAll('.art:not(.hidden)').length === 0);
  }});
  cnt.textContent = n + ' 讲';
}}
q.addEventListener('input', apply); sel.addEventListener('change', apply); apply();
</script>
</body>
</html>"""
    with open(os.path.join(root, "index.html"), "w") as f:
        f.write(doc)
    print(f"index.html written, {total_art} articles -> {root}")


if __name__ == "__main__":
    main()
