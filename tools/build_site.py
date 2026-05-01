#!/usr/bin/env python3
"""Build the public static site from the private Zhihu-ready Markdown files.

The published site is one HTML page per chapter. The source Markdown is not
copied into this repository; images keep the online URLs already present in the
Zhihu version.
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
    ("ch01", "第一章", "第1章", "雷达是什么"),
    ("ch02", "第二章", "第2章", "信号基础"),
    ("ch03", "第三章", "第3章", "雷达信号的生成与接收"),
    ("ch04", "第四章", "第4章", "距离测量"),
    ("ch05", "第五章", "第5章", "速度测量"),
    ("ch06", "第六章", "第6章", "目标检测"),
    ("ch07", "第七章", "第7章", "测角"),
    ("ch08", "第八章", "第8章", "完整处理流程"),
]

INTRO = "一本从直觉出发的雷达信号处理入门教程。"
GITHUB_URL = "https://github.com/apple-art/easy-radar-tutorial"
SITE_URL = "https://apple-art.github.io/easy-radar-tutorial/"
DEFAULT_SOURCE_DIR = Path(r"D:\Obsidian\唐承乾的笔记本\雷达教材\知乎版\系列文章")
PROMO_CUTOFF_MARKERS = (
    "相关资料放在了公众号",
    "后台回复：**雷达**",
    "即可获取：",
    "欢迎关注我的**“知乎专栏”**与**“公众号”**",
)


def url_path(path: str) -> str:
    return urllib.parse.quote(path, safe="/:#?&=%")


def html_attr(text: str) -> str:
    return html.escape(text, quote=True)


def posix_rel(path: Path, start: Path) -> str:
    return Path(os.path.relpath(path, start)).as_posix()


def github_tree_url(rel_path: str) -> str:
    return f"{GITHUB_URL}/tree/main/{url_path(rel_path).rstrip('/')}"


def github_blob_url(rel_path: str) -> str:
    return f"{GITHUB_URL}/blob/main/{url_path(rel_path)}"


def reset_dir(path: Path, root: Path) -> None:
    resolved = path.resolve()
    root_resolved = root.resolve()
    if root_resolved not in resolved.parents and resolved != root_resolved:
        raise RuntimeError(f"Refusing to delete outside output root: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def remove_generated_dir(path: Path, root: Path) -> None:
    resolved = path.resolve()
    root_resolved = root.resolve()
    if path.exists():
        if root_resolved not in resolved.parents and resolved != root_resolved:
            raise RuntimeError(f"Refusing to delete outside output root: {resolved}")
        shutil.rmtree(path)


def is_remote_url(value: str) -> bool:
    return re.match(r"^https?://", value.strip(), flags=re.IGNORECASE) is not None


def section_sort_key(path: Path) -> tuple[int, int, str]:
    match = re.search(r"_(\d+)\.(\d+)_", path.name)
    if match:
        return int(match.group(1)), int(match.group(2)), path.name
    if path.name.startswith("第一章"):
        return 1, 1, path.name
    return 99, 99, path.name


def clean_title(title: str) -> str:
    title = title.strip()
    title = re.sub(r"^易懂的雷达信号处理书\s*\|\s*第\d+章\s*", "", title)
    return title.strip()


def clean_markdown(markdown_text: str) -> str:
    """Remove platform-specific copy from the Zhihu version before publishing."""
    cleaned_lines: list[str] = []
    for line in markdown_text.splitlines():
        if any(marker in line for marker in PROMO_CUTOFF_MARKERS):
            break
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)
    text = text.replace("可到公众号下载配套附件后运行", "可直接运行")
    text = text.replace("到公众号下载配套附件后运行", "直接运行")
    text = text.replace("如果你想把这些数量级和曲线一起看，可到公众号下载配套附件后运行", "如果你想把这些数量级和曲线一起看，可直接运行")
    text = text.replace("如果你想把时域和频域的差别直观看出来，可到公众号下载配套附件后运行", "如果你想把时域和频域的差别直观看出来，可直接运行")
    return text


def extract_title(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return clean_title(match.group(1))
    return fallback


def paragraph_summary(markdown_text: str) -> str:
    captured: list[str] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("![") or stripped == "$$":
            if captured:
                break
            continue
        if stripped in {"---", "***", "___"}:
            continue
        if stripped.startswith("```") or stripped.startswith("|"):
            continue
        captured.append(stripped)
        if len("".join(captured)) > 110:
            break
    text = " ".join(captured)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    return text[:120] + ("..." if len(text) > 120 else "")


class MarkdownRenderer:
    def __init__(self, matlab_files_by_name: dict[str, str]) -> None:
        self.matlab_files_by_name = matlab_files_by_name
        self.heading_counter = 0

    def inline(self, text: str) -> str:
        code_tokens: list[str] = []

        def code_repl(match: re.Match[str]) -> str:
            raw = match.group(1)
            escaped = html.escape(raw)
            target = self.matlab_files_by_name.get(raw)
            if target:
                rendered = f'<a class="inline-code-link" href="{html_attr(github_blob_url(target))}"><code>{escaped}</code></a>'
            else:
                rendered = f"<code>{escaped}</code>"
            code_tokens.append(rendered)
            return f"@@CODE{len(code_tokens) - 1}@@"

        image_tokens: list[str] = []

        def image_repl(match: re.Match[str]) -> str:
            alt = match.group(1).strip()
            src = match.group(2).strip()
            if not is_remote_url(src):
                raise ValueError(f"Image must use an online URL: {src}")
            rendered = f'<img src="{html_attr(url_path(src))}" alt="{html_attr(alt)}" loading="lazy">'
            image_tokens.append(rendered)
            return f"@@IMG{len(image_tokens) - 1}@@"

        text = re.sub(r"`([^`]+)`", code_repl, text)
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

    def table(self, lines: list[str]) -> str:
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
        if len(rows) < 2:
            return ""
        body = rows[2:] if re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[1]) else rows[1:]
        head_html = "".join(f"<th>{self.inline(cell)}</th>" for cell in rows[0])
        body_html = "".join(
            "<tr>" + "".join(f"<td>{self.inline(cell)}</td>" for cell in row) + "</tr>" for row in body
        )
        return f'<div class="table-wrap"><table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table></div>'

    def render(self, markdown_text: str, section_id: str, section_title: str) -> str:
        lines = markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        out: list[str] = []
        paragraph: list[str] = []
        in_code = False
        code_lang = ""
        code_lines: list[str] = []
        in_math = False
        math_lines: list[str] = []
        first_h1_done = False

        def flush_paragraph() -> None:
            if paragraph:
                joined = " ".join(part.strip() for part in paragraph).strip()
                if joined:
                    out.append(f"<p>{self.inline(joined)}</p>")
                paragraph.clear()

        index = 0
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if in_code:
                if stripped.startswith("```"):
                    css_class = f"language-{html_attr(code_lang)}" if code_lang else ""
                    out.append(f'<pre><code class="{css_class}">{html.escape(chr(10).join(code_lines))}</code></pre>')
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
            if stripped in {"---", "***", "___"}:
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
                title = clean_title(heading.group(2))
                if level == 1 and not first_h1_done:
                    out.append(f'<h2 id="{section_id}" class="section-title">{html.escape(section_title)}</h2>')
                    first_h1_done = True
                else:
                    self.heading_counter += 1
                    out.append(f'<h{min(level + 1, 6)} id="sub-{self.heading_counter}">{self.inline(title)}</h{min(level + 1, 6)}>')
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
                out.append(self.table(table_lines))
                continue
            if stripped.startswith(">"):
                flush_paragraph()
                quote_lines = []
                while index < len(lines) and lines[index].strip().startswith(">"):
                    quote_lines.append(lines[index].strip().lstrip(">").strip())
                    index += 1
                out.append(f"<blockquote>{self.inline(' '.join(quote_lines))}</blockquote>")
                continue
            if re.match(r"^\s*[-*+]\s+", line):
                flush_paragraph()
                items = []
                while index < len(lines) and re.match(r"^\s*[-*+]\s+", lines[index]):
                    item = re.sub(r"^\s*[-*+]\s+", "", lines[index]).strip()
                    items.append(f"<li>{self.inline(item)}</li>")
                    index += 1
                out.append("<ul>" + "".join(items) + "</ul>")
                continue
            if re.match(r"^\s*\d+[.)]\s+", line):
                flush_paragraph()
                items = []
                while index < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[index]):
                    item = re.sub(r"^\s*\d+[.)]\s+", "", lines[index]).strip()
                    items.append(f"<li>{self.inline(item)}</li>")
                    index += 1
                out.append("<ol>" + "".join(items) + "</ol>")
                continue
            image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
            if image:
                flush_paragraph()
                alt = image.group(1).strip()
                src = image.group(2).strip()
                if not is_remote_url(src):
                    raise ValueError(f"Image must use an online URL: {src}")
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


class SiteBuilder:
    def __init__(self, source_dir: Path, output_root: Path) -> None:
        self.source_dir = source_dir
        self.output_root = output_root
        self.chapter_out = output_root / "chapters"
        self.asset_out = output_root / "assets"
        self.figure_out = output_root / "figures"
        self.pdf_by_chapter: dict[str, str] = {}
        self.matlab_by_chapter: dict[str, str] = {}
        self.matlab_files_by_name: dict[str, str] = {}
        self.chapters: list[dict] = []

    def build(self) -> None:
        self.validate_source_dir()
        self.validate_public_repo()
        reset_dir(self.chapter_out, self.output_root)
        reset_dir(self.asset_out, self.output_root)
        remove_generated_dir(self.figure_out, self.output_root)
        self.discover_assets()
        self.discover_chapters()
        self.write_assets()
        self.write_pages()
        self.write_gitignore_guard()
        print(f"Generated {len(self.chapters)} chapter pages")
        print("Images: online links from Zhihu Markdown; no local figure copies")

    def validate_source_dir(self) -> None:
        if self.source_dir.resolve() != DEFAULT_SOURCE_DIR.resolve():
            raise RuntimeError(f"Unexpected source directory: {self.source_dir}. Expected: {DEFAULT_SOURCE_DIR}")
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")

    def validate_public_repo(self) -> None:
        blocked_dirs = {"知乎版", "稿件", "手稿", "原稿", "source", "sources", "drafts", "manuscript"}
        for child in self.output_root.iterdir():
            if child.is_dir() and child.name in blocked_dirs:
                raise RuntimeError(f"Refusing to build with private source directory in public repo: {child}")
        leaked_markdown = [p for p in self.output_root.rglob("*.md") if p.name != "README.md" and ".git" not in p.parts]
        if leaked_markdown:
            listed = "\n".join(str(p) for p in leaked_markdown[:10])
            raise RuntimeError(f"Private Markdown files found in public repo:\n{listed}")

    def discover_assets(self) -> None:
        pdf_root = self.output_root / "pdf"
        if pdf_root.exists():
            for pdf in sorted(pdf_root.glob("*.pdf")):
                for _, chapter_cn, _, _ in CHAPTERS:
                    if chapter_cn in pdf.name:
                        self.pdf_by_chapter[chapter_cn] = posix_rel(pdf, self.output_root)
                        break
        matlab_root = self.output_root / "matlab"
        if matlab_root.exists():
            for chapter_dir in sorted([p for p in matlab_root.iterdir() if p.is_dir()]):
                self.matlab_by_chapter[chapter_dir.name] = posix_rel(chapter_dir, self.output_root)
                for mfile in chapter_dir.glob("*.m"):
                    self.matlab_files_by_name[mfile.name] = posix_rel(mfile, self.output_root)

    def discover_chapters(self) -> None:
        for chapter_slug, chapter_cn, chapter_label, chapter_title in CHAPTERS:
            files = sorted(self.source_dir.glob(f"{chapter_cn}_*.md"), key=section_sort_key)
            sections = []
            for section_index, path in enumerate(files, start=1):
                text = path.read_text(encoding="utf-8")
                text = clean_markdown(text)
                fallback = path.stem.split("_", 1)[-1].replace("_", " ")
                section_id = f"{chapter_slug}-s{section_index:02d}"
                sections.append(
                    {
                        "path": path,
                        "id": section_id,
                        "title": extract_title(text, fallback),
                        "summary": paragraph_summary(text),
                        "text": text,
                    }
                )
            self.chapters.append(
                {
                    "slug": chapter_slug,
                    "cn": chapter_cn,
                    "label": chapter_label,
                    "title": chapter_title,
                    "href": f"chapters/{chapter_slug}.html",
                    "sections": sections,
                    "pdf": self.pdf_by_chapter.get(chapter_cn),
                    "matlab": self.matlab_by_chapter.get(chapter_cn),
                }
            )

    def write_pages(self) -> None:
        (self.output_root / "index.html").write_text(self.render_index(), encoding="utf-8")
        (self.output_root / ".nojekyll").write_text("", encoding="utf-8")
        renderer = MarkdownRenderer(self.matlab_files_by_name)
        for chapter in self.chapters:
            (self.chapter_out / f"{chapter['slug']}.html").write_text(self.render_chapter(chapter, renderer), encoding="utf-8")

    def render_index(self) -> str:
        cards = []
        for chapter in self.chapters:
            actions = [f'<a class="btn primary" href="{html_attr(url_path(chapter["href"]))}">网页阅读</a>']
            if chapter.get("pdf"):
                actions.append(f'<a class="btn" href="{html_attr(url_path(chapter["pdf"]))}">阅读 PDF</a>')
            if chapter.get("matlab"):
                actions.append(f'<a class="btn ghost" href="{html_attr(github_tree_url(chapter["matlab"]))}">MATLAB 代码</a>')
            cards.append(
                f"""<article class="chapter-card reveal">
      <div class="chapter-kicker">{chapter["label"]}</div>
      <h3>{html.escape(chapter["title"])}</h3>
      <div class="chapter-actions">{''.join(actions)}</div>
    </article>"""
            )
        body = f"""
