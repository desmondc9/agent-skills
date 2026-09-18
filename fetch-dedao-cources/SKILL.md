---
name: fetch-dedao-cources
description: "抓取得到APP(dedao.cn)付费专栏/课程的全部文章到本地HTML存档:复用本机Chrome登录态(复制Cookies启动调试实例),或注入 Get cookies.txt LOCALLY 导出的 cookies.txt(WSL/无桌面Chrome兜底),API翻页拿全量文章列表,逐页导航收割正文(标题/发布时间/摘要/划重点/图片),图片本地化并按原位置插入,自动过滤课程推广广告图(宽幅横幅+字节重复组OCR/二维码鉴定),生成可搜索的index.html总目录。支持用户自定义: ①课程名+URL列表 ②保存总目录命名规则 ③每讲文件夹命名规则(模板变量 {course}/{module}/{date}/{number}/{title})。Use whenever 用户要求抓取/备份/存档得到课程、精英日课类专栏、或提到 dedao.cn 课程内容下载。"
---

# 抓取得到APP课程到本地存档

把 dedao.cn 付费课程(需用户已购)完整抓成本地 HTML 站点:每讲一个文件夹(HTML + images/),外加可搜索的 index.html。已在万维钢 7 门课(2115 讲)和卓克 7 门课(2019 讲)上全量验证,零遗漏。

## 何时用本 skill

- 用户给出得到课程页 URL(`https://www.dedao.cn/course/detail?id=...`),要求抓取全部文章
- 用户要求备份/存档得到专栏内容到本地
- 前提(二选一):**本机 Chrome 已登录得到**(复制 Chrome 配置复用);或用户能用 Chrome 扩展 **Get cookies.txt LOCALLY** 导出 cookies.txt 注入登录态(WSL/无桌面 Chrome 场景,见第 0 步兜底)

## 总体流程(六步)

```
0. 准备:  检查依赖 → 启动调试 Chrome(复用登录态) → 验证登录
1. 配置:  按【配置规范】写 config.json(课程列表 + 两条命名规则)
2. 列表:  uv run scripts/crawl_lists.py      → 文章清单(与官网计数核对!)
3. 收割:  uv run scripts/harvest_contents.py → 逐篇正文(可断点续跑)
4. 建站:  uv run scripts/build_site.py       → HTML+图片(命名模板生效)
   (可选) uv run scripts/build_index.py      → index.html
5. 广告:  uv run scripts/triage_repeat_images.py → 重复图鉴定报告
   人工复核 → 定稿 blacklist.json → uv run scripts/remove_ads.py
6. 收尾:  bash scripts/teardown_chrome.sh(删Cookie副本!) → 汇报核对数字
```

## 第 0 步:环境与登录态(关键坑最多,严格照做)

**依赖**: `google-chrome`、`uv`、`tesseract`(OCR 用,可选)、curl。脚本用 PEP 723 内联依赖(`uv run` 自动装 websocket-client/requests/pillow/pyzbar)。

**启动调试 Chrome —— 必须在单独的 Bash 调用中执行**(和其它命令混在一起时后台进程会被回收):

```bash
bash scripts/setup_chrome.sh 9223 /tmp/dedao-fetch-work
```

它做的事:复制 `~/.config/google-chrome/Default/Cookies` + `Local State` 到 `/tmp/dedao-fetch-work/chrome-profile/`,再以 headless + `--remote-debugging-port=9223 --remote-allow-origins='*'` 启动。Chrome 自己经 XDG Secret Portal 解密 Cookie(KWallet 里查不到密钥,别走弯路)。

**验证登录**(页内应出现 `token` cookie;未登录则让用户先在自己 Chrome 里登录得到):

```bash
uv run scripts/check_login.py --work /tmp/dedao-fetch-work
```

### 登录态兜底:cookie 注入(本机无已登录 Chrome / 二维码无法展示时)

适用场景:WSL 或无桌面环境(本机没有已登录的 Chrome 可复制)、扫码登录的二维码无法弹出给用户(无图片查看器时 `xdg-open` 会**静默失败**,终端重渲二维码也不一定可扫)。此时 `setup_chrome.sh` 会自动回退:用 Playwright Chromium(`~/.cache/ms-playwright/chromium-*/`)启动**空白 profile**(无登录态可复制时会打 WARN)。

