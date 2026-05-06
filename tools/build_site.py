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

CHAPTER_DESCRIPTIONS = {
    "ch01": "从生活里的回声和目标发现开始，建立雷达最基本的直觉。",
    "ch02": "用时域、频域和采样定理搭起后续信号处理的地基。",
    "ch03": "理解发射信号、目标反射、传播衰减和接收端信号。",
    "ch04": "把时间延迟、线性调频和匹配滤波连接到距离测量。",
    "ch05": "从多普勒频移出发，理解速度估计和运动目标显示。",
    "ch06": "学习阈值、虚警、漏检和 CFAR 如何决定目标是否存在。",
    "ch07": "从天线波束到单脉冲测角，理解目标方向从何而来。",
    "ch08": "把距离、速度、检测串成一条可运行的 MATLAB 处理链。",
}

INTRO = "一本从直觉出发的雷达信号处理入门教程。"
GITHUB_URL = "https://github.com/apple-art/easy-radar-tutorial"
SITE_URL = "https://apple-art.github.io/easy-radar-tutorial/"
ASSET_VERSION = "20260506-toc-card-arrow"
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
        self.last_subheadings: list[dict[str, str]] = []

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
        self.last_subheadings = []
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
                    output_level = min(level + 1, 6)
                    heading_id = f"sub-{self.heading_counter}"
                    if output_level == 3:
                        self.last_subheadings.append({"id": heading_id, "title": title})
                    out.append(f'<h{output_level} id="{heading_id}">{self.inline(title)}</h{output_level}>')
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
            cards.append(
                f"""<article class="chapter-card reveal">
      <div class="chapter-kicker"><span>{chapter["label"]}</span></div>
      <h3>{html.escape(chapter["title"])}</h3>
      <p>{html.escape(CHAPTER_DESCRIPTIONS.get(chapter["slug"], ""))}</p>
      <div class="chapter-actions">{''.join(actions)}</div>
    </article>"""
            )
        body = f"""
<header class="hero">
  <nav class="topbar">
    <a class="brand" href="./"><img src="design/icon-concepts/logo-mark-light.svg" alt="教程图标"><span>Easy Radar Tutorial</span></a>
    <div class="toplinks"><a href="index.html">首页</a><a href="chapters/ch01.html">章节</a><a href="{html_attr(github_tree_url('matlab'))}">MATLAB</a><a href="{html_attr(github_tree_url('pdf'))}">PDF</a><a href="{html_attr(GITHUB_URL)}">GitHub</a></div>
  </nav>
  <div class="hero-shell reveal">
    <div class="hero-banner">
      <div class="hero-art" aria-hidden="true"></div>
      <div class="hero-copy">
        <div class="hero-mark"><img src="design/icon-concepts/logo-mark-light.svg" alt="项目图标"><span class="eyebrow">Radar signal processing</span></div>
        <h1>易懂的雷达信号处理教程</h1>
        <p>面向学生与工程师</p>
        <div class="hero-actions"><a class="btn primary" href="chapters/ch01.html">开始阅读</a><a class="btn" href="#chapters">选择章节</a><a class="btn ghost" href="{html_attr(github_tree_url('matlab'))}">MATLAB 代码</a><a class="btn" href="{html_attr(GITHUB_URL + '/releases/latest')}">下载资料包</a></div>
        <div class="hero-proof" aria-label="教程概览">
          <span><strong>8</strong> 个章节</span>
          <span><strong>{sum(len(c["sections"]) for c in self.chapters)}</strong> 个小节</span>
          <span><strong>{len(self.matlab_files_by_name)}</strong> 个脚本</span>
        </div>
      </div>
    </div>
  </div>
</header>
<main>
  <section id="chapters" class="chapters">
    <div class="section-head reveal"><p class="eyebrow">Read online</p><h2>在线章节</h2></div>
    <div class="chapter-grid">{''.join(cards)}</div>
  </section>
  <section class="author-card reveal" aria-labelledby="author-card-title">
    <div class="section-head author-card-copy">
      <h2 id="author-card-title">作者名片</h2>
      <p>如果这套教程对你有帮助，可以通过这张名片找到我。</p>
    </div>
    <figure class="personal-card-frame">
      <img src="design/personal-card/athens-card-minimal-2-hd.png" alt="唐承乾个人名片" loading="lazy">
    </figure>
  </section>
</main>
<footer class="site-footer"><p>© 唐承乾. 本仓库内容按 LICENSE 中的条款发布。</p><p><a href="{html_attr(GITHUB_URL)}">GitHub 仓库</a> · <a href="LICENSE">LICENSE</a></p></footer>
"""
        return self.shell("首页", body, "index.html", INTRO)

    def render_chapter(self, chapter: dict, renderer: MarkdownRenderer) -> str:
        section_html = []
        for section in chapter["sections"]:
            rendered_section = renderer.render(section["text"], section["id"], section["title"])
            section["subheadings"] = renderer.last_subheadings.copy()
            section_html.append(
                f'<section class="chapter-section" data-section="{html_attr(section["id"])}">'
                + rendered_section
                + "</section>"
            )
        sidebar_items = []
        for item in self.chapters:
            chapter_link = (
                f'<a class="chapter-toc-link{" active" if item["slug"] == chapter["slug"] else ""}" '
                f'href="{html_attr(url_path(item["slug"] + ".html"))}">{html.escape(item["label"])} {html.escape(item["title"])}</a>'
            )
            if item["slug"] == chapter["slug"]:
                subsection_links = []
                for section in item["sections"]:
                    third_level_links = "".join(
                        f'<a class="subtoc-link" href="#{html_attr(subheading["id"])}">{html.escape(subheading["title"])}</a>'
                        for subheading in section.get("subheadings", [])
                    )
                    subitems = f'<div class="toc-subitems">{third_level_links}</div>' if third_level_links else ""
                    subsection_links.append(
                        f'<div class="toc-section" data-section="{html_attr(section["id"])}">'
                        f'<a class="toc-link" href="#{html_attr(section["id"])}">{html.escape(section["title"])}</a>'
                        f'{subitems}</div>'
                    )
                chapter_link += f'<div class="chapter-subtoc">{"".join(subsection_links)}</div>'
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
    <div class="toplinks"><a href="../index.html">首页</a><a href="ch01.html">章节</a><a href="{html_attr(github_tree_url('matlab'))}">MATLAB</a><a href="{html_attr(github_tree_url('pdf'))}">PDF</a><a href="{html_attr(GITHUB_URL)}">GitHub</a></div>
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
  <link rel="stylesheet" href="{depth}assets/site.css?v={ASSET_VERSION}">
  <script>window.MathJax = {{ tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']] }}, svg: {{ fontCache: 'global' }} }};</script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
  <script defer src="{depth}assets/site.js?v={ASSET_VERSION}"></script>
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
  --ink: #17211d;
  --muted: #65726b;
  --soft: #8c9891;
  --paper: #f6efe3;
  --paper-2: #fbf7ef;
  --surface: rgba(255, 253, 248, 0.84);
  --surface-strong: #fffdf8;
  --teal: #0d4746;
  --teal-2: #1e6b68;
  --sage: #87b6a2;
  --sand: #ead8bd;
  --brass: #c9893f;
  --copper: #9b5834;
  --line: rgba(23, 33, 29, 0.12);
  --line-strong: rgba(23, 33, 29, 0.2);
  --shadow: 0 28px 90px rgba(47, 39, 28, 0.14);
  --shadow-soft: 0 16px 48px rgba(47, 39, 28, 0.1);
  --mono: "Cascadia Code", "Fira Code", "Consolas", monospace;
  --serif: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "SimSun", serif;
  --sans: "LXGW WenKai Screen", "HarmonyOS Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 118px; background: var(--paper); }
body {
  margin: 0;
  min-height: 100vh;
  overflow-x: hidden;
  color: var(--ink);
  font-family: var(--serif);
  background:
    radial-gradient(circle at 14% 5%, rgba(201, 137, 63, 0.18), transparent 28rem),
    radial-gradient(circle at 86% 8%, rgba(30, 107, 104, 0.16), transparent 30rem),
    linear-gradient(135deg, #fbf7ef 0%, #f6efe3 46%, #edf3ea 100%);
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -2;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(13, 71, 70, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(13, 71, 70, 0.035) 1px, transparent 1px),
    radial-gradient(circle at 15% 82%, rgba(135, 182, 162, 0.18), transparent 26rem);
  background-size: 56px 56px, 56px 56px, auto;
}
body::after {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background: linear-gradient(90deg, rgba(246, 239, 227, 0.84), transparent 18%, transparent 82%, rgba(246, 239, 227, 0.78));
}
a { color: inherit; text-decoration: none; }
a:hover { color: var(--teal); }
img { max-width: 100%; }
.read-progress { position: fixed; inset: 0 0 auto; height: 4px; z-index: 70; background: rgba(255, 253, 248, 0.58); }
.read-progress span { display: block; width: 0; height: 100%; background: linear-gradient(90deg, var(--brass), var(--teal-2), var(--sage)); box-shadow: 0 0 20px rgba(13, 71, 70, 0.28); }
.topbar {
  width: min(1180px, calc(100% - 40px));
  margin: 18px auto 0;
  padding: 10px 12px 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  position: relative;
  z-index: 10;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 999px;
  background: rgba(255, 253, 248, 0.72);
  box-shadow: 0 18px 48px rgba(47, 39, 28, 0.08);
  backdrop-filter: blur(20px);
}
.topbar.compact { width: min(1320px, calc(100% - 40px)); margin-top: 10px; }
.brand { display: inline-flex; align-items: center; gap: 12px; font-family: var(--sans); font-weight: 900; letter-spacing: 0.01em; color: #18332f; }
.brand img { width: 38px; height: 38px; filter: drop-shadow(0 10px 16px rgba(13, 71, 70, 0.16)); }
.toplinks { display: flex; align-items: center; gap: 5px; color: #50615a; font-family: var(--sans); font-size: 14px; font-weight: 800; }
.toplinks a { padding: 9px 12px; border-radius: 999px; transition: background 0.18s ease, color 0.18s ease; }
.toplinks a:hover { color: var(--teal); background: rgba(13, 71, 70, 0.08); }
.hero { position: relative; min-height: 720px; overflow: hidden; padding-bottom: 76px; }
.hero::before,
.hero::after { content: ""; position: absolute; pointer-events: none; }
.hero::before {
  right: -12vw;
  top: 64px;
  width: min(780px, 58vw);
  aspect-ratio: 1;
  border-radius: 50%;
  background: repeating-radial-gradient(circle, rgba(13, 71, 70, 0.12) 0 1px, transparent 1px 34px);
  mask-image: linear-gradient(90deg, transparent, #000 24%, #000);
  opacity: 0.72;
}
.hero::after {
  left: -14vw;
  bottom: -30vw;
  width: 52vw;
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(201, 137, 63, 0.2), transparent 68%);
}
.hero-shell {
  width: min(1180px, calc(100% - 40px));
  margin: 54px auto 0;
  position: relative;
  z-index: 2;
}
.hero-banner {
  position: relative;
  min-height: clamp(560px, 64vw, 720px);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.76);
  border-radius: 42px;
  background: linear-gradient(145deg, rgba(255, 253, 248, 0.96), rgba(233, 239, 230, 0.82));
  box-shadow: var(--shadow);
  isolation: isolate;
}
.hero-banner::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background:
    linear-gradient(90deg, rgba(251, 247, 239, 0.98) 0%, rgba(251, 247, 239, 0.94) 30%, rgba(251, 247, 239, 0.72) 64%, rgba(13, 71, 70, 0.08) 100%),
    linear-gradient(180deg, rgba(255, 253, 248, 0.1), rgba(12, 55, 54, 0.18));
}
.hero-banner::after {
  content: "";
  position: absolute;
  inset: 18px;
  z-index: 2;
  pointer-events: none;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 30px;
}
.hero-art { position: absolute; inset: 0; background: url("../design/hero/radar-hero-clean.png") center / cover no-repeat; transform: scale(1.02); }
.hero-copy { position: relative; z-index: 3; width: min(980px, 78%); padding: clamp(38px, 6vw, 76px); }
.hero-mark { display: inline-flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.hero-mark img { width: 48px; height: 48px; border-radius: 16px; filter: drop-shadow(0 12px 20px rgba(13, 71, 70, 0.16)); }
.eyebrow { margin: 0; font-family: var(--sans); font-size: 12px; font-weight: 900; letter-spacing: 0.22em; text-transform: uppercase; color: var(--copper); }
h1 { margin: 0 0 24px; max-width: 980px; font-size: clamp(62px, 8.6vw, 118px); line-height: 1.04; letter-spacing: -0.07em; text-wrap: balance; }
.hero-copy p { margin: 0; color: #4f615a; font-size: clamp(24px, 2.3vw, 34px); line-height: 1.45; letter-spacing: -0.03em; }
.hero-actions,
.chapter-actions,
.article-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 30px; }
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 11px 17px;
  border: 1px solid rgba(23, 33, 29, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.68);
  color: #24413b;
  box-shadow: 0 10px 24px rgba(47, 39, 28, 0.08);
  font-family: var(--sans);
  font-size: 15px;
  font-weight: 900;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}
.btn:hover { transform: translateY(-2px); color: var(--teal); background: #fff; border-color: rgba(13, 71, 70, 0.2); box-shadow: 0 16px 34px rgba(47, 39, 28, 0.14); }
.btn.primary { color: #fffaf1; border-color: transparent; background: linear-gradient(135deg, #0d4746, #1e6b68); }
.btn.primary:hover { color: #fff; background: linear-gradient(135deg, #082f30, #185f5d); }
.btn.ghost { background: rgba(255, 255, 255, 0.34); }
.hero-proof { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; color: #55655e; font-family: var(--sans); }
.hero-proof span { display: inline-flex; align-items: baseline; gap: 6px; padding: 9px 12px; border: 1px solid rgba(13, 71, 70, 0.1); border-radius: 999px; background: rgba(255, 253, 248, 0.72); box-shadow: 0 10px 26px rgba(47, 39, 28, 0.08); backdrop-filter: blur(12px); }
.hero-proof strong { color: var(--teal); font-size: 22px; line-height: 1; }
main { width: min(1180px, calc(100% - 40px)); margin: 0 auto; position: relative; z-index: 4; }
.chapters { margin-top: 12px; }
.section-head { max-width: 780px; margin-bottom: 30px; }
h2 { margin: 8px 0 14px; font-size: clamp(34px, 4.2vw, 56px); line-height: 1.1; letter-spacing: -0.045em; text-wrap: balance; }
.section-head p { color: var(--muted); line-height: 1.8; }
.chapter-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }
.chapter-card {
  position: relative;
  min-height: 340px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 26px;
  border: 1px solid rgba(255, 255, 255, 0.74);
  border-radius: 30px;
  background: linear-gradient(180deg, rgba(255, 253, 248, 0.92), rgba(255, 253, 248, 0.64));
  box-shadow: 0 18px 46px rgba(47, 39, 28, 0.08);
  transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
}
.chapter-card::before { content: ""; position: absolute; inset: 0 0 auto; height: 4px; background: linear-gradient(90deg, var(--brass), var(--sage), var(--teal-2)); }
.chapter-card::after { content: ""; position: absolute; right: -74px; top: -78px; width: 190px; height: 190px; border-radius: 50%; background: repeating-radial-gradient(circle, rgba(13, 71, 70, 0.1) 0 1px, transparent 1px 18px); opacity: 0.72; pointer-events: none; }
.chapter-card:hover { transform: translateY(-6px); border-color: rgba(13, 71, 70, 0.18); box-shadow: 0 28px 74px rgba(47, 39, 28, 0.14); }
.chapter-kicker { position: relative; z-index: 1; color: var(--copper); font-family: var(--sans); font-weight: 900; }
.chapter-kicker span { display: inline-flex; padding: 6px 10px; border-radius: 999px; background: rgba(201, 137, 63, 0.14); }
.chapter-card h3 { position: relative; z-index: 1; min-height: 66px; margin: 18px 0 12px; font-size: 25px; line-height: 1.28; letter-spacing: -0.03em; }
.chapter-card p { position: relative; z-index: 1; min-height: 88px; margin: 0 0 22px; color: #58665f; font-size: 16.5px; line-height: 1.78; }
.chapter-card .chapter-actions { position: relative; z-index: 1; min-height: 46px; align-content: flex-start; align-items: flex-start; margin-top: auto; }
.chapter-actions .btn { min-height: 40px; padding: 9px 13px; font-size: 14px; }
.author-card { position: relative; display: grid; grid-template-columns: minmax(0, 0.68fr) minmax(320px, 1.32fr); gap: 32px; align-items: center; margin-top: 76px; padding: clamp(24px, 4vw, 42px); border: 1px solid rgba(255, 255, 255, 0.76); border-radius: 36px; background: linear-gradient(145deg, rgba(255, 253, 248, 0.92), rgba(233, 239, 230, 0.74)); box-shadow: var(--shadow-soft); overflow: hidden; }
.author-card::before { content: ""; position: absolute; right: -110px; top: -130px; width: 360px; height: 360px; border-radius: 50%; background: repeating-radial-gradient(circle, rgba(13, 71, 70, 0.1) 0 2px, transparent 2px 24px); pointer-events: none; }
.author-card-copy { position: relative; z-index: 1; margin-bottom: 0; }
.personal-card-frame { position: relative; z-index: 1; margin: 0; }
.personal-card-frame img { display: block; width: 100%; height: auto; margin: 0 auto; border-radius: 26px; background: #fff; box-shadow: 0 26px 72px rgba(47, 39, 28, 0.16); }
.site-footer { width: min(1180px, calc(100% - 40px)); margin: 84px auto 34px; padding-top: 24px; border-top: 1px solid var(--line); color: var(--muted); font-family: var(--sans); line-height: 1.75; }
.article-top { position: sticky; top: 0; z-index: 60; padding-bottom: 10px; border-bottom: 1px solid rgba(23, 33, 29, 0.1); background: rgba(246, 239, 227, 0.76); backdrop-filter: blur(18px); }
.article-layout { width: min(1380px, calc(100% - 32px)); margin: 28px auto 0; display: grid; grid-template-columns: 318px minmax(0, 1fr); gap: 38px; align-items: start; }
.sidebar { position: sticky; top: 92px; max-height: calc(100vh - 112px); overflow: auto; padding: 18px 16px 24px; border: 1px solid rgba(255, 255, 255, 0.76); border-radius: 30px; background: rgba(255, 253, 248, 0.78); box-shadow: 0 18px 46px rgba(47, 39, 28, 0.08); backdrop-filter: blur(14px); font-family: var(--sans); scrollbar-width: thin; }
.back-home { display: inline-flex; margin: 0 0 16px; padding: 9px 12px; border-radius: 999px; color: var(--copper); font-weight: 900; background: rgba(201, 137, 63, 0.12); }
.book-toc { display: grid; gap: 9px; }
.book-toc-group { display: grid; gap: 6px; }
.chapter-toc-link { display: block; padding: 11px 12px; border-radius: 17px; color: #58655f; font-weight: 900; line-height: 1.35; transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease; }
.chapter-toc-link:hover { color: var(--teal); background: rgba(13, 71, 70, 0.07); transform: translateX(2px); }
.chapter-toc-link.active { color: var(--copper); background: linear-gradient(90deg, rgba(201, 137, 63, 0.2), rgba(135, 182, 162, 0.12)); }
.chapter-subtoc { display: grid; gap: 4px; margin: 0 0 10px 16px; padding-left: 14px; border-left: 2px solid rgba(201, 137, 63, 0.28); }
.toc-link { display: block; padding: 9px 11px; border-radius: 14px; color: #57645e; line-height: 1.4; font-size: 15px; }
.toc-link:hover { color: var(--teal); background: rgba(13, 71, 70, 0.06); }
.toc-link.active { color: var(--copper); background: #f0ddc4; font-weight: 900; box-shadow: inset 0 0 0 1px rgba(201, 137, 63, 0.24); }
.toc-section { display: grid; gap: 4px; }
.toc-subitems { display: none; gap: 3px; margin: 2px 0 10px 18px; padding-left: 12px; border-left: 1px solid rgba(201, 137, 63, 0.28); }
.toc-section.open .toc-subitems { display: grid; }
.subtoc-link { display: block; padding: 7px 10px; border-radius: 12px; color: #6a756f; line-height: 1.45; font-size: 14px; }
.subtoc-link:hover { color: var(--teal); background: rgba(13, 71, 70, 0.06); }
.subtoc-link.active { color: var(--copper); background: rgba(201, 137, 63, 0.17); font-weight: 900; }
.article-main { min-width: 0; padding: 0 0 84px; }
.article-meta { display: flex; flex-wrap: wrap; gap: 10px; margin: 0 auto 18px; max-width: 920px; }
.article-meta span { padding: 7px 11px; border-radius: 999px; background: rgba(201, 137, 63, 0.14); color: var(--copper); font-family: var(--sans); font-size: 13px; font-weight: 900; }
.prose { max-width: 920px; margin: 0 auto; padding: clamp(28px, 4.6vw, 64px); overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.78); border-radius: 34px; background: rgba(255, 253, 248, 0.9); box-shadow: var(--shadow); }
.prose h1 { margin: 0 0 38px; font-size: clamp(36px, 5vw, 62px); line-height: 1.12; letter-spacing: -0.045em; text-wrap: balance; }
.section-title { margin: 76px 0 28px; padding-top: 32px; border-top: 1px solid rgba(23, 33, 29, 0.12); font-size: clamp(30px, 3.6vw, 44px); line-height: 1.25; letter-spacing: -0.035em; text-wrap: balance; }
.chapter-section:first-of-type .section-title { margin-top: 10px; padding-top: 0; border-top: 0; }
.prose h3 { margin: 42px 0 14px; font-size: 25px; letter-spacing: -0.02em; }
.prose h4 { margin: 32px 0 12px; font-size: 22px; }
.prose p,
.prose li,
.prose blockquote { font-size: 18px; line-height: 2.04; }
.prose p { margin: 18px 0; }
.prose ul,
.prose ol { margin: 18px 0; padding-left: 1.5em; }
.prose li { margin: 8px 0; }
.prose a { color: var(--copper); border-bottom: 1px solid rgba(155, 88, 52, 0.34); }
.prose code { padding: 0.12em 0.38em; border: 1px solid rgba(13, 71, 70, 0.08); border-radius: 7px; background: rgba(13, 71, 70, 0.08); font-family: var(--mono); font-size: 0.92em; }
.inline-code-link { border-bottom: none !important; }
.prose pre { overflow: auto; padding: 20px; border-radius: 20px; color: #f7ead6; background: linear-gradient(145deg, #102f33, #183b3f); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08), 0 18px 38px rgba(13, 71, 70, 0.12); }
.prose pre code { padding: 0; border: 0; color: inherit; background: transparent; }
.prose blockquote { margin: 28px 0; padding: 18px 22px; border-left: 5px solid var(--brass); border-radius: 0 20px 20px 0; color: #4d5c55; background: linear-gradient(90deg, rgba(201, 137, 63, 0.14), rgba(135, 182, 162, 0.08)); }
.math-block,
.table-wrap { overflow-x: auto; }
.prose mjx-container[jax="SVG"][display="true"] { max-width: 100%; overflow-x: auto; overflow-y: hidden; }
table { width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 16px; background: rgba(255, 255, 255, 0.56); font-size: 16px; }
th,
td { padding: 12px 14px; border: 1px solid rgba(23, 33, 29, 0.12); text-align: left; vertical-align: top; }
th { background: rgba(13, 71, 70, 0.08); font-family: var(--sans); }
figure { margin: 34px 0; }
figure img { display: block; max-width: 100%; height: auto; margin: 0 auto; border-radius: 22px; background: #fff; box-shadow: 0 20px 52px rgba(47, 39, 28, 0.16); }
figcaption { margin-top: 12px; color: var(--muted); text-align: center; font-family: var(--sans); font-size: 14px; }
.article-actions { max-width: 920px; margin: 26px auto 0; }
.reveal { animation: lift 0.65s ease both; }
@keyframes lift { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 1080px) {
  .hero-copy { width: min(860px, 86%); }
  .chapter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .article-layout { grid-template-columns: 1fr; }
  .sidebar { position: relative; top: auto; max-height: none; }
  .prose,
  .article-meta,
  .article-actions { max-width: none; }
}
@media (max-width: 820px) {
  .author-card { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  html { scroll-padding-top: 92px; }
  .topbar,
  .topbar.compact { width: min(100% - 24px, 760px); align-items: flex-start; flex-direction: column; border-radius: 26px; }
  .toplinks { max-width: 100%; overflow-x: auto; padding-bottom: 2px; }
  .hero { min-height: auto; padding-bottom: 72px; }
  .hero-shell { width: min(100% - 28px, 760px); margin-top: 34px; }
  .hero-banner { min-height: 620px; border-radius: 30px; }
  .hero-banner::before { background: linear-gradient(180deg, rgba(251, 247, 239, 0.96) 0%, rgba(251, 247, 239, 0.9) 46%, rgba(13, 71, 70, 0.08) 100%); }
  .hero-banner::after { inset: 12px; border-radius: 22px; }
  .hero-art { background-position: 58% center; }
  .hero-copy { width: 100%; padding: 30px 26px; }
  .hero-mark img { width: 42px; height: 42px; border-radius: 14px; }
  .hero-proof { margin-top: 16px; }
  h1 { font-size: clamp(50px, 14vw, 78px); line-height: 1.06; letter-spacing: -0.055em; }
  main { width: min(100% - 28px, 760px); }
  .chapter-grid { grid-template-columns: 1fr; }
  .chapter-card { min-height: auto; padding: 22px; }
  .chapter-card h3,
  .chapter-card p { min-height: auto; }
  .author-card { gap: 20px; }
  .article-layout { width: min(100% - 20px, 760px); gap: 22px; }
  .prose { padding: 24px; border-radius: 24px; }
  .prose p,
  .prose li,
  .prose blockquote { font-size: 17px; line-height: 1.92; }
  .chapter-card h3 { font-size: 26px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; scroll-behavior: auto !important; transition: none !important; }
}


/* Visual refresh: keep the original content, refine the reading-site presentation. */
:root {
  --radar-deep: #073b3a;
  --radar-ink: #10241f;
  --radar-glow: rgba(43, 127, 119, 0.18);
  --card-glass: rgba(255, 253, 248, 0.76);
}
html { background: #f3ead8; }
body {
  background:
    radial-gradient(circle at 8% 7%, rgba(201, 137, 63, 0.24), transparent 27rem),
    radial-gradient(circle at 90% 8%, rgba(13, 71, 70, 0.2), transparent 32rem),
    radial-gradient(circle at 72% 72%, rgba(135, 182, 162, 0.18), transparent 30rem),
    linear-gradient(135deg, #fcf3e3 0%, #f5ecda 43%, #e9f2ea 100%);
}
body::before {
  background-image:
    linear-gradient(rgba(13, 71, 70, 0.038) 1px, transparent 1px),
    linear-gradient(90deg, rgba(13, 71, 70, 0.038) 1px, transparent 1px),
    radial-gradient(circle at 16% 78%, rgba(135, 182, 162, 0.2), transparent 26rem);
  background-size: 64px 64px, 64px 64px, auto;
}
.topbar {
  border-color: rgba(255, 255, 255, 0.9);
  background: rgba(255, 253, 248, 0.8);
  box-shadow: 0 18px 52px rgba(47, 39, 28, 0.1);
  backdrop-filter: blur(22px) saturate(1.12);
}
.brand { color: var(--radar-ink); }
.toplinks a { position: relative; }
.toplinks a::after {
  content: "";
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 5px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0;
  transform: scaleX(0.35);
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.toplinks a:hover::after { opacity: 0.42; transform: scaleX(1); }
.hero { min-height: 690px; padding-bottom: 68px; }
.hero::before {
  right: -9vw;
  top: 34px;
  width: min(760px, 54vw);
  opacity: 0.62;
}
.hero-shell { margin-top: 44px; }
.hero-banner {
  min-height: clamp(540px, 58vw, 680px);
  border-radius: 38px;
  border-color: rgba(255, 255, 255, 0.86);
  background: linear-gradient(145deg, rgba(255, 253, 248, 0.96), rgba(232, 241, 232, 0.82));
  box-shadow: 0 36px 110px rgba(47, 39, 28, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.72);
}
.hero-banner::before {
  background:
    linear-gradient(90deg, rgba(251, 247, 239, 0.99) 0%, rgba(251, 247, 239, 0.94) 34%, rgba(251, 247, 239, 0.68) 68%, rgba(13, 71, 70, 0.08) 100%),
    linear-gradient(180deg, rgba(255, 253, 248, 0.03), rgba(12, 55, 54, 0.2));
}
.hero-banner::after { inset: 16px; border-radius: 28px; border-color: rgba(255, 255, 255, 0.82); }
.hero-art { background-position: 52% center; filter: saturate(1.05) contrast(1.02); transform: scale(1.035); }
.hero-copy { width: min(900px, 74%); padding: clamp(42px, 6.2vw, 82px); }
.hero-mark {
  padding: 8px 12px 8px 8px;
  border: 1px solid rgba(13, 71, 70, 0.08);
  border-radius: 999px;
  background: rgba(255, 253, 248, 0.58);
  box-shadow: 0 12px 30px rgba(47, 39, 28, 0.08);
  backdrop-filter: blur(12px);
}
.hero-mark img { width: 42px; height: 42px; }
h1 { max-width: 820px; font-size: clamp(58px, 8vw, 108px); letter-spacing: -0.065em; }
.hero-copy p { max-width: 680px; color: #4c5f58; font-size: clamp(22px, 2.2vw, 31px); }
.hero-actions { margin-top: 34px; }
.btn {
  border-color: rgba(23, 33, 29, 0.16);
  background: rgba(255, 253, 248, 0.82);
  box-shadow: 0 12px 28px rgba(47, 39, 28, 0.1);
}
.btn.primary { background: linear-gradient(135deg, #083838, #1a6b66); box-shadow: 0 16px 34px rgba(13, 71, 70, 0.22); }
.btn.ghost { background: rgba(255, 253, 248, 0.54); }
.hero-proof span {
  border-color: rgba(13, 71, 70, 0.12);
  background: rgba(255, 253, 248, 0.84);
}
.chapters { margin-top: 30px; }
.section-head { margin-bottom: 34px; }
.chapter-grid { grid-template-columns: repeat(auto-fit, minmax(268px, 1fr)); gap: 18px; }
.chapter-card {
  min-height: 320px;
  padding: 28px;
  border-radius: 28px;
  border-color: rgba(255, 255, 255, 0.86);
  background:
    linear-gradient(180deg, rgba(255, 253, 248, 0.95), rgba(255, 253, 248, 0.7)),
    radial-gradient(circle at 100% 0%, rgba(13, 71, 70, 0.08), transparent 12rem);
  box-shadow: 0 18px 48px rgba(47, 39, 28, 0.09);
}
.chapter-card::before { height: 5px; background: linear-gradient(90deg, var(--brass), #8cb69f, var(--radar-deep)); }
.chapter-card::after { opacity: 0.58; }
.chapter-card:hover { transform: translateY(-5px); box-shadow: 0 28px 72px rgba(47, 39, 28, 0.15); }
.chapter-kicker span { background: rgba(201, 137, 63, 0.16); }
.chapter-card h3 { min-height: 62px; font-size: 26px; }
.chapter-card p { min-height: 82px; color: #53645d; }
.author-card {
  margin-top: 86px;
  border-color: rgba(255, 255, 255, 0.86);
  background: linear-gradient(145deg, rgba(255, 253, 248, 0.95), rgba(232, 241, 232, 0.78));
  box-shadow: 0 24px 72px rgba(47, 39, 28, 0.12);
}
.personal-card-frame img { box-shadow: 0 28px 78px rgba(47, 39, 28, 0.18); }
.article-top {
  background: rgba(246, 239, 227, 0.82);
  backdrop-filter: blur(22px) saturate(1.08);
}
.article-layout { gap: 42px; }
.sidebar {
  border-color: rgba(255, 255, 255, 0.84);
  background: rgba(255, 253, 248, 0.82);
  box-shadow: 0 20px 56px rgba(47, 39, 28, 0.1);
}
.prose {
  border-color: rgba(255, 255, 255, 0.86);
  background: rgba(255, 253, 248, 0.93);
  box-shadow: 0 30px 96px rgba(47, 39, 28, 0.14);
}
.prose h1 { color: var(--radar-ink); }
.section-title { border-top-color: rgba(13, 71, 70, 0.1); }
.prose blockquote { background: linear-gradient(90deg, rgba(201, 137, 63, 0.15), rgba(135, 182, 162, 0.1)); }
.prose pre { background: linear-gradient(145deg, #0b2f32, #173f40); }
figure img { box-shadow: 0 22px 58px rgba(47, 39, 28, 0.16); }
@media (min-width: 1120px) {
  .chapter-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
  .hero-banner { min-height: 580px; }
  .hero-copy { width: 100%; padding: 30px 25px; }
  .chapter-card { min-height: auto; }
  .hero-mark { border-radius: 24px; }
}

/* Chapter card polish pass: make the cards visibly redesigned without changing content. */
.chapter-grid { gap: 22px; }
.chapter-card {
  --card-accent: #0d5a57;
  --card-accent-2: #c9893f;
  min-height: 348px;
  padding: 30px 28px 26px;
  border: 1px solid rgba(255, 255, 255, 0.92);
  border-radius: 34px 34px 28px 28px;
  background:
    linear-gradient(155deg, rgba(255, 253, 248, 0.98) 0%, rgba(255, 251, 241, 0.9) 48%, rgba(236, 244, 237, 0.82) 100%),
    radial-gradient(circle at 80% 10%, color-mix(in srgb, var(--card-accent) 18%, transparent), transparent 10rem);
  box-shadow:
    0 24px 60px rgba(47, 39, 28, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
  isolation: isolate;
}
.chapter-card:nth-child(1) { --card-accent: #0a5b58; --card-accent-2: #c9893f; }
.chapter-card:nth-child(2) { --card-accent: #2f6f5f; --card-accent-2: #b9853d; }
.chapter-card:nth-child(3) { --card-accent: #245f7a; --card-accent-2: #b87945; }
.chapter-card:nth-child(4) { --card-accent: #7b5a2a; --card-accent-2: #0c6b65; }
.chapter-card:nth-child(5) { --card-accent: #8b4f35; --card-accent-2: #116763; }
.chapter-card:nth-child(6) { --card-accent: #355f48; --card-accent-2: #c9893f; }
.chapter-card:nth-child(7) { --card-accent: #164f64; --card-accent-2: #c27d45; }
.chapter-card:nth-child(8) { --card-accent: #083f3f; --card-accent-2: #d09a45; }
.chapter-card::before {
  height: 8px;
  border-radius: 999px;
  inset: 0 22px auto;
  background: linear-gradient(90deg, var(--card-accent-2), rgba(135, 182, 162, 0.9), var(--card-accent));
  box-shadow: 0 10px 22px color-mix(in srgb, var(--card-accent) 22%, transparent);
}
.chapter-card::after {
  right: 18px;
  top: 8px;
  width: auto;
  height: auto;
  border-radius: 0;
  background: none;
  color: color-mix(in srgb, var(--card-accent) 10%, transparent);
  font-family: var(--mono);
  font-size: 106px;
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.1em;
  opacity: 1;
  transform: none;
}
.chapter-card:nth-child(1)::after { content: "01"; }
.chapter-card:nth-child(2)::after { content: "02"; }
.chapter-card:nth-child(3)::after { content: "03"; }
.chapter-card:nth-child(4)::after { content: "04"; }
.chapter-card:nth-child(5)::after { content: "05"; }
.chapter-card:nth-child(6)::after { content: "06"; }
.chapter-card:nth-child(7)::after { content: "07"; }
.chapter-card:nth-child(8)::after { content: "08"; }
.chapter-card:hover {
  transform: translateY(-8px) scale(1.01);
  border-color: color-mix(in srgb, var(--card-accent) 24%, white);
  box-shadow:
    0 34px 86px rgba(47, 39, 28, 0.18),
    0 0 0 1px color-mix(in srgb, var(--card-accent) 12%, transparent),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
}
.chapter-kicker { z-index: 2; }
.chapter-kicker span {
  padding: 8px 12px;
  border: 1px solid color-mix(in srgb, var(--card-accent-2) 32%, transparent);
  background: linear-gradient(135deg, color-mix(in srgb, var(--card-accent-2) 20%, white), rgba(255, 253, 248, 0.78));
  color: color-mix(in srgb, var(--card-accent) 72%, #7f4b2d);
  box-shadow: 0 10px 24px rgba(47, 39, 28, 0.08);
}
.chapter-card h3 {
  z-index: 2;
  max-width: 82%;
  min-height: 70px;
  margin-top: 24px;
  font-size: 28px;
  letter-spacing: -0.04em;
}
.chapter-card p {
  z-index: 2;
  max-width: 88%;
  color: #53635d;
}
.chapter-card .chapter-actions {
  width: calc(100% + 16px);
  margin-left: -8px;
  margin-right: -8px;
  padding: 14px 8px 0;
  border-top: 1px solid rgba(13, 71, 70, 0.08);
}
.chapter-actions .btn {
  border-color: rgba(13, 71, 70, 0.12);
  background: rgba(255, 253, 248, 0.86);
}
.chapter-actions .btn.primary {
  background: linear-gradient(135deg, var(--card-accent), color-mix(in srgb, var(--card-accent) 78%, #0a2c2b));
  box-shadow: 0 12px 26px color-mix(in srgb, var(--card-accent) 24%, transparent);
}
@media (max-width: 720px) {
  .chapter-card { min-height: auto; }
  .chapter-card::after { font-size: 82px; }
  .chapter-card h3,
  .chapter-card p { max-width: 100%; }
}

/* 2026-05-05 home visual pass: compact illustrated chapter cards + cinematic first screen. */
.hero-banner { min-height: clamp(620px, 60vw, 740px); }
.hero-copy { z-index: 5; }
.hero-copy h1 { color: #09282a; text-shadow: 0 2px 0 rgba(255, 253, 248, 0.35); }
.hero-copy p::before {
  content: "从原理到实践 · 真正易懂的雷达信号处理";
  display: block;
  margin-bottom: 12px;
  color: #9b6a2d;
  font-family: var(--sans);
  font-size: 18px;
  font-weight: 900;
  letter-spacing: 0.02em;
}
.hero-hud {
  position: absolute;
  z-index: 4;
  right: clamp(42px, 6vw, 92px);
  top: clamp(54px, 7vw, 84px);
  width: min(500px, 43vw);
  aspect-ratio: 1;
  pointer-events: none;
}
.radar-scope {
  position: absolute;
  inset: 0;
  border: 1px solid rgba(221, 182, 122, 0.52);
  border-radius: 50%;
  background:
    repeating-radial-gradient(circle, rgba(72, 190, 169, 0.18) 0 1px, transparent 1px 31px),
    linear-gradient(rgba(239, 205, 148, 0.28), rgba(239, 205, 148, 0.28)) center/1px 100% no-repeat,
    linear-gradient(90deg, rgba(239, 205, 148, 0.28), rgba(239, 205, 148, 0.28)) center/100% 1px no-repeat,
    radial-gradient(circle at center, rgba(64, 230, 190, 0.22), rgba(7, 59, 58, 0.05) 38%, transparent 67%);
  box-shadow: inset 0 0 42px rgba(22, 151, 137, 0.18), 0 0 76px rgba(9, 60, 57, 0.14);
}
.radar-scope::before {
  content: "";
  position: absolute;
  inset: -22px;
  border-radius: 50%;
  background: repeating-conic-gradient(from -1deg, rgba(205, 164, 102, 0.42) 0deg 0.7deg, transparent 0.7deg 1.8deg);
  mask: radial-gradient(circle, transparent 68%, #000 69% 72%, transparent 73%);
}
.sweep {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 46%;
  height: 2px;
  transform-origin: left center;
  transform: rotate(-34deg);
  background: linear-gradient(90deg, rgba(226, 253, 219, 0.95), rgba(45, 219, 180, 0.74), transparent);
  box-shadow: 0 0 28px rgba(57, 235, 194, 0.76);
}
.sweep::after {
  content: "";
  position: absolute;
  left: 0;
  top: -54px;
  width: 100%;
  height: 108px;
  background: conic-gradient(from -22deg at 0 50%, rgba(68, 241, 199, 0.38), transparent 34deg);
  filter: blur(2px);
}
.blip {
  position: absolute;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #ffc069;
  box-shadow: 0 0 18px #ffb85b, 0 0 34px rgba(255, 184, 91, 0.4);
}
.b1 { left: 31%; top: 48%; }
.b2 { left: 64%; top: 69%; }
.b3 { left: 73%; top: 34%; }
.degree { position: absolute; color: rgba(246, 221, 172, 0.86); font-family: var(--sans); font-size: 16px; font-weight: 900; }
.d0 { top: -28px; left: 50%; transform: translateX(-50%); }
.d90 { right: -40px; top: 50%; transform: translateY(-50%); }
.d180 { bottom: -32px; left: 50%; transform: translateX(-50%); }
.d270 { left: -48px; top: 50%; transform: translateY(-50%); }
.telemetry {
  position: absolute;
  right: -44px;
  top: 26%;
  display: grid;
  gap: 12px;
  color: rgba(246, 221, 172, 0.9);
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 900;
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.28);
}
.telemetry span { display: flex; justify-content: space-between; gap: 18px; min-width: 132px; }
.telemetry strong { color: #f5ca81; }
.hero-process {
  position: absolute;
  z-index: 5;
  left: clamp(34px, 5.8vw, 78px);
  right: clamp(34px, 5.8vw, 78px);
  bottom: clamp(28px, 4.3vw, 46px);
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  align-items: center;
  gap: 22px;
  padding: 22px 24px;
  border: 1px solid rgba(255, 253, 248, 0.36);
  border-radius: 28px;
  background: linear-gradient(90deg, rgba(9, 53, 51, 0.76), rgba(8, 49, 48, 0.44));
  box-shadow: 0 22px 58px rgba(3, 33, 32, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
}
.hero-process div { min-width: 0; color: rgba(255, 246, 226, 0.92); font-family: var(--sans); font-size: 13px; font-weight: 900; text-align: center; }
.hero-process i {
  position: absolute;
  top: 50%;
  width: 20px;
  height: 2px;
  background: rgba(255, 239, 207, 0.68);
  transform: translateY(-50%);
}
.hero-process i::after {
  content: "";
  position: absolute;
  right: -1px;
  top: -4px;
  width: 9px;
  height: 9px;
  border-top: 2px solid rgba(255, 239, 207, 0.68);
  border-right: 2px solid rgba(255, 239, 207, 0.68);
  transform: rotate(45deg);
}
.hero-process i:nth-of-type(1) { left: 15.4%; }
.hero-process i:nth-of-type(2) { left: 31.7%; }
.hero-process i:nth-of-type(3) { left: 48%; }
.hero-process i:nth-of-type(4) { left: 64.3%; }
.hero-process i:nth-of-type(5) { left: 80.6%; }
.process-icon {
  display: block;
  width: 100%;
  height: 58px;
  margin: 0 auto 10px;
  border-radius: 10px;
  background: rgba(255, 253, 248, 0.06);
  box-shadow: inset 0 0 0 1px rgba(255, 253, 248, 0.08);
}
.process-icon.target { background: radial-gradient(ellipse at 42% 55%, rgba(225, 215, 190, 0.5) 0 10%, transparent 12%), linear-gradient(28deg, transparent 44%, rgba(238, 214, 164, 0.75) 45% 48%, transparent 49%), radial-gradient(circle, rgba(91, 220, 178, 0.16), transparent 70%); }
.process-icon.tx { background: repeating-linear-gradient(90deg, transparent 0 12px, #d8a755 12px 15px, transparent 15px 25px), linear-gradient(transparent 48%, rgba(216, 167, 85, 0.5) 49% 51%, transparent 52%); }
.process-icon.rx { background: radial-gradient(circle at 18% 50%, rgba(216, 167, 85, 0.8) 0 2px, transparent 3px), repeating-linear-gradient(90deg, transparent 0 9px, rgba(216, 167, 85, 0.2) 9px 10px, transparent 10px 18px); }
.process-icon.matched { background: radial-gradient(ellipse at 50% 50%, rgba(32, 225, 177, 0.92) 0 3%, transparent 16%), repeating-linear-gradient(0deg, transparent 0 12px, rgba(255, 253, 248, 0.1) 12px 13px); }
.process-icon.spectrum { background: linear-gradient(90deg, transparent 18%, rgba(31, 217, 169, 0.9) 19% 20%, transparent 30%, transparent 66%, rgba(31, 217, 169, 0.72) 67% 68%, transparent 80%), repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.06) 0 1px, transparent 1px 12px); }
.process-icon.detection { background: radial-gradient(circle at 32% 45%, transparent 0 6px, rgba(228, 173, 84, 0.84) 7px 8px, transparent 9px), radial-gradient(circle at 70% 63%, transparent 0 6px, rgba(228, 173, 84, 0.84) 7px 8px, transparent 9px), repeating-linear-gradient(0deg, transparent 0 12px, rgba(255, 255, 255, 0.08) 12px 13px), repeating-linear-gradient(90deg, transparent 0 12px, rgba(255, 255, 255, 0.08) 12px 13px); }
.section-head .eyebrow::before {
  content: "";
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 10px;
  border-radius: 50%;
  background: var(--brass);
  box-shadow: 0 0 0 6px rgba(201, 137, 63, 0.12);
}
.chapter-grid {
  grid-template-columns: repeat(auto-fit, minmax(238px, 1fr));
  gap: 18px;
}
.chapter-card {
  min-height: 0;
  padding: 20px 20px 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 253, 248, 0.96), rgba(250, 244, 233, 0.86));
  box-shadow: 0 12px 30px rgba(47, 39, 28, 0.08), inset 0 1px 0 rgba(255,255,255,.9);
}
.chapter-card::before { display: none; }
.chapter-card::after {
  right: 16px;
  top: 12px;
  font-size: 56px;
  color: color-mix(in srgb, var(--card-accent) 7%, transparent);
}
.chapter-kicker span {
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: #65726b;
  font-size: 15px;
}
.chapter-card h3 {
  max-width: 92%;
  min-height: 64px;
  margin: 4px 0 12px;
  color: #1c2c2a;
  font-size: 27px;
  line-height: 1.12;
}
.chapter-visual {
  position: relative;
  z-index: 2;
  height: 118px;
  margin: 0 0 14px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 253, 248, 0.12), rgba(13, 71, 70, 0.03));
  overflow: hidden;
}
.chapter-visual svg { width: 100%; height: 100%; overflow: visible; }
.chapter-visual path,
.chapter-visual circle,
.chapter-visual rect {
  fill: none;
  stroke: var(--card-accent);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.78;
}
.chapter-visual text { fill: #203633; font-family: var(--serif); font-size: 18px; font-weight: 900; }
.chapter-visual .axis,
.chapter-visual .echo,
.chapter-visual .link,
.chapter-visual .arc { stroke: #7d8b84; stroke-width: 2; opacity: 0.65; }
.chapter-visual .dish,
.chapter-visual .target { fill: color-mix(in srgb, var(--card-accent) 75%, white); stroke: #173f3e; opacity: 0.9; }
.chapter-visual .small { opacity: 0.7; }
.chapter-visual .dot { fill: var(--card-accent); stroke: none; }
.chapter-visual .noise circle { fill: var(--card-accent); stroke: none; opacity: 0.35; }
.visual-radar { background: radial-gradient(circle at 63% 52%, rgba(13, 71, 70, 0.08), transparent 48%), linear-gradient(180deg, rgba(255,253,248,.1), rgba(13,71,70,.03)); }
.visual-flow rect { fill: rgba(255, 253, 248, 0.72); stroke-width: 2; }
.chapter-card p {
  min-height: 0;
  max-width: 100%;
  margin-bottom: 18px;
  color: #596962;
  font-size: 15.5px;
  line-height: 1.62;
}
.chapter-card .chapter-actions {
  width: auto;
  min-height: 0;
  margin: auto 0 0;
  padding: 0;
  border: 0;
  gap: 10px;
}
.chapter-actions .btn {
  flex: 1 1 96px;
  min-height: 38px;
  padding: 8px 11px;
  border-radius: 8px;
  font-size: 13px;
}
@media (min-width: 1120px) {
  .chapter-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 980px) {
  .hero-hud { right: -30px; top: 120px; width: 54vw; opacity: 0.62; }
  .telemetry { display: none; }
  .hero-process { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .hero-process i { display: none; }
}
@media (max-width: 720px) {
  .hero-banner { min-height: 760px; }
  .hero-copy p::before { font-size: 15px; }
  .hero-hud { top: 280px; right: -52px; width: 360px; opacity: 0.5; }
  .hero-process { left: 18px; right: 18px; bottom: 18px; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; padding: 14px; border-radius: 20px; }
  .process-icon { height: 34px; margin-bottom: 6px; }
  .hero-process div { font-size: 12px; }
  .chapter-visual { height: 104px; }
}

/* Home chapter cards: compact textbook-figure style. */
.chapters .chapter-grid {
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 16px;
}
.chapters .chapter-card {
  min-height: 286px;
  display: flex;
  flex-direction: column;
  padding: 18px;
  border: 1px solid rgba(91, 76, 53, 0.15);
  border-radius: 16px;
  background: #fbf4e8;
  box-shadow: 0 2px 10px rgba(47, 39, 28, 0.04);
  transform: none;
}
.chapters .chapter-card::before,
.chapters .chapter-card::after {
  display: none;
  content: none;
}
.chapters .chapter-card:hover {
  transform: none;
  border-color: rgba(13, 71, 70, 0.22);
  box-shadow: 0 5px 18px rgba(47, 39, 28, 0.07);
}
.chapters .chapter-kicker span {
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: #6f766f;
  font-family: var(--sans);
  font-size: 13px;
  font-weight: 800;
}
.chapters .chapter-card h3 {
  max-width: none;
  min-height: 0;
  margin: 6px 0 12px;
  color: #172522;
  font-size: 23px;
  line-height: 1.18;
  letter-spacing: -0.03em;
}
.chapters .chapter-visual,
.chapters .chapter-art {
  position: relative;
  z-index: 2;
  display: grid;
  place-items: center;
  height: 112px;
  margin: 0 0 14px;
  padding: 10px 12px;
  overflow: hidden;
  border: 1px solid rgba(55, 76, 71, 0.14);
  border-radius: 12px;
  background: #fffdf8;
  box-shadow: none;
}
.chapters .visual-radar,
.chapters .visual-wave,
.chapters .visual-pulse,
.chapters .visual-range,
.chapters .visual-doppler,
.chapters .visual-detect,
.chapters .visual-angle,
.chapters .visual-flow {
  background: #fffdf8;
}
.chapters .chapter-visual svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}
.chapters .chapter-visual path,
.chapters .chapter-visual circle,
.chapters .chapter-visual rect {
  fill: none;
  stroke: #2f4b47;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.9;
}
.chapters .chapter-visual text {
  fill: #243c38;
  font-family: var(--serif);
  font-size: 16px;
  font-weight: 700;
}
.chapters .chapter-visual .axis,
.chapters .chapter-visual .echo,
.chapters .chapter-visual .link,
.chapters .chapter-visual .arc {
  stroke: #7c8a83;
  stroke-width: 1.4;
  opacity: 0.78;
}
.chapters .chapter-visual .dish,
.chapters .chapter-visual .target,
.chapters .chapter-visual .dot,
.chapters .chapter-visual .noise circle {
  fill: #2f4b47;
  stroke: #2f4b47;
  opacity: 0.78;
}
.chapters .chapter-visual .small { opacity: 0.55; }
.chapters .visual-flow rect {
  fill: #fffdf8;
  stroke-width: 1.4;
}
.chapters .chapter-art img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  margin: 0;
  border-radius: 6px;
  background: transparent;
  box-shadow: none;
  filter: none;
}
.chapters .chapter-card p {
  min-height: 0;
  max-width: none;
  margin: 0 0 14px;
  color: #5d6963;
  font-size: 14.5px;
  line-height: 1.56;
}
.chapters .chapter-card .chapter-actions {
  width: auto;
  min-height: 0;
  margin: auto 0 0;
  padding: 12px 0 0;
  border-top: 1px solid rgba(55, 76, 71, 0.1);
  gap: 8px;
}
.chapters .chapter-actions .btn {
  flex: 1 1 92px;
  min-height: 36px;
  padding: 7px 10px;
  border-radius: 8px;
  border-color: rgba(55, 76, 71, 0.16);
  background: rgba(255, 253, 248, 0.75);
  box-shadow: none;
  font-size: 13px;
}
.chapters .chapter-actions .btn.primary {
  background: #173f3e;
  box-shadow: none;
}
.chapters .chapter-actions .btn:hover {
  transform: none;
  box-shadow: none;
}
@media (min-width: 1120px) {
  .chapters .chapter-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
  .chapters .chapter-card {
    min-height: 258px;
    padding: 16px;
  }
  .chapters .chapter-card h3 { font-size: 22px; }
  .chapters .chapter-visual,
  .chapters .chapter-art {
    height: 100px;
  }
}

/* AI-rendered textbook figures: blend the figure into the card paper instead of nesting a second card. */
.chapters .chapter-art {
  height: 132px;
  margin: 0 -4px 16px;
  padding: 0;
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.chapters .chapter-art img {
  object-fit: contain;
  border-radius: 0;
  background: transparent;
  opacity: 1;
  filter: contrast(1.06) saturate(0.86);
}
@media (max-width: 720px) {
  .chapters .chapter-art {
    height: 112px;
    margin-inline: -2px;
  }
}

/* Hero first screen: restore the clean headline area and add icon-led controls. */
.hero-mark .eyebrow {
  text-transform: none;
  letter-spacing: 0.035em;
  color: #9b6a2d;
  font-size: clamp(14px, 1.35vw, 18px);
}
.hero-copy p::before {
  content: none;
  display: none;
}
.hero-actions {
  gap: 16px;
  align-items: center;
}
.hero-actions .btn {
  gap: 10px;
  min-height: 54px;
  padding: 13px 22px;
  border-radius: 13px;
  font-size: 16px;
}
.hero-actions .btn-icon,
.hero-proof .stat-icon {
  display: inline-grid;
  place-items: center;
  flex: 0 0 auto;
  color: currentColor;
}
.hero-actions .btn-icon svg {
  width: 22px;
  height: 22px;
}
.hero-actions .btn svg,
.hero-proof svg {
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.hero-actions .btn-arrow {
  margin-left: 8px;
  font-size: 22px;
  line-height: 1;
}
.hero-proof {
  width: min(520px, 100%);
  min-height: 96px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  margin-top: 30px;
  padding: 18px 18px;
  overflow: hidden;
  border: 1px solid rgba(255, 253, 248, 0.34);
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(255, 253, 248, 0.24), rgba(12, 49, 47, 0.24)),
    rgba(11, 49, 48, 0.2);
  box-shadow: 0 22px 54px rgba(4, 33, 32, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.2);
  color: rgba(255, 250, 238, 0.94);
  font-family: var(--sans);
  backdrop-filter: blur(18px) saturate(1.08);
}
.hero-proof span {
  display: block;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}
.hero-stat {
  position: relative;
  display: grid;
  grid-template-columns: auto auto;
  grid-template-rows: auto auto;
  column-gap: 14px;
  align-items: center;
  justify-content: center;
  min-width: 0;
}
.hero-stat:not(:first-child)::before {
  content: "";
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 1px;
  background: rgba(255, 253, 248, 0.24);
}
.hero-proof .stat-icon {
  grid-row: 1 / 3;
  width: 36px;
  height: 36px;
  opacity: 0.92;
}
.hero-proof .stat-icon svg {
  width: 34px;
  height: 34px;
}
.hero-stat strong {
  color: #fffaf1;
  font-size: clamp(30px, 3.1vw, 42px);
  line-height: 0.95;
  font-weight: 900;
  letter-spacing: -0.04em;
}
.hero-stat > span:not(.stat-icon) {
  color: rgba(255, 250, 238, 0.88);
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
}
@media (max-width: 720px) {
  .hero-actions {
    gap: 10px;
  }
  .hero-actions .btn {
    flex: 1 1 100%;
    justify-content: flex-start;
    min-height: 48px;
    padding: 11px 16px;
  }
  .hero-actions .btn-arrow {
    margin-left: auto;
  }
  .hero-proof {
    min-height: 82px;
    padding: 14px 10px;
    border-radius: 16px;
  }
  .hero-stat {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    row-gap: 3px;
    text-align: center;
  }
  .hero-proof .stat-icon {
    grid-row: auto;
    justify-self: center;
    width: 26px;
    height: 26px;
  }
  .hero-proof .stat-icon svg {
    width: 24px;
    height: 24px;
  }
  .hero-stat strong {
    font-size: 26px;
  }
  .hero-stat > span:not(.stat-icon) {
    font-size: 12px;
  }
}

/* Hero correction: use the original background image, not the extra generated overlays. */
.hero-hud,
.hero-process {
  display: none;
}
.hero-art {
  background-image: url("../design/hero/radar-hero-clean.png");
  background-position: center;
  background-size: cover;
  filter: saturate(1.02) contrast(1);
  transform: scale(1.02);
}
.hero-banner::before {
  background:
    linear-gradient(90deg, rgba(251, 247, 239, 0.98) 0%, rgba(251, 247, 239, 0.9) 36%, rgba(251, 247, 239, 0.42) 68%, rgba(13, 71, 70, 0.04) 100%),
    linear-gradient(180deg, rgba(255, 253, 248, 0.02), rgba(12, 55, 54, 0.06));
}
.hero-copy {
  width: min(980px, 78%);
}
.hero-actions {
  flex-wrap: nowrap;
  width: max-content;
  max-width: 100%;
  gap: 12px;
}
.hero-actions .btn {
  flex: 0 0 auto;
  min-height: 50px;
  padding: 11px 17px;
  border-radius: 13px;
  font-size: 15px;
  white-space: nowrap;
}
.hero-actions .btn-icon svg {
  width: 20px;
  height: 20px;
}
.hero-actions .btn-arrow {
  margin-left: 4px;
  font-size: 20px;
}
@media (max-width: 980px) {
  .hero-actions {
    flex-wrap: wrap;
    width: auto;
  }
}

/* Reading mode: collapsible table of contents for centered, immersive chapters. */
.toc-toggle {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: rgba(13, 71, 70, 0.66);
  box-shadow: none;
  font-family: var(--sans);
  cursor: pointer;
  opacity: 0.78;
  transition: transform 0.18s ease, color 0.18s ease, opacity 0.18s ease;
}
.toc-toggle::before {
  content: "";
  position: absolute;
  inset: 5px;
  border-radius: inherit;
  background:
    radial-gradient(circle at 50% 35%, rgba(255, 253, 248, 0.72), transparent 58%),
    linear-gradient(135deg, rgba(13, 71, 70, 0.06), rgba(201, 137, 63, 0.08));
  opacity: 0;
  transition: opacity 0.18s ease;
}
.toc-toggle svg {
  position: relative;
  z-index: 1;
  width: 23px;
  height: 23px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.05;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.toc-toggle-rail {
  opacity: 0.34;
  stroke-width: 1.7;
}
.toc-toggle:hover {
  transform: translateX(-1px);
  color: var(--teal);
  opacity: 1;
}
.toc-toggle:hover::before {
  opacity: 1;
}
body.toc-collapsed .toc-toggle {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  color: var(--teal);
  opacity: 0.9;
}
body.toc-collapsed .toc-toggle::before {
  inset: 4px;
  opacity: 1;
  background:
    radial-gradient(circle at 38% 28%, rgba(255, 253, 248, 0.92), transparent 56%),
    linear-gradient(135deg, rgba(255, 253, 248, 0.5), rgba(135, 182, 162, 0.16));
}
body.toc-collapsed .article-layout {
  width: min(1060px, calc(100% - 32px));
  grid-template-columns: minmax(0, 1fr);
  gap: 0;
}
body.toc-collapsed .sidebar {
  position: fixed;
  left: max(18px, calc((100vw - 1060px) / 2 - 58px));
  top: 118px;
  z-index: 80;
  width: 44px;
  height: 44px;
  max-height: none;
  overflow: visible;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 253, 248, 0.42);
  box-shadow: 0 14px 34px rgba(47, 39, 28, 0.1);
  backdrop-filter: blur(14px) saturate(1.08);
}
body.toc-collapsed .sidebar > :not(.toc-toggle) {
  display: none;
}
body.toc-collapsed .article-main {
  width: 100%;
  grid-column: 1;
}
body.toc-collapsed .prose,
body.toc-collapsed .article-meta,
body.toc-collapsed .article-actions {
  max-width: 920px;
}
@media (max-width: 1080px) {
  .toc-toggle {
    top: 14px;
    right: 14px;
  }
  body.toc-collapsed .toc-toggle {
    position: absolute;
  }
  body.toc-collapsed .sidebar {
    left: 24px;
    top: 110px;
  }
}
@media (max-width: 720px) {
  .toc-toggle {
    width: 42px;
    height: 42px;
  }
  body.toc-collapsed .sidebar {
    left: 16px;
    top: auto;
    bottom: 18px;
    width: 42px;
    height: 42px;
  }
}
"""

JS = r"""
(function(){
  const bar=document.querySelector('.read-progress span');
  const tocLinks=[...document.querySelectorAll('.toc-link')];
  const subtocLinks=[...document.querySelectorAll('.subtoc-link')];
  const sections=tocLinks.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const subSections=subtocLinks.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const articleLayout=document.querySelector('.article-layout');
  const sidebar=document.querySelector('.sidebar');
  const storageKey='easy-radar-toc-collapsed';
  let tocToggle=null;
  function setTocCollapsed(collapsed){
    document.body.classList.toggle('toc-collapsed', collapsed);
    if(tocToggle){
      tocToggle.setAttribute('aria-expanded', String(!collapsed));
      const icon=collapsed
        ? '<svg viewBox="0 0 28 28" aria-hidden="true"><path class="toc-toggle-rail" d="M22 6.5v15"/><path d="m9.5 7.5 6.5 6.5-6.5 6.5"/><path d="m14.5 7.5 6.5 6.5-6.5 6.5"/></svg>'
        : '<svg viewBox="0 0 28 28" aria-hidden="true"><path class="toc-toggle-rail" d="M6 6.5v15"/><path d="m18.5 7.5-6.5 6.5 6.5 6.5"/><path d="m13.5 7.5-6.5 6.5 6.5 6.5"/></svg>';
      tocToggle.innerHTML=icon;
      tocToggle.setAttribute('aria-label', collapsed ? '展开目录' : '收起目录');
      tocToggle.setAttribute('title', collapsed ? '展开目录' : '收起目录');
    }
    try{ localStorage.setItem(storageKey, collapsed ? '1' : '0'); }catch(_){}
  }
  if(articleLayout && sidebar){
    tocToggle=document.createElement('button');
    tocToggle.type='button';
    tocToggle.className='toc-toggle';
    tocToggle.setAttribute('aria-controls','book-toc-sidebar');
    sidebar.id=sidebar.id || 'book-toc-sidebar';
    sidebar.appendChild(tocToggle);
    let saved=false;
    try{ saved=localStorage.getItem(storageKey)==='1'; }catch(_){}
    setTocCollapsed(saved);
    tocToggle.addEventListener('click',()=>setTocCollapsed(!document.body.classList.contains('toc-collapsed')));
  }
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
    let currentSub=null;
    const currentSection=current && current.closest ? current.closest('.chapter-section') : null;
    for(const sec of subSections){
      if(sec.closest('.chapter-section')===currentSection && sec.getBoundingClientRect().top<260) currentSub=sec;
    }
    tocLinks.forEach(a=>a.classList.toggle('active', current && a.getAttribute('href')==='#'+current.id));
    subtocLinks.forEach(a=>a.classList.toggle('active', currentSub && a.getAttribute('href')==='#'+currentSub.id));
    document.querySelectorAll('.toc-section').forEach(group=>{
      group.classList.toggle('open', current && group.dataset.section===current.id);
    });
  }
  function scrollToHash(hash){
    if(!hash || hash==='#')return false;
    const target=document.getElementById(decodeURIComponent(hash.slice(1)));
    if(!target)return false;
    const offset=document.querySelector('.article-top')?96:0;
    const top=target.getBoundingClientRect().top+window.scrollY-offset;
    window.scrollTo({top:Math.max(0,top),behavior:'smooth'});
    return true;
  }
  document.addEventListener('click',event=>{
    const link=event.target.closest('.toc-link,.subtoc-link');
    if(!link || !link.hash || link.pathname!==window.location.pathname)return;
    if(!scrollToHash(link.hash))return;
    event.preventDefault();
    history.pushState(null,'',link.hash);
    updateActive();
    window.setTimeout(updateActive,350);
    window.setTimeout(updateActive,900);
  });
  window.addEventListener('scroll',()=>{updateProgress();updateActive();},{passive:true});
  window.addEventListener('resize',()=>{updateProgress();updateActive();});
  window.addEventListener('load',()=>{
    if(location.hash)scrollToHash(location.hash);
    window.setTimeout(updateActive,350);
  });
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
