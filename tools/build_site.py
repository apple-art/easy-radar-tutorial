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
ASSET_VERSION = "20260502-modern6"
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
    <div class="toplinks"><a href="#chapters">章节</a><a href="{html_attr(github_tree_url('matlab'))}">MATLAB</a><a href="{html_attr(github_tree_url('pdf'))}">PDF</a><a href="{html_attr(GITHUB_URL)}">GitHub</a></div>
  </nav>
  <div class="hero-shell reveal">
    <div class="hero-banner">
      <div class="hero-art" aria-hidden="true"></div>
      <div class="hero-copy">
        <div class="hero-mark"><img src="design/icon-concepts/logo-mark-light.svg" alt="项目图标"><span class="eyebrow">Radar signal processing</span></div>
        <h1>易懂的雷达信号处理教程</h1>
        <p>面向学生与工程师</p>
        <div class="hero-actions"><a class="btn primary" href="chapters/ch01.html">开始阅读</a><a class="btn" href="#chapters">选择章节</a><a class="btn ghost" href="{html_attr(github_tree_url('matlab'))}">MATLAB 代码</a></div>
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
    <div class="section-head reveal"><p class="eyebrow">Read online</p><h2>在线章节</h2><p>像浏览现代技术文档一样阅读：左侧章节、正文公式、PDF 与 MATLAB 代码入口都放在手边。</p></div>
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
"""

JS = r"""
(function(){
  const bar=document.querySelector('.read-progress span');
  const tocLinks=[...document.querySelectorAll('.toc-link')];
  const subtocLinks=[...document.querySelectorAll('.subtoc-link')];
  const sections=tocLinks.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const subSections=subtocLinks.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
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
