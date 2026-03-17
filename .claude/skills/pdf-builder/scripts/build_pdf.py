#!/usr/bin/env python3
"""
build_pdf.py -- Convert markdown chapters into a typeset PDF book.

Uses the python `markdown` library to convert each chapter to HTML,
assembles them with a cover page, title page, copyright page, and
table of contents, applies a CSS stylesheet, and renders the result
to PDF via WeasyPrint.

Produces professional Korean book-grade typesetting with proper
chapter openings, running headers, and B5 page format.
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("ERROR: 'markdown' package is required. Install with: pip install markdown")

try:
    from weasyprint import HTML
except ImportError:
    sys.exit("ERROR: 'weasyprint' package is required. Install with: pip install weasyprint")


# ---------------------------------------------------------------------------
# Markdown conversion
# ---------------------------------------------------------------------------

MARKDOWN_EXTENSIONS = [
    "fenced_code",
    "codehilite",
    "tables",
    "toc",
    "pymdownx.superfences",
    "smarty",
    "attr_list",
]

MARKDOWN_EXTENSION_CONFIGS = {
    "codehilite": {
        "css_class": "highlight",
        "linenums": False,
        "guess_lang": True,
    },
    "toc": {
        "permalink": False,
    },
}


def convert_markdown_to_html(md_text: str) -> str:
    """Convert a markdown string to an HTML fragment."""
    md = markdown.Markdown(
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
        output_format="html",
    )
    return md.convert(md_text)


# ---------------------------------------------------------------------------
# Chapter discovery
# ---------------------------------------------------------------------------

CHAPTER_PATTERN = re.compile(r"^ch(\d+)_.*\.md$", re.IGNORECASE)


def discover_chapters(chapters_dir: str) -> list[Path]:
    """Return a sorted list of chapter markdown files in *chapters_dir*."""
    chapters_path = Path(chapters_dir)
    if not chapters_path.is_dir():
        sys.exit(f"ERROR: Chapters directory does not exist: {chapters_dir}")

    chapter_files: list[tuple[int, Path]] = []
    for entry in chapters_path.iterdir():
        m = CHAPTER_PATTERN.match(entry.name)
        if m and entry.is_file():
            chapter_files.append((int(m.group(1)), entry))

    if not chapter_files:
        sys.exit(f"ERROR: No chapter files (ch{{NN}}_*.md) found in {chapters_dir}")

    chapter_files.sort(key=lambda t: t[0])
    return [path for _, path in chapter_files]


# ---------------------------------------------------------------------------
# Image path resolution
# ---------------------------------------------------------------------------

def resolve_image_paths(html: str, images_dir: str | None) -> str:
    """Replace relative image `src` attributes with absolute file:// URIs.

    WeasyPrint needs absolute paths (or URLs) to locate images during
    rendering.  This function resolves paths relative to *images_dir*
    as well as generic relative paths.
    """
    if images_dir:
        abs_images = str(Path(images_dir).resolve())
    else:
        abs_images = None

    def _replace(match: re.Match) -> str:
        src = match.group(1)
        # Already absolute or a URL -- leave it alone.
        if src.startswith(("http://", "https://", "file://", "/")):
            return match.group(0)

        # Try to resolve relative to the images directory first.
        if abs_images:
            candidate = os.path.join(abs_images, src)
            if os.path.isfile(candidate):
                return f'src="file://{candidate}"'

        # Fall back to resolving relative to cwd.
        candidate = str(Path(src).resolve())
        if os.path.isfile(candidate):
            return f'src="file://{candidate}"'

        # Return original if nothing found (WeasyPrint will warn).
        return match.group(0)

    return re.sub(r'src="([^"]+)"', _replace, html)


# ---------------------------------------------------------------------------
# Chapter HTML wrapping with proper book structure
# ---------------------------------------------------------------------------

H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
H2_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
TAG_STRIP_RE = re.compile(r"<[^>]+>")


def wrap_chapter(chapter_html: str, chapter_num: int) -> str:
    """Wrap a chapter HTML fragment with proper book chapter-opening structure.

    Extracts the H1 title from the chapter body, creates a structured
    chapter opening with chapter number, title, and decorative rule,
    then appends the remaining body content.

    Also adds id attributes to H2 elements for TOC linking.
    """
    # Extract H1 title
    h1_match = H1_RE.search(chapter_html)
    if h1_match:
        title_html = h1_match.group(1).strip()
        title_text = TAG_STRIP_RE.sub("", title_html).strip()
        # Remove the H1 from the body
        body_html = chapter_html[:h1_match.start()] + chapter_html[h1_match.end():]
    else:
        title_text = f"Chapter {chapter_num}"
        body_html = chapter_html

    # Add id attributes to H2 elements for TOC linking
    section_counter = 0

    def _add_h2_id(match: re.Match) -> str:
        nonlocal section_counter
        section_counter += 1
        tag_content = match.group(0)
        # Check if id already exists
        if 'id="' in tag_content or "id='" in tag_content:
            return tag_content
        return tag_content.replace("<h2", f'<h2 id="ch{chapter_num}-s{section_counter}"', 1)

    body_html = re.sub(r"<h2\b[^>]*>", _add_h2_id, body_html)

    # Clean up leading whitespace in body
    body_html = body_html.strip()

    return (
        f'<section class="chapter" id="ch{chapter_num}">\n'
        f'  <div class="chapter-opening">\n'
        f'    <span class="chapter-number">Chapter {chapter_num}</span>\n'
        f'    <h1 class="chapter-title">{title_text}</h1>\n'
        f'    <div class="chapter-rule"></div>\n'
        f'  </div>\n'
        f'  {body_html}\n'
        f'</section>'
    )


# ---------------------------------------------------------------------------
# Table of contents generation
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"<(h[12])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)


def generate_toc(chapter_htmls: list[str], chapter_nums: list[int]) -> str:
    """Build an HTML table-of-contents section from chapter headings.

    Uses anchor links and target-counter for page numbers via CSS.
    """
    items: list[str] = []
    for idx, html_fragment in enumerate(chapter_htmls):
        chapter_num = chapter_nums[idx]
        section_counter = 0
        for m in HEADING_RE.finditer(html_fragment):
            level = m.group(1).lower()
            text = TAG_STRIP_RE.sub("", m.group(2)).strip()

            if level == "h1":
                items.append(
                    f'<li class="toc-chapter">'
                    f'<a href="#ch{chapter_num}">'
                    f'{text}'
                    f'<span class="toc-page-num"></span>'
                    f'</a></li>'
                )
            elif level == "h2":
                section_counter += 1
                items.append(
                    f'<li class="toc-section">'
                    f'<a href="#ch{chapter_num}-s{section_counter}">'
                    f'{text}'
                    f'<span class="toc-page-num"></span>'
                    f'</a></li>'
                )

    if not items:
        return ""

    toc_html = (
        '<div class="toc-page">\n'
        '<h1>Table of Contents</h1>\n'
        '<ul class="toc-list">\n'
        + "\n".join(items)
        + "\n</ul>\n</div>\n"
    )
    return toc_html


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------

def render_cover(
    template_path: str | None,
    title: str,
    subtitle: str,
    author: str,
    date_str: str,
) -> str:
    """Return the cover page HTML.

    If *template_path* is given and the file exists, placeholders inside
    it are replaced.  Otherwise a simple built-in cover is used.
    """
    if template_path and os.path.isfile(template_path):
        raw = Path(template_path).read_text(encoding="utf-8")
    else:
        raw = _default_cover_html()

    html = (
        raw.replace("{{TITLE}}", title)
        .replace("{{SUBTITLE}}", subtitle)
        .replace("{{AUTHOR}}", author)
        .replace("{{DATE}}", date_str)
    )
    return html


def _default_cover_html() -> str:
    return """\
