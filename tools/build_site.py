#!/usr/bin/env python3
"""Build the public static site from private Markdown manuscripts.

The Markdown source stays outside this public repository. This script only
publishes generated HTML, copied figures, PDFs, and MATLAB examples.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import urllib.parse
from pathlib import Path


CHAPTERS = [
    ("第1章", "第一章", "雷达是什么"),
    ("第2章", "第二章", "信号基础"),
    ("第3章", "第三章", "雷达信号的生成与接收"),
    ("第4章", "第四章", "距离测量"),
    ("第5章", "第五章", "速度测量"),
    ("第6章", "第六章", "目标检测"),
    ("第7章", "第七章", "测角"),
    ("第8章", "第八章", "完整处理流程"),
]

INTRO = "面向学生和工程师的雷达信号处理入门教材：先建立直觉，再跑通 MATLAB 示例。"
GITHUB_URL = "https://github.com/apple-art/easy-radar-tutorial"
SITE_URL = "https://apple-art.github.io/easy-radar-tutorial/"


def posix_rel(path: Path, start: Path) -> str:
    return Path(os.path.relpath(path, start)).as_posix()


def url_path(path: str) -> str:
    return urllib.parse.quote(path, safe="/:#?&=%")


def html_attr(text: str) -> str:
    return html.escape(text, quote=True)


def github_tree_url(rel_path: str) -> str:
    return f"{GITHUB_URL}/tree/main/{url_path(rel_path).rstrip('/')}"


def github_blob_url(rel_path: str) -> str:
    return f"{GITHUB_URL}/blob/main/{url_path(rel_path)}"


def reset_generated_dir(path: Path, root: Path) -> None:
    resolved = path.resolve()
    root_resolved = root.resolve()
    if root_resolved not in resolved.parents and resolved != root_resolved:
        raise RuntimeError(f"Refusing to delete outside output root: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def strip_number_prefix(stem: str) -> str:
    stem = re.sub(r"^第[一二三四五六七八九十]+章[_-]?", "", stem)
    stem = re.sub(r"^\d+(?:\.\d+)?[_-]?", "", stem)
    return stem.replace("_", " ").strip()


def section_key(path: Path) -> tuple[int, int, str]:
    match = re.match(r"^(\d+)\.(\d+)", path.stem)
    if match:
        return int(match.group(1)), int(match.group(2)), path.name
    return 99, 99, path.name


def section_slug(path: Path, chapter_index: int) -> str:
    match = re.match(r"^(\d+)\.(\d+)", path.stem)
    if match:
        return f"ch{int(match.group(1)):02d}-{int(match.group(2)):02d}.html"
    return f"ch{chapter_index:02d}-index.html"


def extract_title(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return fallback


def first_paragraph(markdown_text: str) -> str:
    captured: list[str] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("![") or stripped == "$$":
            if captured:
                break
            continue
        if stripped.startswith("```") or stripped.startswith("|"):
            continue
        captured.append(stripped)
        if len("".join(captured)) > 120:
            break
    text = " ".join(captured)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    return text[:130] + ("..." if len(text) > 130 else "")


class SiteBuilder:
    def __init__(self, source_root: Path, output_root: Path) -> None:
        self.source_root = source_root
        self.manuscript_root = source_root / "手稿"
        self.figure_source_root = source_root / "figures"
        self.output_root = output_root
        self.chapter_out = output_root / "chapters"
        self.asset_out = output_root / "assets"
        self.figure_out = output_root / "figures"
        self.pdf_by_chapter: dict[str, str] = {}
        self.matlab_dir_by_chapter: dict[str, str] = {}
        self.matlab_files_by_name: dict[str, str] = {}
        self.sections: list[dict] = []
        self.by_chapter: list[dict] = []

    def build(self) -> None:
        self.prepare_dirs()
        self.discover_public_assets()
        self.discover_sections()
        self.write_assets()
        self.write_pages()
        self.write_gitignore_guard()
        print(f"Generated {len(self.sections)} HTML section pages")
        print(f"Copied {len(list(self.figure_out.rglob('*.*')))} referenced figure files")
        print(f"Index: {self.output_root / 'index.html'}")

    def prepare_dirs(self) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        for path in [self.chapter_out, self.asset_out, self.figure_out]:
            reset_generated_dir(path, self.output_root)

    def discover_public_assets(self) -> None:
        pdf_root = self.output_root / "pdf"
        if pdf_root.exists():
            for pdf in sorted(pdf_root.glob("*.pdf")):
                for _, chapter_cn, _ in CHAPTERS:
                    if chapter_cn in pdf.name:
                        self.pdf_by_chapter[chapter_cn] = posix_rel(pdf, self.output_root)
                        break
        matlab_root = self.output_root / "matlab"
        if matlab_root.exists():
            for chapter_dir in sorted([p for p in matlab_root.iterdir() if p.is_dir()]):
                self.matlab_dir_by_chapter[chapter_dir.name] = posix_rel(chapter_dir, self.output_root)
                for mfile in chapter_dir.glob("*.m"):
                    self.matlab_files_by_name[mfile.name] = posix_rel(mfile, self.output_root)

    def discover_sections(self) -> None:
        for chapter_index, (label, chapter_cn, chapter_title) in enumerate(CHAPTERS, start=1):
            chapter_dir = self.manuscript_root / chapter_cn
            chapter_sections = []
            if chapter_dir.exists():
                for md_path in sorted(chapter_dir.glob("*.md"), key=section_key):
                    markdown_text = md_path.read_text(encoding="utf-8")
                    section = {
                        "chapter_label": label,
                        "chapter_cn": chapter_cn,
                        "chapter_title": chapter_title,
                        "chapter_index": chapter_index,
                        "source": md_path,
                        "title": extract_title(markdown_text, strip_number_prefix(md_path.stem)),
                        "slug": section_slug(md_path, chapter_index),
                        "summary": first_paragraph(markdown_text),
                    }
                    section["href"] = f"chapters/{section['slug']}"
                    self.sections.append(section)
                    chapter_sections.append(section)
            self.by_chapter.append(
                {
                    "label": label,
                    "cn": chapter_cn,
                    "title": chapter_title,
                    "index": chapter_index,
                    "sections": chapter_sections,
                    "pdf": self.pdf_by_chapter.get(chapter_cn),
                    "matlab": self.matlab_dir_by_chapter.get(chapter_cn),
                }
            )
        for index, section in enumerate(self.sections):
            section["prev"] = self.sections[index - 1] if index > 0 else None
            section["next"] = self.sections[index + 1] if index + 1 < len(self.sections) else None

    def copy_referenced_image(self, md_path: Path, href: str) -> str:
        href = href.strip()
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", href) or href.startswith("#"):
            return href
        clean_href = href.split("#", 1)[0].split("?", 1)[0]
        src = (md_path.parent / clean_href).resolve()
        if not src.exists():
            parts = Path(clean_href).parts
            if "figures" in parts:
                src = (self.figure_source_root / Path(*parts[parts.index("figures") + 1 :])).resolve()
        if not src.exists():
            return href
        try:
            rel_from_figures = src.relative_to(self.figure_source_root.resolve())
        except ValueError:
            rel_from_figures = Path(src.name)
        dest = self.figure_out / rel_from_figures
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return "../" + posix_rel(dest, self.output_root)

    def inline_convert(self, text: str, md_path: Path) -> str:
        code_tokens: list[str] = []

        def code_repl(match: re.Match[str]) -> str:
            raw = match.group(1)
            target = self.matlab_files_by_name.get(raw)
            escaped = html.escape(raw)
            if target:
                rendered = f'<a class="inline-code-link" href="{html_attr(github_blob_url(target))}"><code>{escaped}</code></a>'
            else:
                rendered = f"<code>{escaped}</code>"
            code_tokens.append(rendered)
            return f"@@CODE{len(code_tokens) - 1}@@"

        text = re.sub(r"`([^`]+)`", code_repl, text)

        image_tokens: list[str] = []

        def image_repl(match: re.Match[str]) -> str:
            alt = match.group(1).strip()
            src = self.copy_referenced_image(md_path, match.group(2).strip())
            rendered = f'<img src="{html_attr(url_path(src))}" alt="{html_attr(alt)}" loading="lazy">'
            image_tokens.append(rendered)
            return f"@@IMG{len(image_tokens) - 1}@@"

        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", image_repl, text)
        text = html.escape(text, quote=False)

        def link_repl(match: re.Match[str]) -> str:
            label = html.escape(match.group(1).strip())
            href = url_path(match.group(2).strip())
            return f'<a href="{html_attr(href)}">{label}</a>'

        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
        for index, rendered in enumerate(code_tokens):
            text = text.replace(f"@@CODE{index}@@", rendered)
        for index, rendered in enumerate(image_tokens):
            text = text.replace(f"@@IMG{index}@@", rendered)
        return text

    def render_table(self, lines: list[str], md_path: Path) -> str:
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
        if len(rows) < 2:
            return ""
        body = rows[2:] if re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[1]) else rows[1:]
        head_html = "".join(f"<th>{self.inline_convert(cell, md_path)}</th>" for cell in rows[0])
        body_html = "".join(
            "<tr>" + "".join(f"<td>{self.inline_convert(cell, md_path)}</td>" for cell in row) + "</tr>"
            for row in body
        )
        return f'<div class="table-wrap"><table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table></div>'

    def render_markdown(self, markdown_text: str, md_path: Path) -> str:
        lines = markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        out: list[str] = []
        paragraph: list[str] = []
        in_code = False
        code_lang = ""
        code_lines: list[str] = []
        in_math = False
        math_lines: list[str] = []
        heading_counter = 0

        def flush_paragraph() -> None:
            if paragraph:
                joined = " ".join(part.strip() for part in paragraph).strip()
                if joined:
                    out.append(f"<p>{self.inline_convert(joined, md_path)}</p>")
                paragraph.clear()

        index = 0
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if in_code:
                if stripped.startswith("```"):
                    lang_class = f"language-{html_attr(code_lang)}" if code_lang else ""
                    out.append(f'<pre><code class="{lang_class}">{html.escape(chr(10).join(code_lines))}</code></pre>')
                    in_code = False
                    code_lang = ""
                    code_lines = []
                else:
                    code_lines.append(line)
                index += 1
                continue
            if in_math:
                math_lines.append(line)
                if stripped == "$$":
                    out.append(f'<div class="math-block">{html.escape(chr(10).join(math_lines))}</div>')
                    in_math = False
                    math_lines = []
                index += 1
                continue
            if not stripped:
                flush_paragraph()
                index += 1
                continue
            if stripped.startswith("```"):
                flush_paragraph()
                in_code = True
                code_lang = stripped[3:].strip()
                index += 1
                continue
            if stripped == "$$":
                flush_paragraph()
                in_math = True
                math_lines = [line]
                index += 1
                continue
            heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading:
                flush_paragraph()
                level = len(heading.group(1))
                heading_counter += 1
                title = self.inline_convert(heading.group(2).strip(), md_path)
                out.append(f'<h{level} id="section-{heading_counter}">{title}</h{level}>')
                index += 1
                continue
            if (
                re.match(r"^\s*\|.*\|\s*$", line)
                and index + 1 < len(lines)
                and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1])
            ):
                flush_paragraph()
                table_lines = [line, lines[index + 1]]
                index += 2
                while index < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[index]):
                    table_lines.append(lines[index])
                    index += 1
                out.append(self.render_table(table_lines, md_path))
                continue
            if stripped.startswith(">"):
                flush_paragraph()
                quote_lines = []
                while index < len(lines) and lines[index].strip().startswith(">"):
                    quote_lines.append(lines[index].strip().lstrip(">").strip())
                    index += 1
                out.append(f"<blockquote>{self.inline_convert(' '.join(quote_lines), md_path)}</blockquote>")
                continue
            if re.match(r"^\s*[-*+]\s+", line):
                flush_paragraph()
                items = []
                while index < len(lines) and re.match(r"^\s*[-*+]\s+", lines[index]):
                    item = re.sub(r"^\s*[-*+]\s+", "", lines[index]).strip()
                    items.append(f"<li>{self.inline_convert(item, md_path)}</li>")
                    index += 1
                out.append("<ul>" + "".join(items) + "</ul>")
                continue
            if re.match(r"^\s*\d+[.)]\s+", line):
                flush_paragraph()
                items = []
                while index < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[index]):
                    item = re.sub(r"^\s*\d+[.)]\s+", "", lines[index]).strip()
                    items.append(f"<li>{self.inline_convert(item, md_path)}</li>")
                    index += 1
                out.append("<ol>" + "".join(items) + "</ol>")
                continue
            image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
            if image:
                flush_paragraph()
                alt = image.group(1).strip()
                src = self.copy_referenced_image(md_path, image.group(2).strip())
                out.append(
                    f'<figure><img src="{html_attr(url_path(src))}" alt="{html_attr(alt)}" loading="lazy">'
                    f"<figcaption>{html.escape(alt)}</figcaption></figure>"
                )
                index += 1
                continue
            paragraph.append(line)
            index += 1
        flush_paragraph()
        return "\n".join(out)

    def sidebar_html(self, current_slug: str = "") -> str:
        groups = []
        for chapter in self.by_chapter:
            if not chapter["sections"]:
                continue
            links = []
            for section in chapter["sections"]:
                active = " active" if section["slug"] == current_slug else ""
                href = "../" + section["href"]
                links.append(f'<a class="side-link{active}" href="{html_attr(url_path(href))}">{html.escape(section["title"])}</a>')
            groups.append(
                f'<div class="side-group"><div class="side-heading">{chapter["label"]} '
                f'{html.escape(chapter["title"])}</div>{"".join(links)}</div>'
            )
        return "".join(groups)

    def page_shell(self, title: str, body: str, description: str = INTRO, canonical_path: str = "") -> str:
        depth = "../" if canonical_path.startswith("chapters/") else ""
        canonical = SITE_URL.rstrip("/") + "/" + canonical_path.lstrip("/") if canonical_path else SITE_URL
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} | 易懂的雷达信号处理教程</title>
  <meta name="description" content="{html_attr(description)}">
  <link rel="canonical" href="{html_attr(canonical)}">
  <link rel="icon" href="{depth}design/icon-concepts/logo-mark-light.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{depth}assets/site.css">
  <script>
    window.MathJax = {{ tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']] }}, svg: {{ fontCache: 'global' }} }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
  <script defer src="{depth}assets/site.js"></script>
</head>
<body>
  <div class="read-progress" aria-hidden="true"><span></span></div>
  {body}
</body>
</html>
"""

    def render_index(self) -> str:
        cards = "\n".join(self.chapter_card(chapter) for chapter in self.by_chapter)
        latest = self.sections[0]["href"] if self.sections else "#"
        matlab_count = len(list((self.output_root / "matlab").rglob("*.m"))) if (self.output_root / "matlab").exists() else 0
        body = f"""
<header class="hero">
  <nav class="topbar">
    <a class="brand" href="./">
      <img src="design/icon-concepts/logo-mark-light.svg" alt="易懂的雷达信号处理教程图标">
      <span>Easy Radar Tutorial</span>
    </a>
    <div class="toplinks">
      <a href="#chapters">章节</a>
      <a href="{html_attr(github_tree_url('matlab'))}">MATLAB</a>
      <a href="{html_attr(github_tree_url('pdf'))}">PDF</a>
      <a href="{html_attr(GITHUB_URL)}">GitHub</a>
    </div>
  </nav>
  <div class="hero-grid">
    <div class="hero-copy reveal">
      <div class="eyebrow">静态网页版 / PDF / MATLAB 示例</div>
      <h1>易懂的雷达信号处理教程</h1>
      <p>{INTRO}</p>
      <div class="hero-actions">
        <a class="btn primary" href="{html_attr(url_path(latest))}">开始网页阅读</a>
        <a class="btn" href="#chapters">选择章节</a>
        <a class="btn ghost" href="{html_attr(GITHUB_URL)}">查看 GitHub 仓库</a>
      </div>
    </div>
    <aside class="signal-panel reveal" aria-label="教材特色">
      <div class="scope-ring"></div>
      <div class="metric"><span>8</span><small>章 PDF</small></div>
      <div class="metric"><span>{len(self.sections)}</span><small>个网页小节</small></div>
      <div class="metric"><span>{matlab_count}</span><small>个 MATLAB 脚本</small></div>
    </aside>
  </div>
</header>
<main>
  <section class="intro-strip reveal">
    <p><strong>发布原则：</strong>公开仓库只保留生成后的网页、PDF、图片和 MATLAB 示例；原始 Markdown 稿件继续留在作者本地工作区。</p>
  </section>
  <section id="chapters" class="chapters">
    <div class="section-head reveal">
      <p class="eyebrow">Read Online</p>
      <h2>在线章节</h2>
      <p>网页适合快速浏览与公式阅读；PDF 适合下载、打印和整章阅读；MATLAB 代码用于动手复现实验。</p>
    </div>
    <div class="chapter-grid">{cards}</div>
  </section>
</main>
<footer class="site-footer">
  <p>© 唐承乾. 本仓库内容按 LICENSE 中的条款发布。</p>
  <p><a href="{html_attr(GITHUB_URL)}">GitHub 仓库</a> · <a href="README.md">README</a> · <a href="LICENSE">LICENSE</a></p>
</footer>
"""
        return self.page_shell("首页", body, INTRO, "index.html")

    def chapter_card(self, chapter: dict) -> str:
        section_links = "".join(
            f'<a href="{html_attr(url_path(section["href"]))}">{html.escape(section["title"])}</a>' for section in chapter["sections"]
        )
        actions = []
        if chapter["sections"]:
            actions.append(f'<a class="btn primary" href="{html_attr(url_path(chapter["sections"][0]["href"]))}">网页阅读</a>')
        if chapter.get("pdf"):
            actions.append(f'<a class="btn" href="{html_attr(url_path(chapter["pdf"]))}">阅读 PDF</a>')
        if chapter.get("matlab"):
            actions.append(f'<a class="btn ghost" href="{html_attr(github_tree_url(chapter["matlab"]))}">MATLAB 代码</a>')
        return f"""<article class="chapter-card reveal">
      <div class="chapter-kicker">{chapter["label"]}</div>
      <h3>{html.escape(chapter["title"])}</h3>
      <p>{len(chapter["sections"])} 个网页小节；PDF 与配套代码保持同步发布。</p>
      <div class="chapter-actions">{''.join(actions)}</div>
      <details>
        <summary>查看小节目录</summary>
        <div class="section-list">{section_links}</div>
      </details>
    </article>"""

    def render_article(self, section: dict) -> str:
        article_html = self.render_markdown(section["source"].read_text(encoding="utf-8"), section["source"])
        chapter = self.by_chapter[section["chapter_index"] - 1]
        pdf_link = f'<a class="btn" href="../{html_attr(url_path(chapter["pdf"]))}">本章 PDF</a>' if chapter.get("pdf") else ""
        matlab_link = f'<a class="btn ghost" href="{html_attr(github_tree_url(chapter["matlab"]))}">本章 MATLAB</a>' if chapter.get("matlab") else ""
        prev_link = (
            f'<a class="pager-link" href="{html_attr(url_path(section["prev"]["slug"]))}">← {html.escape(section["prev"]["title"])}</a>'
            if section.get("prev")
            else "<span></span>"
        )
        next_link = (
            f'<a class="pager-link next" href="{html_attr(url_path(section["next"]["slug"]))}">{html.escape(section["next"]["title"])} →</a>'
            if section.get("next")
            else "<span></span>"
        )
        body = f"""
<header class="article-top">
  <nav class="topbar compact">
    <a class="brand" href="../index.html">
      <img src="../design/icon-concepts/logo-mark-light.svg" alt="易懂的雷达信号处理教程图标">
      <span>Easy Radar Tutorial</span>
    </a>
    <div class="toplinks">
      <a href="../index.html#chapters">章节</a>
      <a href="{html_attr(github_tree_url('matlab'))}">MATLAB</a>
      <a href="{html_attr(github_tree_url('pdf'))}">PDF</a>
      <a href="{html_attr(GITHUB_URL)}">GitHub</a>
    </div>
  </nav>
</header>
<div class="article-layout">
  <aside class="sidebar">
    <a class="back-home" href="../index.html">← 首页</a>
    {self.sidebar_html(section["slug"])}
  </aside>
  <main class="article-main reveal">
    <div class="article-meta">
      <span>{html.escape(section["chapter_label"])}</span>
      <span>{html.escape(section["chapter_title"])}</span>
    </div>
    <article class="prose">
      {article_html}
    </article>
    <div class="article-actions">
      {pdf_link}{matlab_link}<a class="btn ghost" href="{html_attr(GITHUB_URL)}">GitHub 仓库</a>
    </div>
    <nav class="pager">{prev_link}{next_link}</nav>
  </main>
</div>
"""
        return self.page_shell(section["title"], body, section["summary"] or INTRO, section["href"])

    def write_pages(self) -> None:
        (self.output_root / "index.html").write_text(self.render_index(), encoding="utf-8")
        (self.output_root / ".nojekyll").write_text("", encoding="utf-8")
        for section in self.sections:
            (self.chapter_out / section["slug"]).write_text(self.render_article(section), encoding="utf-8")

    def write_gitignore_guard(self) -> None:
        gitignore = self.output_root / ".gitignore"
        guard = """# Keep private manuscript sources out of the public repository.
*.md
!README.md

# Common private draft/source folders.
source/
sources/
drafts/
manuscript/
稿件/
手稿/
原稿/
"""
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if "Keep private manuscript sources out of the public repository." not in existing:
            gitignore.write_text((existing.rstrip() + "\n\n" + guard).lstrip(), encoding="utf-8")

    def write_assets(self) -> None:
        (self.asset_out / "site.css").write_text(CSS.strip() + "\n", encoding="utf-8")
        (self.asset_out / "site.js").write_text(JS.strip() + "\n", encoding="utf-8")


