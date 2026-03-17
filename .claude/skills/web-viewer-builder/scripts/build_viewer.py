#!/usr/bin/env python3
"""
build_viewer.py — Generate a PDF.js-based web viewer for the ebook.

Takes generated PDFs and produces an index.html that renders them
with a book-spread layout, page-turn animation, chapter sidebar,
and language toggle.

Usage:
    python3 build_viewer.py \
        --pdf-primary output/final/book_ko.pdf \
        --pdf-secondary output/final/book_en.pdf \
        --output output/web-viewer/ \
        --template .claude/skills/web-viewer-builder/references/viewer_template.html \
        --title "Book Title" \
        --title-secondary "Book Title (EN)" \
        --primary-lang ko \
        --secondary-lang en
"""

import argparse
import shutil
import sys
from pathlib import Path


LANG_CONFIG = {
    "ko": {
        "label": "한국어",
        "toc_label": "목차",
    },
    "en": {
        "label": "English",
        "toc_label": "Contents",
    },
}


def main():
    p = argparse.ArgumentParser(description="Build PDF.js web viewer for ebook")
    p.add_argument("--pdf-primary", required=True, help="Path to primary language PDF")
    p.add_argument("--pdf-secondary", default=None, help="Path to secondary language PDF")
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--template", required=True, help="Path to viewer_template.html")
    p.add_argument("--title", required=True, help="Book title (primary language)")
    p.add_argument("--title-secondary", default="", help="Book title (secondary language)")
    p.add_argument("--primary-lang", default="ko", choices=list(LANG_CONFIG.keys()), help="Primary language code")
    p.add_argument("--secondary-lang", default="en", choices=list(LANG_CONFIG.keys()), help="Secondary language code")
    args = p.parse_args()

    # Validate inputs
    pdf_primary = Path(args.pdf_primary)
    if not pdf_primary.is_file():
        sys.exit(f"ERROR: Primary PDF not found: {pdf_primary}")

    template_path = Path(args.template)
    if not template_path.is_file():
        sys.exit(f"ERROR: Template not found: {template_path}")

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy PDFs to output directory
    primary_pdf_name = f"book_{args.primary_lang}.pdf"
    shutil.copy2(pdf_primary, out_dir / primary_pdf_name)
    print(f"Copied: {pdf_primary} -> {out_dir / primary_pdf_name}")

    secondary_pdf_name = f"book_{args.secondary_lang}.pdf"
    if args.pdf_secondary and Path(args.pdf_secondary).is_file():
        shutil.copy2(args.pdf_secondary, out_dir / secondary_pdf_name)
        print(f"Copied: {args.pdf_secondary} -> {out_dir / secondary_pdf_name}")
    else:
        secondary_pdf_name = primary_pdf_name  # fallback to primary
        print("No secondary PDF; both buttons will load the primary PDF.")

    # Language config
    pl = LANG_CONFIG[args.primary_lang]
    sl = LANG_CONFIG[args.secondary_lang]

    title_secondary = args.title_secondary or args.title

    # Read and fill template
    html = template_path.read_text(encoding="utf-8")

    replacements = {
        "{{LANG}}": args.primary_lang,
        "{{TITLE}}": args.title,
        "{{TITLE_SECONDARY}}": title_secondary,
        "{{PRIMARY_PDF}}": primary_pdf_name,
        "{{SECONDARY_PDF}}": secondary_pdf_name,
        "{{PRIMARY_LABEL}}": pl["label"],
        "{{SECONDARY_LABEL}}": sl["label"],
        "{{PRIMARY_TOC_LABEL}}": pl["toc_label"],
        "{{SECONDARY_TOC_LABEL}}": sl["toc_label"],
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    # Write index.html
    index_path = out_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    print(f"Written: {index_path}")
    print("Build complete!")


if __name__ == "__main__":
    main()