<section class="cover">
  <div class="cover-page">
    <div class="cover-content">
      <h1 class="cover-title">{{TITLE}}</h1>
      <p class="cover-subtitle">{{SUBTITLE}}</p>
      <div class="cover-divider"></div>
      <p class="cover-author">{{AUTHOR}}</p>
      <p class="cover-date">{{DATE}}</p>
    </div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Title page
# ---------------------------------------------------------------------------

def render_title_page(title: str, subtitle: str, author: str) -> str:
    """Return the title page HTML."""
    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""
    return (
        '<section class="title-page">\n'
        '  <div class="title-page-content">\n'
        f'    <h1>{title}</h1>\n'
        f'    {subtitle_html}\n'
        f'    <p class="author">{author}</p>\n'
        '  </div>\n'
        '</section>\n'
    )


# ---------------------------------------------------------------------------
# Copyright page
# ---------------------------------------------------------------------------

def render_copyright_page(author: str, date_str: str) -> str:
    """Return the copyright page HTML."""
    year = date_str[:4] if len(date_str) >= 4 else str(datetime.now().year)
    return (
        '<section class="copyright-page">\n'
        '  <div class="copyright-content">\n'
        f'    <p>&copy; {year} {author}. All rights reserved.</p>\n'
        f'    <p>Generated by Ebook Writer Agent</p>\n'
        f'    <p>{date_str}</p>\n'
        '  </div>\n'
        '</section>\n'
    )


# ---------------------------------------------------------------------------
# Full document assembly
# ---------------------------------------------------------------------------