CSS = r"""
:root {
  --ink: #1d2524; --muted: #66716b; --paper: #fff8ed; --copper: #b76538;
  --copper-dark: #74391f; --navy: #12343a; --line: rgba(29,37,36,.16);
  --shadow: 0 24px 70px rgba(39,30,21,.16);
  --mono: "Cascadia Code", "Fira Code", "Consolas", monospace;
  --serif: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "SimSun", serif;
  --sans: "LXGW WenKai Screen", "Microsoft YaHei", "PingFang SC", sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; color: var(--ink); font-family: var(--serif); min-height: 100vh;
  background: radial-gradient(circle at 12% 8%, rgba(183,101,56,.20), transparent 34rem),
    radial-gradient(circle at 88% 0%, rgba(18,52,58,.18), transparent 30rem),
    linear-gradient(135deg, #fffaf1 0%, #f5ead8 48%, #fff8ed 100%);
}
a { color: inherit; text-decoration: none; }
a:hover { color: var(--copper-dark); }
.read-progress { position: fixed; inset: 0 0 auto; height: 4px; z-index: 20; }
.read-progress span { display: block; height: 100%; width: 0; background: linear-gradient(90deg, var(--copper), var(--navy)); }
.topbar { width: min(1180px, calc(100% - 40px)); margin: 0 auto; padding: 22px 0; display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.topbar.compact { width: min(1280px, calc(100% - 40px)); }
.brand { display: inline-flex; align-items: center; gap: 12px; font-family: var(--sans); font-weight: 700; letter-spacing: .02em; }
.brand img { width: 42px; height: 42px; }
.toplinks { display: flex; gap: 18px; align-items: center; color: var(--muted); font-family: var(--sans); font-size: 15px; }
.hero { min-height: 760px; position: relative; overflow: hidden; }
.hero::before { content: ""; position: absolute; right: -12vw; top: 120px; width: 48vw; aspect-ratio: 1; border-radius: 50%; background: repeating-radial-gradient(circle, rgba(18,52,58,.18) 0 2px, transparent 2px 32px); opacity: .8; }
.hero-grid { width: min(1180px, calc(100% - 40px)); margin: 58px auto 0; display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(320px, .9fr); gap: 56px; align-items: center; position: relative; }
.eyebrow { font-family: var(--sans); text-transform: uppercase; letter-spacing: .18em; font-size: 12px; color: var(--copper-dark); font-weight: 800; }
h1 { font-size: clamp(46px, 7vw, 88px); line-height: .98; letter-spacing: -.06em; margin: 18px 0 24px; }
.hero-copy p { font-size: clamp(18px, 2vw, 24px); color: #4e5a54; line-height: 1.8; max-width: 720px; }
.hero-actions, .chapter-actions, .article-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 28px; }
.btn { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 12px 18px; border: 1px solid rgba(29,37,36,.18); border-radius: 999px; background: rgba(255,255,255,.56); box-shadow: 0 8px 22px rgba(39,30,21,.08); font-family: var(--sans); font-weight: 700; }
.btn.primary { color: #fffaf1; border-color: transparent; background: linear-gradient(135deg, var(--navy), #23606a); }
.btn.ghost { background: transparent; }
.signal-panel { min-height: 420px; border: 1px solid rgba(29,37,36,.14); border-radius: 38px; background: linear-gradient(145deg, rgba(18,52,58,.92), rgba(116,57,31,.88)); color: #fff8ed; box-shadow: var(--shadow); position: relative; overflow: hidden; padding: 34px; display: grid; align-content: end; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.scope-ring { position: absolute; left: 50%; top: 42%; width: 320px; height: 320px; transform: translate(-50%, -50%); border-radius: 50%; background: linear-gradient(90deg, transparent 49%, rgba(156,203,183,.5) 50%, transparent 51%), linear-gradient(0deg, transparent 49%, rgba(156,203,183,.5) 50%, transparent 51%), repeating-radial-gradient(circle, transparent 0 42px, rgba(156,203,183,.28) 43px 44px); animation: pulse 5s ease-in-out infinite; }
.metric { position: relative; padding: 18px 12px; border-radius: 20px; background: rgba(255,248,237,.12); backdrop-filter: blur(8px); text-align: center; }
.metric span { display: block; font-size: 42px; font-weight: 900; font-family: var(--sans); }
.metric small { color: rgba(255,248,237,.78); }
main { width: min(1180px, calc(100% - 40px)); margin: 0 auto; }
.intro-strip { margin: -70px 0 70px; position: relative; padding: 22px 26px; border-radius: 24px; background: rgba(255,255,255,.72); border: 1px solid var(--line); box-shadow: var(--shadow); }
.intro-strip p { margin: 0; line-height: 1.8; color: #526059; }
.section-head { max-width: 760px; margin-bottom: 28px; }
h2 { font-size: clamp(32px, 4vw, 54px); margin: 8px 0 14px; letter-spacing: -.04em; }
.section-head p { color: var(--muted); line-height: 1.8; }
.chapter-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.chapter-card { padding: 28px; border: 1px solid var(--line); border-radius: 30px; background: rgba(255,255,255,.68); box-shadow: 0 16px 36px rgba(39,30,21,.08); }
.chapter-kicker { font-family: var(--sans); color: var(--copper-dark); font-weight: 900; }
.chapter-card h3 { font-size: 28px; margin: 8px 0 10px; }
.chapter-card p, .site-footer { color: var(--muted); line-height: 1.75; }
details { margin-top: 18px; color: var(--muted); }
summary { cursor: pointer; font-family: var(--sans); font-weight: 700; }
.section-list { display: grid; gap: 8px; margin-top: 12px; }
.section-list a { padding: 8px 0; border-bottom: 1px dashed rgba(29,37,36,.14); color: var(--ink); }
.site-footer { width: min(1180px, calc(100% - 40px)); margin: 80px auto 32px; padding-top: 24px; border-top: 1px solid var(--line); font-family: var(--sans); }
.article-top { position: sticky; top: 0; z-index: 10; background: rgba(255,248,237,.82); backdrop-filter: blur(16px); border-bottom: 1px solid var(--line); }
.article-layout { width: min(1280px, calc(100% - 32px)); margin: 0 auto; display: grid; grid-template-columns: 290px minmax(0, 1fr); gap: 44px; align-items: start; }
.sidebar { position: sticky; top: 90px; max-height: calc(100vh - 110px); overflow: auto; padding: 22px 0 40px; font-family: var(--sans); }
.back-home { display: inline-flex; margin-bottom: 18px; color: var(--copper-dark); font-weight: 800; }
.side-group { margin-bottom: 20px; }
.side-heading { margin: 8px 0; color: var(--muted); font-size: 13px; font-weight: 900; text-transform: uppercase; letter-spacing: .05em; }
.side-link { display: block; padding: 8px 10px; border-radius: 12px; color: #53605a; line-height: 1.35; font-size: 14px; }
.side-link.active { background: rgba(183,101,56,.13); color: var(--copper-dark); font-weight: 900; }
.article-main { padding: 44px 0 80px; min-width: 0; }
.article-meta { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 18px; }
.article-meta span { padding: 6px 10px; border-radius: 999px; background: rgba(183,101,56,.12); color: var(--copper-dark); font-family: var(--sans); font-size: 13px; font-weight: 800; }
.prose { padding: clamp(26px, 4vw, 56px); border: 1px solid var(--line); border-radius: 32px; background: rgba(255,255,255,.82); box-shadow: var(--shadow); }
.prose h1 { font-size: clamp(34px, 5vw, 58px); line-height: 1.12; margin: 0 0 28px; }
.prose h2 { font-size: clamp(26px, 3vw, 38px); margin-top: 54px; padding-top: 16px; border-top: 1px solid rgba(29,37,36,.1); }
.prose h3 { font-size: 24px; margin-top: 36px; }
.prose p, .prose li, .prose blockquote { font-size: 18px; line-height: 2.02; }
.prose p { margin: 18px 0; }
.prose ul, .prose ol { padding-left: 1.5em; }
.prose li { margin: 8px 0; }
.prose a { color: var(--copper-dark); border-bottom: 1px solid rgba(183,101,56,.35); }
.prose code { font-family: var(--mono); font-size: .92em; background: rgba(18,52,58,.08); border-radius: 7px; padding: .12em .38em; }
.inline-code-link { border-bottom: none !important; }
.prose pre { overflow: auto; padding: 18px; border-radius: 18px; background: #102b2f; color: #f7ead6; box-shadow: inset 0 0 0 1px rgba(255,255,255,.08); }
.prose pre code { background: transparent; padding: 0; color: inherit; }
.prose blockquote { margin: 26px 0; padding: 18px 22px; border-left: 5px solid var(--copper); background: rgba(183,101,56,.09); border-radius: 0 18px 18px 0; color: #4d5c55; }
.math-block, .table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 16px; background: rgba(255,255,255,.5); }
th, td { padding: 12px 14px; border: 1px solid rgba(29,37,36,.14); text-align: left; vertical-align: top; }
th { background: rgba(18,52,58,.08); font-family: var(--sans); }
figure { margin: 30px 0; }
figure img { display: block; max-width: 100%; height: auto; border-radius: 20px; box-shadow: 0 18px 44px rgba(39,30,21,.14); margin: 0 auto; background: #fff; }
figcaption { margin-top: 10px; color: var(--muted); text-align: center; font-family: var(--sans); font-size: 14px; }
.pager { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 34px; }
.pager-link { padding: 18px; border-radius: 18px; border: 1px solid var(--line); background: rgba(255,255,255,.68); font-family: var(--sans); font-weight: 800; }
.pager-link.next { text-align: right; }
.reveal { animation: lift .65s ease both; }
@keyframes lift { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pulse { 0%,100% { transform: translate(-50%, -50%) scale(.96); opacity: .74; } 50% { transform: translate(-50%, -50%) scale(1.04); opacity: 1; } }
@media (max-width: 920px) {
  .topbar, .topbar.compact { width: min(100% - 24px, 760px); align-items: flex-start; }
  .toplinks { overflow-x: auto; max-width: 100%; padding-bottom: 4px; }
  .hero { min-height: auto; padding-bottom: 80px; }
  .hero-grid { grid-template-columns: 1fr; margin-top: 24px; }
  .signal-panel { min-height: 300px; }
  .chapter-grid, .article-layout, .pager { grid-template-columns: 1fr; }
  .intro-strip { margin-top: 0; }
  .sidebar { position: relative; top: auto; max-height: none; padding-bottom: 0; }
  .side-group { display: none; }
  .article-main { padding-top: 18px; }
  .prose { padding: 24px; border-radius: 24px; }
  .prose p, .prose li, .prose blockquote { font-size: 17px; line-height: 1.9; }
  .pager-link.next { text-align: left; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; scroll-behavior: auto !important; }
}
"""


JS = r"""
(function () {
  const bar = document.querySelector('.read-progress span');
  function updateProgress() {
    if (!bar) return;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const pct = max > 0 ? (window.scrollY / max) * 100 : 0;
    bar.style.width = pct.toFixed(2) + '%';
  }
  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', updateProgress);
  updateProgress();
})();
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static HTML from private Markdown manuscripts.")
    parser.add_argument("--source-root", required=True, type=Path, help="Private source root that contains 手稿/ and figures/.")
    parser.add_argument("--output-root", default=Path.cwd(), type=Path, help="Public repository root.")
    args = parser.parse_args()
    SiteBuilder(args.source_root.resolve(), args.output_root.resolve()).build()


if __name__ == "__main__":
    main()