让用户在**任意一台已登录得到的浏览器**(Chrome/Edge)里装扩展 **Get cookies.txt LOCALLY**,导出 cookies.txt 放到本机(约定路径 `~/.cookie_contexts/cookies.txt`),然后注入:

```bash
uv run scripts/inject_cookies.py --cookies ~/.cookie_contexts/cookies.txt --port 9223
```

它只提取 dedao/umiwi/luojisiwei 相关条目,经 CDP `Network.setCookie` 注入调试 Chrome,并自动打开得到首页验证登录(页首不再出现"登录"即成功;失败说明 cookie 过期,让用户重新导出)。

注意事项:
- cookies.txt 含**完整登录凭据**,绝不提交入库、用完提醒用户删除;
- 注入前 `check_login.py` 可能显示有 `token`——那是**游客 token**(首次访问自动下发),不代表已登录,以页面有无"登录"入口/注入脚本验证结果为准;
- 手动杀调试 Chrome 时 `pkill -f <pattern>` 会匹配到执行命令的 shell 自身导致挂死,用 `pgrep -f '[c]hrome-profile'` 式防自匹配写法。

## 第 1 步:配置规范(config.json)

三项用户输入对应关系:①课程名+URL → `courses[]`;②总目录命名 → `root_dir`(支持 `{date} {year} {month} {author}` 模板);③每讲文件夹命名 → `folder_template`。

```json
{
  "author": "万维钢",
  "base_dir": "/home/desmond/Books-and-Articles",
  "root_dir": "{date}-{author}",
  "courses": [
    {"key": "S1", "name": "精英日课", "url": "https://www.dedao.cn/course/detail?id=93N5e6Rya4ZJjQYsQgVOmGApwlo08D"}
  ],
  "folder_template": "{course}-{module}-{date}-{title}",
  "strip_module_prefix": true,
  "strip_number_prefix": false,
  "work_dir": "/tmp/dedao-fetch-work",
  "chrome_port": 9223,
  "tabs": 5
}
```

字段说明:

| 字段 | 说明 |
|---|---|
| `author` | 作者名,用于 root_dir 模板与页面标题 |
| `base_dir` + `root_dir` | root_dir 为绝对路径时直接用;否则拼 `base_dir/root_dir`。支持模板变量 `{date}`(当天 YYYY-MM-DD)/`{year}`/`{month}`/`{author}`;纯字面量(如 `2026-08-25-万维钢`)也合法 |
| `courses[].key` | 短代号(缺省自动 C01/C02...),`courses[].name` 是**用户指定的课程名**,直接用于 `{course}`;`url` 里的 `id=` 参数即 detail_id |
| `folder_template` | 每讲文件夹名。变量:`{course}` 课程名、`{module}` 模块/章节名(自动去`(N讲)`后缀和书名号《》)、`{date}` 发布日(北京时间)、`{number}` 文章编号(见下)、`{title}` 标题 |
| `strip_module_prefix` | true 时标题去掉与模块同名的《书名》前缀(万维钢式书课推荐开) |
| `strip_number_prefix` | true 时从 `NNN｜标题` 前缀提取 `{number}`(卓克科技参考式推荐开);课程内有编号体系时,无编号文章(发刊词等)回退 `000`,否则用序号 |

**命名模板实例**(已验证):
- 万维钢式:`{course}-{module}-{date}-{title}` + `strip_module_prefix:true` → `精英日课2-你能做任何工作-2017-09-18-1_"文科生"的反击_软技能的时代`
- 卓克式:`{course}-{date}-{number}_{title}` + `strip_number_prefix:true` → `科技参考2-2022-01-07-005_元宇宙的一盆凉水`

**文件名净化规则**(自动):`\ / : * ? " < > | ： ｜ 丨 ， ,` 及空白→`_`;连续`_`折叠;HTML 文件名与文件夹同名,存在 `images/` 子目录;题图存为 `header_*`。

## 第 2~4 步:跑流水线

```bash
CFG=/tmp/dedao-fetch-work/config.json
uv run scripts/crawl_lists.py --config $CFG        # 全局翻页+逐章节count=0 双保险去重
uv run scripts/harvest_contents.py --config $CFG   # 5标签并行, ~80篇/分钟, 断点续跑
uv run scripts/build_site.py --config $CFG         # 生成HTML+下载图片+宽幅广告过滤
uv run scripts/build_index.py --config $CFG        # index.html 总目录(搜索/筛选)
```