def assemble_document(
    cover_html: str,
    title_page_html: str,
    copyright_page_html: str,
    toc_html: str,
    chapter_sections: list[str],
    css_text: str,
    title: str,
    language: str,
) -> str:
    """Combine all parts into a single self-contained HTML document."""
    chapters_combined = "\n".join(chapter_sections)

    # Hidden element to provide book title for running headers via string-set
    book_title_meta = f'<span class="book-title-meta" style="display:none">{title}</span>'

    html = f"""\
<!DOCTYPE html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{css_text}
</style>
</head>
<body>
{book_title_meta}
{cover_html}
{title_page_html}
{copyright_page_html}
{toc_html}
{chapters_combined}
</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------

def render_pdf(html_string: str, output_path: str, base_url: str | None = None) -> None:
    """Render *html_string* to a PDF file at *output_path* using WeasyPrint."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = HTML(string=html_string, base_url=base_url or ".")
        doc.write_pdf(str(out))
    except Exception as exc:
        sys.exit(f"ERROR: WeasyPrint failed to render PDF.\n  {type(exc).__name__}: {exc}")

    # Verify output.
    if not out.is_file():
        sys.exit(f"ERROR: PDF file was not created at {output_path}")
    if out.stat().st_size == 0:
        sys.exit(f"ERROR: PDF file is empty (0 bytes) at {output_path}")

    print(f"PDF created successfully: {output_path} ({out.stat().st_size:,} bytes)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Convert markdown chapters into a typeset PDF book.",
    )
    p.add_argument(
        "--chapters",
        required=True,
        help="Directory containing ch{NN}_*.md chapter files.",
    )
    p.add_argument(
        "--images",
        default=None,
        help="Directory containing images referenced in chapters.",
    )
    p.add_argument(
        "--output",
        required=True,
        help="Output PDF file path.",
    )
    p.add_argument(
        "--language",
        default="ko",
        choices=["ko", "en"],
        help="Language code (default: ko).",
    )
    p.add_argument(
        "--styles",
        default=None,
        help="Path to CSS stylesheet for the book layout.",
    )
    p.add_argument(
        "--cover",
        default=None,
        help="Path to cover page HTML template.",
    )
    p.add_argument(
        "--title",
        required=True,
        help="Book title.",
    )
    p.add_argument(
        "--subtitle",
        default="",
        help="Book subtitle (optional).",
    )
    p.add_argument(
        "--author",
        default="Generated by Ebook Writer Agent",
        help="Author name for the cover page.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # 1. Discover and read chapters.
    chapter_paths = discover_chapters(args.chapters)
    print(f"Found {len(chapter_paths)} chapter(s).")

    chapter_md_texts: list[str] = []
    for cp in chapter_paths:
        chapter_md_texts.append(cp.read_text(encoding="utf-8"))
        print(f"  - {cp.name}")

    # 2. Convert each chapter to HTML.
    chapter_htmls: list[str] = []
    for md_text in chapter_md_texts:
        chapter_htmls.append(convert_markdown_to_html(md_text))

    # 3. Resolve image paths.
    chapter_htmls = [
        resolve_image_paths(h, args.images) for h in chapter_htmls
    ]

    # 4. Determine chapter numbers from filenames.
    chapter_nums: list[int] = []
    for cp in chapter_paths:
        m = CHAPTER_PATTERN.match(cp.name)
        if m:
            chapter_nums.append(int(m.group(1)))
        else:
            chapter_nums.append(len(chapter_nums) + 1)

    # 5. Generate table of contents (before wrapping, so we can read raw H1/H2).
    toc_html = generate_toc(chapter_htmls, chapter_nums)

    # 6. Wrap each chapter with proper book structure.
    chapter_sections: list[str] = []
    for idx, ch_html in enumerate(chapter_htmls):
        chapter_sections.append(wrap_chapter(ch_html, chapter_nums[idx]))

    # 7. Render cover page.
    date_str = datetime.now().strftime("%Y-%m-%d")
    cover_html = render_cover(
        template_path=args.cover,
        title=args.title,
        subtitle=args.subtitle,
        author=args.author,
        date_str=date_str,
    )

    # 8. Render title page.
    title_page_html = render_title_page(
        title=args.title,
        subtitle=args.subtitle,
        author=args.author,
    )

    # 9. Render copyright page.
    copyright_page_html = render_copyright_page(
        author=args.author,
        date_str=date_str,
    )

    # 10. Load CSS.
    css_text = ""
    if args.styles and os.path.isfile(args.styles):
        css_text = Path(args.styles).read_text(encoding="utf-8")
        print(f"Loaded stylesheet: {args.styles}")
    elif args.styles:
        print(f"WARNING: Stylesheet not found at {args.styles}, using defaults.")

    # 11. Assemble full HTML document.
    full_html = assemble_document(
        cover_html=cover_html,
        title_page_html=title_page_html,
        copyright_page_html=copyright_page_html,
        toc_html=toc_html,
        chapter_sections=chapter_sections,
        css_text=css_text,
        title=args.title,
        language=args.language,
    )

    # 12. Determine base_url for WeasyPrint (for resolving relative resources).
    base_url = str(Path(args.chapters).resolve())

    # 13. Render to PDF.
    print("Rendering PDF...")
    render_pdf(full_html, args.output, base_url=base_url)


if __name__ == "__main__":
    main()
