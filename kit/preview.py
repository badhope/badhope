# -*- coding: utf-8 -*-
"""预览：把生成的 README 转成单文件可导航 HTML。"""

import pathlib
import re

import accounts as A

from .build import generate_to, write_account_files
from .config import PLATFORM_LABEL
from .data import load_stats
from .paths import ROOT
from .mdrender import render as render_markdown
from .textutil import esc

PREVIEW_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>主页面 kit · 预览</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin:0; background:#04060E; color:#F4F7FF;
         font:16px/1.65 "Helvetica Neue",Helvetica,Arial,"PingFang SC","Microsoft YaHei",sans-serif; }}
  .page {{ max-width:900px; margin:0 auto; padding:48px 28px 96px; }}
  .badge {{ display:inline-block; padding:2px 10px; border:1px solid rgba(217,184,118,.5);
            border-radius:999px; color:#D9B876; font-size:12px; letter-spacing:2px; }}
  .kit {{ font-size:13px; color:#5C6A94; letter-spacing:2px; }}
  .account {{ margin-top:72px; border-top:1px solid rgba(217,184,118,.22); padding-top:40px; }}
  .account h1 {{ font-family:Georgia,"Times New Roman",serif; font-weight:600;
                 letter-spacing:1px; font-size:26px; }}
  .account img.hero {{ width:100%; border-radius:14px; border:1px solid rgba(217,184,118,.25); }}
  .readme {{ margin-top:28px; }}
  .readme h2 {{ font-family:Georgia,serif; font-size:21px; border-bottom:1px solid rgba(217,184,118,.2);
                padding-bottom:8px; margin-top:44px; }}
  .readme h3 {{ font-size:17px; color:#D9B876; margin-top:28px; }}
  .readme a {{ color:#F2DC9E; text-decoration:none; }}
  .readme code {{ background:#131D3D; border:1px solid rgba(217,184,118,.18);
                  border-radius:6px; padding:1px 6px; font-size:13px; color:#9AA8CC; }}
  .readme blockquote {{ border-left:3px solid rgba(217,184,118,.5); margin-left:0;
                        padding-left:16px; color:#9AA8CC; }}
  .readme img {{ max-width:100%; }}
  .readme ul {{ padding-left:22px; }}
  .readme table {{ border-collapse:collapse; margin:8px 0; }}
  .readme th, .readme td {{ padding:6px 12px; border:1px solid rgba(217,184,118,.18); text-align:left; vertical-align:middle; }}
  .readme th {{ color:#D9B876; font-weight:600; }}
  .tscroll {{ overflow-x:auto; }}
  .readme .tscroll table {{ min-width:520px; }}
  .meta {{ color:#5C6A94; font-size:13px; margin-top:6px; }}
</style>
</head>
<body>
<div class="page">
  <span class="badge">主页面 KIT · 预览</span>
  <p class="kit">GENERATED PREVIEW · {count} ACCOUNTS · {langs} LANGUAGES · SELF-CONTAINED SVG</p>
{body}
</div>
</body>
</html>
"""

PREVIEW_FALLBACK = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>主页面 kit · 预览</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; background:#04060E; color:#F4F7FF;
         font:16px/1.65 "Helvetica Neue",Helvetica,Arial,"PingFang SC","Microsoft YaHei",sans-serif; }
  .page { max-width:900px; margin:0 auto; padding:48px 28px 96px; }
  .badge { display:inline-block; padding:2px 10px; border:1px solid rgba(217,184,118,.5);
           border-radius:999px; color:#D9B876; font-size:12px; letter-spacing:2px; }
  .kit { font-size:13px; color:#5C6A94; letter-spacing:2px; }
  nav.pills { display:flex; gap:8px; flex-wrap:wrap; margin:24px 0; }
  nav.pills button { background:#0E1630; color:#9AA8CC; border:1px solid rgba(217,184,118,.25);
                     border-radius:999px; padding:4px 14px; cursor:pointer; }
  nav.pills button.is-active { color:#F2DC9E; border-color:currentColor; }
  .account { margin-top:72px; border-top:1px solid rgba(217,184,118,.22); padding-top:40px; }
  .account h1 { font-family:Georgia,serif; font-weight:600; letter-spacing:1px; font-size:26px; }
  .account img { max-width:100%; }
  .meta { color:#5C6A94; font-size:13px; }
  .tabs { display:flex; gap:8px; margin:18px 0 10px; }
  .tabs .tab { background:transparent; color:#9AA8CC; border:1px solid rgba(217,184,118,.25);
               border-radius:6px; padding:2px 12px; cursor:pointer; }
  .tabs .tab.is-active { color:#D9B876; border-color:#D9B876; }
  .pane { display:none; }
  .pane.is-active { display:block; }
  .readme h2 { font-family:Georgia,serif; font-size:21px; border-bottom:1px solid rgba(217,184,118,.2);
               padding-bottom:8px; margin-top:44px; }
  .readme h3 { font-size:17px; color:#D9B876; margin-top:28px; }
  .readme a { color:#F2DC9E; text-decoration:none; }
  .readme blockquote { border-left:3px solid rgba(217,184,118,.5); margin-left:0;
                       padding-left:16px; color:#9AA8CC; }
  .readme table { border-collapse:collapse; margin:8px 0; }
  .readme th, .readme td { padding:6px 12px; border:1px solid rgba(217,184,118,.18); text-align:left; }
  .readme th { color:#D9B876; }
  .tscroll { overflow-x:auto; }
</style>
</head>
<body>
<div class="page">
  <span class="badge">主页面 KIT · 预览</span>
  <p class="kit">GENERATED PREVIEW · {{count}} ACCOUNTS · {{langs}} LANGUAGES · SELF-CONTAINED SVG</p>
  <nav class="pills">{{nav}}</nav>
  <div class="readme">{{panels}}</div>
</div>
<script>
document.querySelectorAll('nav.pills button').forEach(function (btn) {{
  btn.addEventListener('click', function () {{
    document.querySelectorAll('nav.pills button').forEach(function (b) {{ b.classList.remove('is-active'); }});
    btn.classList.add('is-active');
    var target = document.getElementById(btn.dataset.target);
    if (target) target.scrollIntoView({{ behavior: 'smooth' }});
  }});
}});
document.querySelectorAll('.tabs').forEach(function (group) {{
  group.querySelectorAll('.tab').forEach(function (tab) {{
    tab.addEventListener('click', function () {{
      var section = tab.closest('.account');
      section.querySelectorAll('.tab').forEach(function (t) {{ t.classList.remove('is-active'); }});
      section.querySelectorAll('.pane').forEach(function (p) {{ p.classList.remove('is-active'); }});
      tab.classList.add('is-active');
      var pane = section.querySelector('.pane[data-lang="' + tab.dataset.lang + '"]');
      if (pane) pane.classList.add('is-active');
    }});
  }});
}});
</script>
</body>
</html>
"""

def md_line_html(text):
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text

def md_to_html(md):
    out, in_ul, in_table = [], False, False

    def is_sep_row(line):
        return bool(re.fullmatch(r"\s*\|[\s:|-]*\|\s*", line)) and "-" in line

    for raw in md.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if in_ul and not stripped.startswith("- "):
            out.append("</ul>")
            in_ul = False
        is_table_row = stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2
        if in_table and not is_table_row:
            out.append("</table></div>")
            in_table = False
        if stripped.startswith("## "):
            out.append("<h2>%s</h2>" % md_line_html(stripped[3:]))
        elif stripped.startswith("### "):
            out.append("<h3>%s</h3>" % md_line_html(stripped[4:]))
        elif is_table_row:
            if is_sep_row(stripped):
                continue
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            if not in_table:
                out.append('<div class="tscroll"><table>')
                in_table = True
                tag = "th"
            else:
                tag = "td"
            tds = "".join("<%s>%s</%s>" % (tag, md_line_html(c), tag) for c in cells)
            out.append("<tr>%s</tr>" % tds)
        elif stripped.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>%s</li>" % md_line_html(stripped[2:]))
        elif stripped.startswith("> "):
            out.append("<blockquote>%s</blockquote>" % md_line_html(stripped[2:]))
        elif line.startswith("<") or (line[:1] == " " and stripped.startswith("<")):
            out.append(line)  # 原生 HTML（含缩进的 img/picture 等），按原样输出
        elif not line:
            out.append("")
        else:
            out.append("<p>%s</p>" % md_line_html(line))
    if in_ul:
        out.append("</ul>")
    if in_table:
        out.append("</table></div>")
    return "\n".join(out)

def LOCALIZE_BADGES(md):
    """把 shields.io 动态徽章替换为本地静态文本块（预览页专用，不改动部署产物）。"""
    def repl(m):
        label = m.group(1) or ""
        value = m.group(2) or ""
        return ('<span class="staticbadge"><b>%s</b>%s</span>'
                % (esc(label.replace("+", " ")), esc(value.replace("+", " "))))
    # 形如 https://img.shields.io/badge/dynamic/json?...&label=xxx  → 用 label 文本占位
    md = re.sub(r'<img[^>]*src="https://img\.shields\.io[^"]*label=([^"&]*)[^"]*"[^>]*/?>',
                lambda m: repl_static(m.group(1)), md)
    return md

def repl_static(label):
    from urllib.parse import unquote_plus
    return '<span class="staticbadge">%s</span>' % esc(unquote_plus(label))

def strip_preview_dupes(md):
    """预览页自带语言 tab 与 hero，剥离 README 里重复的那两段。"""
    lines = md.split("\n")
    out = []
    i = 0
    while i < len(lines):
        st = lines[i].strip()
        # 顶部语言导航行：[English](...) | [中文](...) | [日本語](...)
        if ("README.md)" in st and "README.zh-CN.md)" in st and "README.ja.md)" in st
                and st.startswith("[")):
            i += 1
            continue
        # hero 块：<p ...> 起始，内部含 hero.svg（可能包在 <picture>/<source> 里），直到 </p>
        if st.startswith("<p"):
            # 向后看最多 6 行，找到 </p>
            j = i
            block = []
            while j < len(lines) and j < i + 6:
                block.append(lines[j])
                if "</p>" in lines[j]:
                    break
                j += 1
            joined = "\n".join(block)
            if 'assets/hero.svg' in joined and "</p>" in joined:
                i = j + 1
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)

def _preview_panel(key, acct, langs_data, stats_block, accent):
    """内置预览面板（brand.py / preview.py 缺失时的降级实现，零外部依赖）。"""
    tabs, bodies = [], []
    for i, (lang, data) in enumerate(langs_data.items()):
        active = i == 0
        tabs.append('<button class="tab%s" data-lang="%s">%s</button>'
                    % (" is-active" if active else "", lang, esc(data["label"])))
        bodies.append('<div class="pane%s" data-lang="%s">%s</div>'
                      % (" is-active" if active else "", lang, data["html"]))
    return """
<section class="account" id="%s" style="--accent:%s">
  <h1>%s <span class="meta">%s</span></h1>
  <p class="meta">%s · %s</p>
  <div class="tabs">%s</div>
  %s
</section>""" % (esc(key), accent, esc(acct["handle"]), esc(PLATFORM_LABEL[acct["platform"]]),
                 esc(acct["home_display"]), esc(acct["role"]["md"]),
                 "".join(tabs), "\n".join(bodies))

def build_preview(out_dir):
    """构建多账号、多语言、可导航的预览界面（单文件 + 相对路径资产）。

    brand.py / preview.py 属于上游 kit 的可选模块；镜像仓库里没有它们，
    此时使用内置的精简模板，保证 --preview 在任意 checkout 里都能跑通。
    """
    try:
        import brand
        import preview as P
        panel = P._account_panel
        template = P.TEMPLATE
    except ImportError:
        brand = None
        panel = _preview_panel
        template = PREVIEW_FALLBACK

    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # dist 放在 preview 的兄弟目录：模板里的 ../dist/... 相对路径才能解析，
    # --out 指到任意目录时也不会去引用仓库根下的旧 dist。
    dist = out_dir.parent / "dist"
    stats = load_stats(ROOT / "data" / "stats.json")

    if brand is not None:
        brand_dir = dist / "brand"
        brand_dir.mkdir(parents=True, exist_ok=True)
        (brand_dir / "mark.svg").write_text(brand.logo_mark(64, with_wordmark=False), encoding="utf-8", newline="\n")
        (brand_dir / "logo.svg").write_text(brand.logo_mark(64, with_wordmark=True), encoding="utf-8", newline="\n")
        (brand_dir / "favicon.svg").write_text(brand.favicon_svg(), encoding="utf-8", newline="\n")
        (brand_dir / "mark-light.svg").write_text(brand.logo_light(), encoding="utf-8", newline="\n")

    lang_labels = {"md": "English", "zh-CN": "中文", "ja": "日本語"}
    accent = {"gh_x33834": "#7C9CFF", "gh_morningstar": "#C9A0FF",
              "gh_badhope": "#D9B876", "gitcode_badhope": "#3FD9C0", "gitee_badhope": "#FF8FA3"}

    nav, panels = [], []
    for key in A.ACCOUNT_ORDER:
        acct = A.ACCOUNTS[key]
        generate_to(dist / key, key, stats)
        rel = "../dist/%s/assets" % key
        langs_data = {}
        for lang in A.LANGS:
            md = (dist / key / A.README_NAME[lang]).read_text(encoding="utf-8")
            md = strip_preview_dupes(md)
            md = md.replace("./assets/", rel + "/")
            # 预览页必须离线可开：把实时 shields 徽章换成等价的本地静态条，
            # 否则内网/离线环境下 <img> 永不加载完成，整页卡在 loading。
            md = LOCALIZE_BADGES(md)
            langs_data[lang] = {
                "label": lang_labels.get(lang, lang),
                "labels": A.LABELS[lang],
                "html": render_markdown(md)[0],
                "hero": rel + "/hero.svg",
            }
        block = (stats.get("accounts") or {}).get(key) or {}
        panels.append(panel(key, acct, langs_data, block, accent.get(key, "#D9B876")))
        nav.append(
            '<button class="navitem%s" data-target="%s" style="--accent:%s">'
            '<span class="dot"></span><span>%s</span>'
            '<span class="nav-plat"> · %s</span></button>'
            % (" is-active" if key == A.ACCOUNT_ORDER[0] else "", key,
               accent.get(key, "#D9B876"), esc(acct["handle"]),
               esc(PLATFORM_LABEL[acct["platform"]]))
        )

    if template is PREVIEW_FALLBACK:
        html = (template.replace("{{count}}", str(len(A.ACCOUNT_ORDER)))
                        .replace("{{langs}}", str(len(A.LANGS)))
                        .replace("{{nav}}", "".join(nav))
                        .replace("{{panels}}", "".join(panels)))
    else:
        html = template.format(count=len(A.ACCOUNT_ORDER), langs=len(A.LANGS),
                               nav="".join(nav), panels="".join(panels))
    (out_dir / "index.html").write_text(html, encoding="utf-8", newline="\n")
    return out_dir / "index.html"
