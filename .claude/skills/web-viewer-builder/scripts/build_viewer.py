#!/usr/bin/env python3
"""
build_viewer.py — Generate a PDF.js-based web viewer for the ebook.

Extracts chapter TOC from PDFs at build time (using PyMuPDF) and embeds
it as JSON in the HTML, so the sidebar works instantly without client-side
PDF text scanning.

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
import json
import re
import shutil
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

LANG_CONFIG = {
    "ko": {"label": "한국어", "toc_label": "목차"},
    "en": {"label": "English", "toc_label": "Contents"},
}


def extract_toc(pdf_path: str) -> list[dict]:
    """Extract chapter start pages from a PDF using font-size detection.

    Looks for large text (>=14pt) in the top 40% of each page that matches
    chapter heading patterns (제N장 or Chapter N).
    """
    if fitz is None:
        print("WARNING: PyMuPDF not installed. TOC will be empty.")
        return []

    doc = fitz.open(pdf_path)
    chapters = []

    for p in range(doc.page_count):
        page = doc[p]
        page_h = page.rect.height

        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:
                continue
            # Only top 40% of the page
            if block["bbox"][1] > page_h * 0.40:
                continue

            for line in block["lines"]:
                text = "".join(span["text"] for span in line["spans"]).strip()
                font_size = max((span["size"] for span in line["spans"]), default=0)

                # Chapter headings use large font (>= 14pt)
                if font_size < 14:
                    continue

                m = re.match(r"제(\d+)장", text) or re.match(
                    r"Chapter\s+(\d+)", text, re.I
                )
                if m:
                    ch_num = int(m.group(1))
                    # Skip TOC/front-matter pages (cover, title, copyright, toc)
                    if p + 1 <= 8:
                        continue
                    # Skip duplicates
                    if any(c["ch"] == ch_num for c in chapters):
                        continue
                    # Clean title
                    title = re.sub(r"\s+", " ", text).strip()
                    if len(title) > 55:
                        title = title[:53] + "..."
                    chapters.append({"ch": ch_num, "t": title, "p": p + 1})
                    break
            else:
                continue
            break

    chapters.sort(key=lambda x: x["ch"])
    return chapters


def main():
    p = argparse.ArgumentParser(description="Build PDF.js web viewer for ebook")
    p.add_argument("--pdf-primary", required=True)
    p.add_argument("--pdf-secondary", default=None)
    p.add_argument("--output", required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--title-secondary", default="")
    p.add_argument("--primary-lang", default="ko", choices=list(LANG_CONFIG.keys()))
    p.add_argument("--secondary-lang", default="en", choices=list(LANG_CONFIG.keys()))
    args = p.parse_args()

    pdf_primary = Path(args.pdf_primary)
    if not pdf_primary.is_file():
        sys.exit(f"ERROR: Primary PDF not found: {pdf_primary}")
    template_path = Path(args.template)
    if not template_path.is_file():
        sys.exit(f"ERROR: Template not found: {template_path}")

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy PDFs
    primary_pdf_name = f"book_{args.primary_lang}.pdf"
    shutil.copy2(pdf_primary, out_dir / primary_pdf_name)
    print(f"Copied: {pdf_primary} -> {out_dir / primary_pdf_name}")

    secondary_pdf_name = f"book_{args.secondary_lang}.pdf"
    if args.pdf_secondary and Path(args.pdf_secondary).is_file():
        shutil.copy2(args.pdf_secondary, out_dir / secondary_pdf_name)
        print(f"Copied: {args.pdf_secondary} -> {out_dir / secondary_pdf_name}")
    else:
        secondary_pdf_name = primary_pdf_name
        print("No secondary PDF; both buttons will load the primary PDF.")

    # Extract TOC from both PDFs at build time
    print("Extracting TOC from primary PDF...")
    toc_primary = extract_toc(str(pdf_primary))
    print(f"  Found {len(toc_primary)} chapters")

    toc_secondary = []
    if args.pdf_secondary and Path(args.pdf_secondary).is_file():
        print("Extracting TOC from secondary PDF...")
        toc_secondary = extract_toc(args.pdf_secondary)
        print(f"  Found {len(toc_secondary)} chapters")

    # Build template replacements
    pl = LANG_CONFIG[args.primary_lang]
    sl = LANG_CONFIG[args.secondary_lang]
    title_secondary = args.title_secondary or args.title

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
        "{{TOC_PRIMARY}}": json.dumps(toc_primary, ensure_ascii=False),
        "{{TOC_SECONDARY}}": json.dumps(toc_secondary, ensure_ascii=False),
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    index_path = out_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    print(f"Written: {index_path}")
    print("Build complete!")


if __name__ == "__main__":
    main()
