#!/usr/bin/env python3
"""
build_viewer.py — Generate a single-page HTML ebook viewer from markdown chapters.

Reads Korean and English chapter .md files, converts them to HTML, splits them
into pages (~800 words each), and injects them into the viewer template to
produce a self-contained, deployable index.html.

Usage:
    python3 build_viewer.py \
        --chapters-ko output/chapters/ko/ \
        --chapters-en output/chapters/en/ \
        --images output/images/ \
        --output output/web-viewer/ \
        --template .claude/skills/web-viewer-builder/references/viewer_template.html \
        --title "Book Title"
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print("Error: 'markdown' library is required. Install it with: pip install markdown")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a single-page HTML ebook viewer from markdown chapters."
    )
    parser.add_argument(
        "--chapters-ko",
        required=True,
        help="Directory containing Korean chapter .md files",
    )
    parser.add_argument(
        "--chapters-en",
        required=True,
        help="Directory containing English chapter .md files",
    )
    parser.add_argument(
        "--images",
        required=True,
        help="Directory containing book images",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for the generated web viewer",
    )
    parser.add_argument(
        "--template",
        required=True,
        help="Path to the HTML template file",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Book title displayed in the viewer",
    )
    return parser.parse_args()


def get_sorted_chapter_files(directory: str) -> list[Path]:
    """Return chapter .md files sorted by chapter number."""
    chapter_dir = Path(directory)
    if not chapter_dir.is_dir():
        print(f"Warning: Chapter directory not found: {directory}")
        return []

    md_files = list(chapter_dir.glob("*.md"))

    def extract_number(path: Path) -> int:
        match = re.search(r"(\d+)", path.stem)
        return int(match.group(1)) if match else 0

    return sorted(md_files, key=extract_number)


def read_chapter(filepath: Path) -> tuple[str, str]:
    """Read a chapter file and return (title, markdown_content).

    The title is extracted from the first H1 heading. If no H1 is found,
    the filename is used as the title.
    """
    text = filepath.read_text(encoding="utf-8")

    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        title = filepath.stem.replace("_", " ").replace("-", " ").title()

    return title, text


def markdown_to_html(md_text: str) -> str:
    """Convert markdown text to HTML."""
    extensions = [
        "fenced_code",
        "codehilite",
        "tables",
        "toc",
        "nl2br",
    ]
    extension_configs = {
        "codehilite": {
            "css_class": "code-highlight",
            "guess_lang": False,
        },
    }
    return markdown.markdown(
        md_text,
        extensions=extensions,
        extension_configs=extension_configs,
    )


def split_into_pages(html_content: str, words_per_page: int = 800) -> list[str]:
    """Split HTML content into pages of approximately `words_per_page` words.

    Splits at paragraph boundaries (<p>, <h1>-<h6>, <pre>, <table>, <ul>, <ol>,
    <div>, <blockquote>) to avoid breaking mid-element.
    """
    block_pattern = re.compile(
        r"(<(?:p|h[1-6]|pre|table|ul|ol|div|blockquote|hr)[\s>].*?</(?:p|h[1-6]|pre|table|ul|ol|div|blockquote)>|<hr\s*/?>)",
        re.DOTALL | re.IGNORECASE,
    )
    blocks = block_pattern.findall(html_content)

    if not blocks:
        # Fallback: if no block-level elements found, return entire content as one page
        return [html_content] if html_content.strip() else []

    pages = []
    current_page_blocks = []
    current_word_count = 0

    for block in blocks:
        # Count words by stripping HTML tags
        text_only = re.sub(r"<[^>]+>", "", block)
        word_count = len(text_only.split())

        # If adding this block would exceed the limit and we already have content,
        # start a new page (but always include at least one block per page)
        if current_word_count + word_count > words_per_page and current_page_blocks:
            pages.append("\n".join(current_page_blocks))
            current_page_blocks = []
            current_word_count = 0

        current_page_blocks.append(block)
        current_word_count += word_count

    # Don't forget the last page
    if current_page_blocks:
        pages.append("\n".join(current_page_blocks))

    return pages


def extract_chapter_number(filepath: Path) -> int:
    """Extract chapter number from filename."""
    match = re.search(r"(\d+)", filepath.stem)
    return int(match.group(1)) if match else 0


def build_pages_html(
    chapter_files: list[Path], lang: str
) -> tuple[list[str], list[dict]]:
    """Process chapter files and return (page_divs, toc_entries).

    Each page div:
        <div class="page" data-lang="ko" data-chapter="1" data-page="1">
            ...content...
        </div>

    Each toc entry:
        {"chapter": 1, "title": "...", "page_start": 1}
    """
    page_divs = []
    toc_entries = []
    global_page_num = 1

    for filepath in chapter_files:
        chapter_num = extract_chapter_number(filepath)
        title, md_text = read_chapter(filepath)
        html_content = markdown_to_html(md_text)
        pages = split_into_pages(html_content)

        if not pages:
            continue

        toc_entries.append(
            {
                "chapter": chapter_num,
                "title": title,
                "page_start": global_page_num,
            }
        )

        for local_page, page_html in enumerate(pages, start=1):
            div = (
                f'<div class="page" data-lang="{lang}" '
                f'data-chapter="{chapter_num}" data-page="{global_page_num}">\n'
                f"{page_html}\n"
                f"</div>"
            )
            page_divs.append(div)
            global_page_num += 1

    return page_divs, toc_entries


def build_toc_html(toc_entries: list[dict], lang: str) -> str:
    """Generate table of contents HTML list items."""
    items = []
    for entry in toc_entries:
        chapter = entry["chapter"]
        title = entry["title"]
        page_start = entry["page_start"]
        item = (
            f'<li class="toc-item" data-lang="{lang}" '
            f'data-target-page="{page_start}">'
            f'<span class="toc-chapter-num">{chapter}.</span> {title}</li>'
        )
        items.append(item)
    return "\n".join(items)


def copy_images(src_dir: str, output_dir: str):
    """Copy images from source to output/images/ directory."""
    src_path = Path(src_dir)
    if not src_path.is_dir():
        print(f"Warning: Images directory not found: {src_dir}")
        return

    dest_path = Path(output_dir) / "images"
    dest_path.mkdir(parents=True, exist_ok=True)

    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
    copied = 0

    for img_file in src_path.iterdir():
        if img_file.suffix.lower() in image_extensions:
            shutil.copy2(img_file, dest_path / img_file.name)
            copied += 1

    print(f"Copied {copied} image(s) to {dest_path}")


def main():
    args = parse_args()

    # Read the template
    template_path = Path(args.template)
    if not template_path.is_file():
        print(f"Error: Template file not found: {args.template}")
        sys.exit(1)

    template = template_path.read_text(encoding="utf-8")

    # Process Korean chapters
    ko_files = get_sorted_chapter_files(args.chapters_ko)
    print(f"Found {len(ko_files)} Korean chapter(s)")
    ko_page_divs, ko_toc = build_pages_html(ko_files, "ko")

    # Process English chapters
    en_files = get_sorted_chapter_files(args.chapters_en)
    print(f"Found {len(en_files)} English chapter(s)")
    en_page_divs, en_toc = build_pages_html(en_files, "en")

    # Build combined pages HTML
    all_pages = "\n".join(ko_page_divs + en_page_divs)

    # Build TOC HTML
    toc_html = build_toc_html(ko_toc, "ko") + "\n" + build_toc_html(en_toc, "en")

    # Total page counts
    total_ko = len(ko_page_divs)
    total_en = len(en_page_divs)

    print(f"Total pages — KO: {total_ko}, EN: {total_en}")

    # Inject into template
    output_html = template
    output_html = output_html.replace("{{TITLE}}", args.title)
    output_html = output_html.replace("{{TOC_ITEMS}}", toc_html)
    output_html = output_html.replace("{{PAGES}}", all_pages)
    output_html = output_html.replace("{{TOTAL_PAGES_KO}}", str(total_ko))
    output_html = output_html.replace("{{TOTAL_PAGES_EN}}", str(total_en))

    # Create output directory and write index.html
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "index.html"
    output_file.write_text(output_html, encoding="utf-8")
    print(f"Written: {output_file}")

    # Copy images
    copy_images(args.images, args.output)

    print("Build complete!")


if __name__ == "__main__":
    main()