<header class="hero">
  <nav class="topbar">
    <a class="brand" href="./"><img src="design/icon-concepts/logo-mark-light.svg" alt="教程图标"><span>Easy Radar Tutorial</span></a>
    <div class="toplinks"><a href="#chapters">章节</a><a href="{html_attr(github_tree_url('matlab'))}">MATLAB</a><a href="{html_attr(github_tree_url('pdf'))}">PDF</a><a href="{html_attr(GITHUB_URL)}">GitHub</a></div>
  </nav>
  <div class="hero-grid">
    <div class="hero-copy reveal">
      <div class="eyebrow">One chapter, one page</div>
      <h1>易懂的雷达信号处理教程</h1>
      <p>从雷达是什么开始，一路讲到距离、速度、检测、测角和完整 MATLAB 处理流程。</p>
      <div class="hero-actions"><a class="btn primary" href="chapters/ch01.html">开始阅读</a><a class="btn" href="#chapters">选择章节</a><a class="btn ghost" href="{html_attr(github_tree_url('matlab'))}">MATLAB 代码</a></div>
    </div>
    <aside class="signal-panel reveal" aria-label="教材数据">
      <div class="scope-ring"></div><div class="metric"><span>8</span><small>章网页</small></div><div class="metric"><span>{sum(len(c["sections"]) for c in self.chapters)}</span><small>个小节</small></div><div class="metric"><span>{len(self.matlab_files_by_name)}</span><small>个 MATLAB 脚本</small></div>
    </aside>
  </div>
