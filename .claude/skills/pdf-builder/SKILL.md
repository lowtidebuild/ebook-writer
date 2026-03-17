# PDF Builder Skill

## Purpose

Convert markdown chapters into a professionally typeset PDF book using WeasyPrint. This skill takes the authored chapter files (Markdown) and produces a print-ready PDF complete with cover page, table of contents, page numbers, headers/footers, syntax-highlighted code blocks, and properly placed images.

## Script

`scripts/build_pdf.py`

## Features

- **Cover page** -- Rendered from an HTML template with title, subtitle, author, and date placeholders.
- **Table of contents** -- Auto-generated from chapter headings (H1 and H2) with page references.
- **Page numbers** -- Centered in the footer on every page except the cover.
- **Headers and footers** -- Configurable via CSS `@page` rules; suppressed on the cover page.
- **Code highlighting** -- Fenced code blocks are syntax-highlighted using Pygments (friendly theme).
- **Image placement** -- Images are resolved to absolute paths so WeasyPrint can locate them, centered with constrained width.
- **Multilingual support** -- `--language` flag switches between Korean (`ko`) and English (`en`) typographic defaults.

## Dependencies

| Package              | Purpose                                  |
|----------------------|------------------------------------------|
| `weasyprint`         | HTML/CSS to PDF rendering engine         |
| `markdown`           | Markdown to HTML conversion              |
| `pymdown-extensions` | Extended Markdown syntax (superfences)   |
| `Pygments`           | Syntax highlighting for code blocks      |

Install all at once:

```bash
pip install weasyprint markdown pymdown-extensions Pygments
```

## Reference Files

| File                                    | Description                        |
|-----------------------------------------|------------------------------------|
| `references/book_styles.css`            | Professional book layout CSS       |
| `references/cover_template.html`        | HTML template for the cover page   |

## Usage

```bash
python3 scripts/build_pdf.py \
  --chapters output/chapters/ko/ \
  --images output/images/ \
  --output output/final/book_ko.pdf \
  --language ko \
  --styles .claude/skills/pdf-builder/references/book_styles.css \
  --cover .claude/skills/pdf-builder/references/cover_template.html \
  --title "Book Title"
```

### Arguments

| Argument      | Required | Description                                      |
|---------------|----------|--------------------------------------------------|
| `--chapters`  | Yes      | Directory containing `ch{NN}_*.md` chapter files  |
| `--images`    | No       | Directory containing images referenced in chapters|
| `--output`    | Yes      | Output PDF file path                              |
| `--language`  | No       | Language code (`ko` or `en`), default `ko`        |
| `--styles`    | No       | Path to CSS stylesheet                            |
| `--cover`     | No       | Path to cover page HTML template                  |
| `--title`     | Yes      | Book title injected into cover and metadata       |
| `--subtitle`  | No       | Book subtitle for the cover page                  |
| `--author`    | No       | Author name for the cover page                    |

## When to Use

**Step 7 of the ebook generation pipeline.** Run this skill after all chapters have been written, reviewed, and finalized, and after images have been generated. The input is the complete set of markdown chapter files; the output is the final PDF book.
