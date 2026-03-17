#!/usr/bin/env python3
"""
build_pdf.py -- Convert markdown chapters into a typeset PDF book.

Uses the python `markdown` library to convert each chapter to HTML,
assembles them with a cover page and table of contents, applies a CSS
stylesheet, and renders the result to PDF via WeasyPrint.
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
# Table of contents generation
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"<(h[12])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
TAG_STRIP_RE = re.compile(r"<[^>]+>")


def generate_toc(chapter_htmls: list[str]) -> str:
    """Build an HTML table-of-contents section from chapter headings."""
    items: list[str] = []
    for html_fragment in chapter_htmls:
        for m in HEADING_RE.finditer(html_fragment):
            level = m.group(1).lower()
            text = TAG_STRIP_RE.sub("", m.group(2)).strip()
            css_class = "toc-h1" if level == "h1" else "toc-h2"
            items.append(f'<li class="{css_class}">{text}</li>')

    if not items:
        return ""

    toc_html = (
        '<div class="toc-page">\n'
        "<h1>Table of Contents</h1>\n"
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
<div class="cover-page">
  <div class="cover-content">
    <h1 class="cover-title">{{TITLE}}</h1>
    <p class="cover-subtitle">{{SUBTITLE}}</p>
    <p class="cover-author">{{AUTHOR}}</p>
    <p class="cover-date">{{DATE}}</p>
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# Full document assembly
# ---------------------------------------------------------------------------

def assemble_document(
    cover_html: str,
    toc_html: str,
    chapter_htmls: list[str],
    css_text: str,
    title: str,
    language: str,
) -> str:
    """Combine all parts into a single self-contained HTML document."""
    chapters_combined = "\n".join(
        f'<section class="chapter">\n{ch}\n</section>' for ch in chapter_htmls
    )

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
{cover_html}
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

    # 4. Generate table of contents.
    toc_html = generate_toc(chapter_htmls)

    # 5. Render cover page.
    date_str = datetime.now().strftime("%Y-%m-%d")
    cover_html = render_cover(
        template_path=args.cover,
        title=args.title,
        subtitle=args.subtitle,
        author=args.author,
        date_str=date_str,
    )

    # 6. Load CSS.
    css_text = ""
    if args.styles and os.path.isfile(args.styles):
        css_text = Path(args.styles).read_text(encoding="utf-8")
        print(f"Loaded stylesheet: {args.styles}")
    elif args.styles:
        print(f"WARNING: Stylesheet not found at {args.styles}, using defaults.")

    # 7. Assemble full HTML document.
    full_html = assemble_document(
        cover_html=cover_html,
        toc_html=toc_html,
        chapter_htmls=chapter_htmls,
        css_text=css_text,
        title=args.title,
        language=args.language,
    )

    # 8. Determine base_url for WeasyPrint (for resolving relative resources).
    base_url = str(Path(args.chapters).resolve())

    # 9. Render to PDF.
    print("Rendering PDF...")
    render_pdf(full_html, args.output, base_url=base_url)


if __name__ == "__main__":
    main()