</header>
<main>
  <section id="chapters" class="chapters">
    <div class="section-head reveal"><p class="eyebrow">Read Online</p><h2>在线章节</h2><p>每一章是一整页，左侧目录用于章节内跳转；PDF 保留给下载、打印和离线阅读。</p></div>
    <div class="chapter-grid">{''.join(cards)}</div>
  </section>
</main>
<footer class="site-footer"><p>© 唐承乾. 本仓库内容按 LICENSE 中的条款发布。</p><p><a href="{html_attr(GITHUB_URL)}">GitHub 仓库</a> · <a href="LICENSE">LICENSE</a></p></footer>
"""
        return self.shell("首页", body, "index.html", INTRO)

    def render_chapter(self, chapter: dict, renderer: MarkdownRenderer) -> str:
        section_html = []
        for section in chapter["sections"]:
            section_html.append(
                f'<section class="chapter-section" data-section="{html_attr(section["id"])}">'
                + renderer.render(section["text"], section["id"], section["title"])
                + "</section>"
            )
        sidebar_items = []
        for item in self.chapters:
            chapter_link = (
                f'<a class="chapter-toc-link{" active" if item["slug"] == chapter["slug"] else ""}" '
                f'href="{html_attr(url_path(item["slug"] + ".html"))}">{html.escape(item["label"])} {html.escape(item["title"])}</a>'
            )
            if item["slug"] == chapter["slug"]:
                subsection_links = "".join(
                    f'<a class="toc-link" href="#{html_attr(section["id"])}">{html.escape(section["title"])}</a>'
                    for section in item["sections"]
                )
                chapter_link += f'<div class="chapter-subtoc">{subsection_links}</div>'
            sidebar_items.append(f'<div class="book-toc-group">{chapter_link}</div>')
        sidebar = "".join(sidebar_items)
        actions = []
        if chapter.get("pdf"):
            actions.append(f'<a class="btn" href="../{html_attr(url_path(chapter["pdf"]))}">本章 PDF</a>')
        if chapter.get("matlab"):
            actions.append(f'<a class="btn ghost" href="{html_attr(github_tree_url(chapter["matlab"]))}">本章 MATLAB</a>')
        body = f"""
