# Web Viewer Builder Skill

## Purpose

Generate a single-page HTML ebook viewer from markdown chapters. The viewer provides a polished, book-like reading experience with page-flip animation, bilingual support (Korean/English), and full mobile responsiveness. The output is a self-contained static site deployable to GitHub Pages with zero external dependencies.

## When to Use

**Step 8** of the ebook pipeline — after chapters have been written in both languages and images have been generated. This skill takes the finalized chapter markdown files and produces a deployable web viewer.

## Script

`scripts/build_viewer.py`

### Usage

```bash
python3 build_viewer.py \
  --chapters-ko output/chapters/ko/ \
  --chapters-en output/chapters/en/ \
  --images output/images/ \
  --output output/web-viewer/ \
  --template .claude/skills/web-viewer-builder/references/viewer_template.html \
  --title "Book Title"
```

### Arguments

| Argument | Required | Description |
|---|---|---|
| `--chapters-ko` | Yes | Directory containing Korean chapter `.md` files |
| `--chapters-en` | Yes | Directory containing English chapter `.md` files |
| `--images` | Yes | Directory containing book images |
| `--output` | Yes | Output directory for the generated web viewer |
| `--template` | Yes | Path to the HTML template file |
| `--title` | Yes | Book title displayed in the viewer |

## Features

- **Page-flip animation**: Smooth CSS translateX transitions (300ms ease-in-out) for natural page turning
- **KO/EN language toggle**: Switch between Korean and English content while maintaining page position; preference saved in localStorage
- **Table of contents sidebar**: Collapsible chapter list with click-to-jump navigation
- **Keyboard navigation**: Left/Right arrow keys for page turning
- **Touch navigation**: Swipe left/right on mobile devices; tap page edges to navigate
- **Mobile responsive**: Stacked layout with touch-friendly buttons on small screens
- **Zero external dependencies**: Vanilla HTML, CSS, and JavaScript only
- **GitHub Pages deployable**: Static output directory ready for deployment

## Template

The viewer template is located at `references/viewer_template.html`. It is a fully self-contained single-page application with inline CSS and JS. The build script injects content into the following placeholders:

- `{{TITLE}}` — Book title
- `{{TOC_ITEMS}}` — Generated table of contents HTML
- `{{PAGES}}` — All page `<div>` elements with chapter content
- `{{TOTAL_PAGES_KO}}` — Total number of Korean pages
- `{{TOTAL_PAGES_EN}}` — Total number of English pages

## Dependencies

- Python 3.8+
- `markdown` (Python library for converting `.md` to HTML)

No frontend dependencies. The output HTML is entirely self-contained.