**每步都要核对**:
- crawl_lists 日志里 `SAVED n (claimed m)` —— **n 必须等于 m**(官网计数),少了就重跑(幂等);
- harvest 后 `find <work>/contents -name '*.json' | wc -l` 应等于总讲数,缺的重跑补收;
- build 后抽查:用户给过的示例文章文件夹名、图片引用无缺失(`scripts/audit.py --config $CFG`)。

长任务用后台运行 + 轮询日志(`crawl_lists.log` / `harvest.log` 里每 25/80 篇打点)。

## 第 5 步:广告图过滤(两重,缺一不可)

**第一重(自动,已内建在 build_site)**:无图注且宽高比≥3 的横幅(标准 1080×260)删除;块里没尺寸的老图下载后 PIL 实测。**带图注的宽图是内容图表,不能删。**

**第二重(半自动,必须做)**:非宽幅推广图(订阅海报/公众号引流/小程序推广,每篇 URL 不同但字节相同)。内容图(书封/漫画/手写笔记)也会跨文章重复,**不能见重复就删**:

```bash
uv run scripts/triage_repeat_images.py --config $CFG
```

产出 `<work>/triage/report.json`(OCR+二维码自动判定)+ `<work>/triage/gNNN.jpg`(每组代表图)。然后:
1. 自动判 AD 的直接采信;
2. 自动判 CONTENT 但 **n≥3 的大重复组**(广告 campaign 通常几十上百次)以及你怀疑的组,**逐张看图复核**——推广特征:二维码、"订阅/扫码/立即购买/重磅首发/版权归得到App所有/未经许可/商务合作/等你归队/小剧场"等字样;
3. 把确认的组 md5 写进 `<work>/ads_blacklist.json`(格式 `[{"md5":"...","note":"..."}]`),可并入 `assets/known_ads_blacklist.json`(已验证的 12 组通用推广图);
4. `uv run scripts/remove_ads.py --config $CFG` 移除(HTML 去掉对应 `<figure>` + 删文件),再跑 `scripts/audit.py` 确认零残留零悬空。

## 第 6 步:收尾(必做)

```bash
bash scripts/teardown_chrome.sh /tmp/dedao-fetch-work   # 杀调试Chrome + 删除含Cookie的profile副本
```

向用户汇报:各课程 `n/n` 计数、总讲数、HTML/图片数、广告移除数、root 目录路径。提醒:抓取数据仅供个人学习。

## 关键坑备忘(违反任何一条都会返工)

1. **正文不在页内 fetch 里**:`article/info` → `dd_article/get/v2` 重放**拿不到正文**(服务端按页面加载时序 withholding)。唯一可靠方式 = 逐篇导航真实文章页 + CDP `Network.getResponseBody` 收割 ddarticle 响应。
2. **正文在响应的 `c.content`**,不是 `c.article.content`。
3. 列表翻页用 **`max_id`**(上一页最后一篇的 id);`since_id` 无效;每章 `chapter_id=<id>, count:0` 一次取全。
4. **图片文件名冲突**:不同 URL 尾段可能同名(`.../<不同id>/031519.png`),必须按 URL 哈希去重,否则同图重复+原图丢失。
5. 调试 Chrome 必须单独 Bash 调用启动;CDP ws URL 里 `127.0.0.1` 要换 `localhost`;无 `--remote-allow-origins='*'` 会 403。
6. 直连 requests 会被反爬拦(h.c=104000),一切 API 调用走页内 fetch 或页面自身请求。
7. 发布时间是 UTC 秒,展示日期按 **北京时间(+8)** 转换。
8. 图片 CDN(piccdn*.umiwi.com)可直连下载,带 UA+Referer 即可。
9. 任务结束**必须** teardown(Cookie 副本很敏感)。
10. **登录二维码展示的坑**:无图片查看器的环境(WSL)里 `xdg-open` 静默失败、有界面 Chrome 也可能因 zygote fork 失败起不来;别死磕扫码展示,直接走第 0 步的 cookie 注入兜底。另注意游客 `token` cookie 首访即有,**不能**作为已登录判据。

## 产出结构

```
<root>/
├── index.html                     # 总目录: 课程分组+搜索+筛选
├── _manifest.json                 # 全部文章元数据(标题/时间/摘要/相对链接)
└── <每讲文件夹>/                   # 命名按 folder_template
    ├── <同名>.html                # 标题/发布时间/摘要/题图/正文/图片
    └── images/*.jpg               # 正文图片(原位置)+header_题图
```