<header class="article-top">
  <nav class="topbar compact">
    <a class="brand" href="../index.html"><img src="../design/icon-concepts/logo-mark-light.svg" alt="教程图标"><span>Easy Radar Tutorial</span></a>
    <div class="toplinks"><a href="../index.html#chapters">章节</a><a href="{html_attr(github_tree_url('matlab'))}">MATLAB</a><a href="{html_attr(github_tree_url('pdf'))}">PDF</a><a href="{html_attr(GITHUB_URL)}">GitHub</a></div>
  </nav>
</header>
<div class="article-layout">
  <aside class="sidebar">
    <a class="back-home" href="../index.html">← 首页</a>
    <nav class="book-toc">{sidebar}</nav>
  </aside>
  <main class="article-main reveal">
    <div class="article-meta"><span>{html.escape(chapter["label"])}</span><span>{html.escape(chapter["title"])}</span></div>
    <article class="prose chapter-prose">
      <h1>{html.escape(chapter["label"])} {html.escape(chapter["title"])}</h1>
      {''.join(section_html)}
    </article>
    <div class="article-actions">{''.join(actions)}<a class="btn ghost" href="{html_attr(GITHUB_URL)}">GitHub 仓库</a></div>
  </main>
</div>
"""
        summary = chapter["sections"][0]["summary"] if chapter["sections"] else INTRO
        return self.shell(f'{chapter["label"]} {chapter["title"]}', body, chapter["href"], summary)

    def shell(self, title: str, body: str, canonical_path: str, description: str) -> str:
        depth = "../" if canonical_path.startswith("chapters/") else ""
        canonical = SITE_URL.rstrip("/") + "/" + canonical_path.lstrip("/")
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
  <script>window.MathJax = {{ tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']] }}, svg: {{ fontCache: 'global' }} }};</script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
  <script defer src="{depth}assets/site.js"></script>
</head>
<body><div class="read-progress" aria-hidden="true"><span></span></div>{body}</body>
</html>
"""

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
知乎版/
"""
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if "Keep private manuscript sources out of the public repository." not in existing:
            gitignore.write_text((existing.rstrip() + "\n\n" + guard).lstrip(), encoding="utf-8")
        elif "知乎版/" not in existing:
            gitignore.write_text(existing.rstrip() + "\n知乎版/\n", encoding="utf-8")

    def write_assets(self) -> None:
        (self.asset_out / "site.css").write_text(CSS.strip() + "\n", encoding="utf-8")
        (self.asset_out / "site.js").write_text(JS.strip() + "\n", encoding="utf-8")


CSS = r"""
:root {
  --ink:#1d2524; --muted:#66716b; --paper:#fff8ed; --copper:#b76538;
  --copper-dark:#74391f; --navy:#12343a; --line:rgba(29,37,36,.16);
  --shadow:0 24px 70px rgba(39,30,21,.16);
  --mono:"Cascadia Code","Fira Code","Consolas",monospace;
  --serif:"Noto Serif SC","Source Han Serif SC","Songti SC","SimSun",serif;
  --sans:"LXGW WenKai Screen","Microsoft YaHei","PingFang SC",sans-serif;
}
*{box-sizing:border-box} html{scroll-behavior:smooth} body{margin:0;color:var(--ink);font-family:var(--serif);background:radial-gradient(circle at 12% 8%,rgba(183,101,56,.20),transparent 34rem),radial-gradient(circle at 88% 0%,rgba(18,52,58,.18),transparent 30rem),linear-gradient(135deg,#fffaf1 0%,#f5ead8 48%,#fff8ed 100%);min-height:100vh}
a{color:inherit;text-decoration:none} a:hover{color:var(--copper-dark)}
.read-progress{position:fixed;inset:0 0 auto;height:4px;z-index:30}.read-progress span{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--copper),var(--navy))}
.topbar{width:min(1180px,calc(100% - 40px));margin:0 auto;padding:22px 0;display:flex;align-items:center;justify-content:space-between;gap:24px}.topbar.compact{width:min(1320px,calc(100% - 40px))}
.brand{display:inline-flex;align-items:center;gap:12px;font-family:var(--sans);font-weight:800}.brand img{width:42px;height:42px}.toplinks{display:flex;gap:18px;align-items:center;color:var(--muted);font-family:var(--sans);font-size:15px}
.hero{min-height:720px;position:relative;overflow:hidden}.hero:before{content:"";position:absolute;right:-12vw;top:120px;width:48vw;aspect-ratio:1;border-radius:50%;background:repeating-radial-gradient(circle,rgba(18,52,58,.18) 0 2px,transparent 2px 32px);opacity:.8}
.hero-grid{width:min(1180px,calc(100% - 40px));margin:58px auto 0;display:grid;grid-template-columns:minmax(0,1.1fr) minmax(320px,.9fr);gap:56px;align-items:center;position:relative}.eyebrow{font-family:var(--sans);text-transform:uppercase;letter-spacing:.18em;font-size:12px;color:var(--copper-dark);font-weight:900}
h1{font-size:clamp(46px,7vw,88px);line-height:.98;letter-spacing:-.06em;margin:18px 0 24px}.hero-copy p{font-size:clamp(18px,2vw,24px);color:#4e5a54;line-height:1.8;max-width:720px}
.hero-actions,.chapter-actions,.article-actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:12px 18px;border:1px solid rgba(29,37,36,.18);border-radius:999px;background:rgba(255,255,255,.56);box-shadow:0 8px 22px rgba(39,30,21,.08);font-family:var(--sans);font-weight:800}.btn.primary{color:#fffaf1;border-color:transparent;background:linear-gradient(135deg,var(--navy),#23606a)}.btn.ghost{background:transparent}
.signal-panel{min-height:420px;border:1px solid rgba(29,37,36,.14);border-radius:38px;background:linear-gradient(145deg,rgba(18,52,58,.92),rgba(116,57,31,.88));color:#fff8ed;box-shadow:var(--shadow);position:relative;overflow:hidden;padding:34px;display:grid;align-content:end;grid-template-columns:repeat(3,1fr);gap:12px}.scope-ring{position:absolute;left:50%;top:42%;width:320px;height:320px;transform:translate(-50%,-50%);border-radius:50%;background:linear-gradient(90deg,transparent 49%,rgba(156,203,183,.5) 50%,transparent 51%),linear-gradient(0deg,transparent 49%,rgba(156,203,183,.5) 50%,transparent 51%),repeating-radial-gradient(circle,transparent 0 42px,rgba(156,203,183,.28) 43px 44px);animation:pulse 5s ease-in-out infinite}.metric{position:relative;padding:18px 12px;border-radius:20px;background:rgba(255,248,237,.12);backdrop-filter:blur(8px);text-align:center}.metric span{display:block;font-size:42px;font-weight:900;font-family:var(--sans)}.metric small{color:rgba(255,248,237,.78)}
main{width:min(1180px,calc(100% - 40px));margin:0 auto}.intro-strip{margin:-70px 0 70px;position:relative;padding:22px 26px;border-radius:24px;background:rgba(255,255,255,.72);border:1px solid var(--line);box-shadow:var(--shadow)}.intro-strip p{margin:0;line-height:1.8;color:#526059}.section-head{max-width:760px;margin-bottom:28px}h2{font-size:clamp(32px,4vw,54px);margin:8px 0 14px;letter-spacing:-.04em}.section-head p{color:var(--muted);line-height:1.8}
.chapter-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.chapter-card{padding:28px;border:1px solid var(--line);border-radius:30px;background:rgba(255,255,255,.68);box-shadow:0 16px 36px rgba(39,30,21,.08)}.chapter-kicker{font-family:var(--sans);color:var(--copper-dark);font-weight:900}.chapter-card h3{font-size:28px;margin:8px 0 10px}.chapter-card p,.site-footer{color:var(--muted);line-height:1.75}.site-footer{width:min(1180px,calc(100% - 40px));margin:80px auto 32px;padding-top:24px;border-top:1px solid var(--line);font-family:var(--sans)}
.article-top{position:sticky;top:0;z-index:20;background:rgba(255,248,237,.82);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}.article-layout{width:min(1360px,calc(100% - 32px));margin:0 auto;display:grid;grid-template-columns:340px minmax(0,1fr);gap:44px;align-items:start}.sidebar{position:sticky;top:90px;max-height:calc(100vh - 110px);overflow:auto;padding:22px 0 40px;font-family:var(--sans)}.back-home{display:inline-flex;margin-bottom:18px;color:var(--copper-dark);font-weight:900}.book-toc{display:grid;gap:10px}.book-toc-group{display:grid;gap:6px}.chapter-toc-link{display:block;padding:10px 12px;border-radius:16px;color:#5d6a64;font-weight:900;line-height:1.35}.chapter-toc-link:hover{background:rgba(255,255,255,.56)}.chapter-toc-link.active{color:var(--copper-dark);background:rgba(183,101,56,.10)}.chapter-subtoc{display:grid;gap:4px;margin:2px 0 10px 16px;padding-left:14px;border-left:2px solid rgba(183,101,56,.20)}.toc-link{display:block;padding:10px 12px;border-radius:16px;color:#52605b;line-height:1.35;font-size:15px}.toc-link.active{background:#efdac6;color:var(--copper-dark);font-weight:900}
.article-main{padding:44px 0 80px;min-width:0}.article-meta{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:18px}.article-meta span{padding:6px 10px;border-radius:999px;background:rgba(183,101,56,.12);color:var(--copper-dark);font-family:var(--sans);font-size:13px;font-weight:900}.prose{padding:clamp(26px,4vw,56px);border:1px solid var(--line);border-radius:32px;background:rgba(255,255,255,.82);box-shadow:var(--shadow)}.prose h1{font-size:clamp(34px,5vw,58px);line-height:1.12;margin:0 0 34px}.section-title{font-size:clamp(28px,3.4vw,42px);line-height:1.25;margin:72px 0 26px;padding-top:28px;border-top:1px solid rgba(29,37,36,.13);letter-spacing:-.03em}.chapter-section:first-of-type .section-title{margin-top:14px;border-top:0;padding-top:0}.prose h3{font-size:24px;margin-top:38px}.prose h4{font-size:21px;margin-top:30px}.prose p,.prose li,.prose blockquote{font-size:18px;line-height:2.02}.prose p{margin:18px 0}.prose ul,.prose ol{padding-left:1.5em}.prose li{margin:8px 0}.prose a{color:var(--copper-dark);border-bottom:1px solid rgba(183,101,56,.35)}.prose code{font-family:var(--mono);font-size:.92em;background:rgba(18,52,58,.08);border-radius:7px;padding:.12em .38em}.inline-code-link{border-bottom:none!important}.prose pre{overflow:auto;padding:18px;border-radius:18px;background:#102b2f;color:#f7ead6;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08)}.prose pre code{background:transparent;padding:0;color:inherit}.prose blockquote{margin:26px 0;padding:18px 22px;border-left:5px solid var(--copper);background:rgba(183,101,56,.09);border-radius:0 18px 18px 0;color:#4d5c55}.math-block,.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:16px;background:rgba(255,255,255,.5)}th,td{padding:12px 14px;border:1px solid rgba(29,37,36,.14);text-align:left;vertical-align:top}th{background:rgba(18,52,58,.08);font-family:var(--sans)}figure{margin:32px 0}figure img{display:block;max-width:100%;height:auto;border-radius:20px;box-shadow:0 18px 44px rgba(39,30,21,.14);margin:0 auto;background:#fff}figcaption{margin-top:10px;color:var(--muted);text-align:center;font-family:var(--sans);font-size:14px}
.reveal{animation:lift .65s ease both}@keyframes lift{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}@keyframes pulse{0%,100%{transform:translate(-50%,-50%) scale(.96);opacity:.74}50%{transform:translate(-50%,-50%) scale(1.04);opacity:1}}
@media(max-width:920px){.topbar,.topbar.compact{width:min(100% - 24px,760px);align-items:flex-start}.toplinks{overflow-x:auto;max-width:100%;padding-bottom:4px}.hero{min-height:auto;padding-bottom:80px}.hero-grid,.chapter-grid,.article-layout{grid-template-columns:1fr}.hero-grid{margin-top:24px}.signal-panel{min-height:300px}.intro-strip{margin-top:0}.sidebar{position:relative;top:auto;max-height:none;padding-bottom:0}.toc{grid-template-columns:1fr}.article-main{padding-top:18px}.prose{padding:24px;border-radius:24px}.prose p,.prose li,.prose blockquote{font-size:17px;line-height:1.9}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;scroll-behavior:auto!important}}
"""


JS = r"""
(function(){
  const bar=document.querySelector('.read-progress span');
  const links=[...document.querySelectorAll('.toc-link')];
  const sections=links.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
  function updateProgress(){
    if(!bar)return;
    const max=document.documentElement.scrollHeight-window.innerHeight;
    bar.style.width=(max>0?window.scrollY/max*100:0).toFixed(2)+'%';
  }
  function updateActive(){
    let current=sections[0];
    for(const sec of sections){
      if(sec.getBoundingClientRect().top<160) current=sec;
    }
    links.forEach(a=>a.classList.toggle('active', current && a.getAttribute('href')==='#'+current.id));
  }
  window.addEventListener('scroll',()=>{updateProgress();updateActive();},{passive:true});
  window.addEventListener('resize',()=>{updateProgress();updateActive();});
  updateProgress(); updateActive();
})();
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one-page-per-chapter static HTML from Zhihu Markdown.")
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR, type=Path, help="Private Zhihu Markdown directory.")
    parser.add_argument("--output-root", default=Path.cwd(), type=Path, help="Public repository root.")
    args = parser.parse_args()
    SiteBuilder(args.source_dir.resolve(), args.output_root.resolve()).build()


if __name__ == "__main__":
    main()
