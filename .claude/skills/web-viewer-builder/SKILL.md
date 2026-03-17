# Web Viewer Builder Skill

## Purpose

Generate a PDF.js-based web ebook viewer from the typeset PDFs. The viewer renders the actual PDF pages with a two-page book spread layout, page-turn animation, chapter navigation sidebar, and bilingual language toggle. Deployable to GitHub Pages.

## When to Use

**Step 8** of the ebook pipeline — after PDFs have been generated in Step 7. This skill takes the finalized PDF files and produces a deployable web viewer.

## Script

`scripts/build_viewer.py`

### Usage

```bash
python3 build_viewer.py \
  --pdf-primary output/final/book_ko.pdf \
  --pdf-secondary output/final/book_en.pdf \
  --output output/web-viewer/ \
  --template .claude/skills/web-viewer-builder/references/viewer_template.html \
  --title "Book Title" \
  --title-secondary "Book Title (EN)" \
  --primary-lang ko \
  --secondary-lang en
```

### Arguments

| Argument | Required | Description |
|---|---|---|
| `--pdf-primary` | Yes | Path to primary language PDF |
| `--pdf-secondary` | No | Path to secondary language PDF (falls back to primary) |
| `--output` | Yes | Output directory for the web viewer |
| `--template` | Yes | Path to viewer_template.html |
| `--title` | Yes | Book title (primary language) |
| `--title-secondary` | No | Book title (secondary language) |
| `--primary-lang` | No | Primary language code, default `ko` |
| `--secondary-lang` | No | Secondary language code, default `en` |

## How It Works

1. **Build time**: PyMuPDF scans both PDFs for chapter headings (font size >= 14pt in top 40% of page)
2. **Build time**: Chapter-to-page mapping is extracted and embedded as JSON in the HTML
3. **Runtime**: PDF.js loads and renders the PDF pages on canvas elements
4. **Runtime**: Sidebar is populated instantly from the embedded JSON (no client-side scanning)

## Features

- **PDF.js rendering**: Actual typeset PDF rendered at full quality
- **Two-page book spread**: Left/right pages side-by-side with spine shadow and gutter effects
- **Page-turn animation**: 3D rotateY with shadow for book-like feel
- **Chapter sidebar**: Build-time extracted TOC with click-to-jump, active chapter highlighting
- **Language toggle**: Switch between primary/secondary PDF
- **Zoom controls**: Scale up/down the rendered pages
- **Keyboard navigation**: Left/Right arrow keys
- **Touch navigation**: Swipe left/right on mobile
- **Mobile responsive**: Single-page mode on small screens

## Template Placeholders

| Placeholder | Description |
|---|---|
| `{{TITLE}}` | Book title (primary) |
| `{{TITLE_SECONDARY}}` | Book title (secondary) |
| `{{PRIMARY_PDF}}` | Primary PDF filename |
| `{{SECONDARY_PDF}}` | Secondary PDF filename |
| `{{PRIMARY_LABEL}}` | Primary language button label (e.g., "한국어") |
| `{{SECONDARY_LABEL}}` | Secondary language button label (e.g., "English") |
| `{{PRIMARY_TOC_LABEL}}` | TOC header label (e.g., "목차") |
| `{{SECONDARY_TOC_LABEL}}` | TOC header label (e.g., "Contents") |
| `{{TOC_PRIMARY}}` | Chapter TOC JSON for primary language |
| `{{TOC_SECONDARY}}` | Chapter TOC JSON for secondary language |

## Dependencies

- Python 3.8+
- `pymupdf` (PyMuPDF — for build-time chapter page extraction)
- PDF.js loaded from CDN at runtime (no local install needed)
