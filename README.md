<div align="center">

# Ebook Writer Agent

**A multi-agent system that transforms a topic into a professional, print-ready ebook.**

Research &rarr; Outline &rarr; Writing &rarr; Editing &rarr; Images &rarr; Translation &rarr; PDF &rarr; Web Viewer

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet?logo=anthropic)](https://claude.ai/claude-code)
[![WeasyPrint](https://img.shields.io/badge/PDF%20Engine-WeasyPrint-blue)](https://weasyprint.org/)
[![Gemini](https://img.shields.io/badge/Images-Gemini%20API-orange?logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[**한국어 README**](README_KO.md)

</div>

---

## Live Demo

> **"Claude Code for Lawyers"** — a 13-chapter, 250+ page ebook generated entirely by this agent system.

**[Read the book online &rarr; lowtidebuild.github.io/ebook-writer](https://lowtidebuild.github.io/ebook-writer/)**

The web viewer renders the actual typeset PDF with two-page spread layout, page-turn animation, and KO/EN language toggle.

---

## What This Does

You give it a **topic** and (optionally) a **domain plugin**. It produces:

| Output | Description |
|--------|-------------|
| `book_{lang}.pdf` | Typeset PDF — B5 format, serif body, professional chapter openings, running headers |
| `book_{lang}.pdf` | Translated PDF in secondary language |
| `web-viewer/` | Browser-based book viewer with page-flip and language toggle |

The entire pipeline is automated with only **two human checkpoints**: outline approval and final review.

---

## Architecture

The system is orchestrated by `CLAUDE.md` which manages an 8-step pipeline, dispatching specialized sub-agents and executing scripts at each stage.

```
                         +-----------------+
                         |    CLAUDE.md    |
                         |  Orchestrator   |
                         +--------+--------+
                                  |
          +-----------+-----------+-----------+-----------+
          |           |           |           |           |
     +----+----+ +----+----+ +----+----+ +----+----+ +----+----+
     |Researcher| |Architect| | Writer  | | Editor  | |Translator|
     | Agent    | | Agent   | | Agent   | | Agent   | | Agent    |
     |          | |         | |  (x N)  | |         | |  (x N)  |
     +----+----+ +----+----+ +----+----+ +----+----+ +----+----+
          |           |           |           |           |
          v           v           v           v           v
     Research      Outline     Chapters    Validated   Translated
     Report         (ToC)     (per ch.)   Chapters    Chapters
                                  |
                    +-------------+-------------+
                    |             |             |
              +-----+-----+ +----+----+ +------+------+
              |   Image    | |   PDF   | | Web Viewer  |
              | Generator  | | Builder | |   Builder   |
              |  (Gemini)  | | (Weasy) | |  (PDF.js)   |
              +------------+ +---------+ +-------------+
```

### The Orchestrator: `CLAUDE.md`

The brain of the system. It manages:

- **Pipeline state** via `pipeline_state.json` &mdash; checkpoint-resume on interruption
- **Sub-agent dispatch** &mdash; spawns specialized agents as parallel Tasks
- **Dependency waves** &mdash; chapters without dependencies write in parallel; dependent chapters wait
- **Quality gates** &mdash; pauses for human approval at outline and final review
- **Retry protocol** &mdash; up to 2 retries per step, then escalation to user
- **Plugin injection** &mdash; detects domain plugins and injects config at relevant steps

### Sub-Agents

Each agent has a focused responsibility and its own `AGENT.md` instruction file:

| Agent | Role | Execution |
|-------|------|-----------|
| **Researcher** | Web search + reference material analysis &rarr; structured research report | Single task |
| **Architect** | Research report &rarr; book outline with chapter dependencies | Single task |
| **Writer** | Outline section &rarr; full chapter in target language | Parallel (per chapter) |
| **Editor** | 2-pass review: per-chapter quality + cross-chapter consistency. Detects production artifacts. | Single task |
| **Translator** | Bidirectional translation (KO&harr;EN) preserving code blocks and structure | Parallel (per chapter) |

### Skills

Reusable capabilities that agents and the orchestrator invoke:

| Skill | Purpose | Key Scripts |
|-------|---------|-------------|
| `web-research` | Search strategy, source credibility ranking, deduplication | &mdash; |
| `reference-analyzer` | Parse .md / .pdf / .docx reference files | `parse_references.py` |
| `code-example-validator` | Validate code block syntax (Python, JS, Bash) | `validate_code.py` |
| `quality-checker` | Quality rubric + domain plugin criteria application | &mdash; |
| `image-generator` | Extract `[IMAGE:]` markers &rarr; Gemini API &rarr; insert into chapters | `extract_markers.py`, `generate_images.py`, `insert_images.py` |
| `pdf-builder` | Markdown &rarr; structured HTML &rarr; WeasyPrint PDF (B5, book-grade) | `build_pdf.py` |
| `web-viewer-builder` | PDF.js-based browser viewer with two-page spread | `build_viewer.py` |

### Domain Plugins

Plugins inject domain-specific expertise without modifying the core engine:

```
.claude/plugins/legal/
  ├── PLUGIN.md              # Domain metadata, target audience, writing guidelines
  ├── research_sources.md    # Domain-specific research questions and sources
  ├── quality_criteria.md    # Terminology standards, citation format, disclaimers
  └── references/            # Source materials (.md, .pdf, .docx)
```

The included `legal` plugin configures the system for legal professionals &mdash; adding ethics guidelines, legal terminology validation, and citation format checking.

**Creating your own plugin**: Copy the `legal/` folder, rename it, and customize the three `.md` files for your domain (medical, finance, engineering, etc.).

---

## Pipeline Flow

```
Step 1  ── Research ─────────────── Researcher Agent (web search + references)
Step 2  ── Outline Design ───────── Architect Agent
        ══ Gate 1: Outline Approval   (human review)
Step 3  ── Chapter Writing ──────── Writer Agent x N (parallel, dependency waves)
Step 4  ── Editing & Validation ─── Editor Agent (2-pass + artifact detection)
Step 5  ── Image Generation ─────── Scripts (Gemini 3.1 Flash Image Preview)
Step 6  ── Translation ──────────── Translator Agent x N (parallel, bidirectional)
Step 7  ── PDF Typesetting ──────── Scripts (WeasyPrint, B5, book-grade CSS)
Step 8  ── Web Viewer ───────────── Scripts (PDF.js-based viewer)
        ══ Gate 2: Final Review       (human review)
```

**Key behaviors:**

- Gate 1 rejection &rarr; re-run outline only (research preserved)
- Gate 2 rejection &rarr; re-edit only flagged chapters (partial regeneration)
- Image generation failures are **non-blocking** (placeholder inserted, pipeline continues)
- Writer outputs max 2&ndash;3 image markers per chapter (useful diagrams only)
- Editor detects and removes production artifacts before final output

---

## PDF Typesetting

The PDF output targets **Korean book publishing standards**:

| Feature | Spec |
|---------|------|
| Page size | B5 (176 &times; 250 mm) |
| Margins | Asymmetric &mdash; inner 22mm &gt; outer 18mm (for binding) |
| Body font | Noto Serif CJK KR, 10pt, line-height 1.75 |
| Heading font | Pretendard (sans-serif contrast) |
| Code font | Fira Code, 9pt |
| Chapter openings | Recto page, 30% top space, chapter number + title + decorative rule |
| Running headers | Even pages: book title (left) &bull; Odd pages: chapter title (right) |
| Page numbers | Even: bottom-left &bull; Odd: bottom-right |
| TOC | Dot leaders with page numbers |
| Body text | Justified, `word-break: keep-all`, `text-indent: 1em` |
| Tables | Horizontal rules only (no vertical borders) |
| Special pages | Cover, title page, copyright page |

---

## Quick Start

### Prerequisites

```bash
# macOS
brew install pango cairo gdk-pixbuf
brew install --cask font-noto-serif-cjk-kr font-fira-code

# Create virtual environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Environment

```bash
# For image generation (Step 5) — optional, pipeline continues without it
echo 'GEMINI_API_KEY=your-key-here' > .env
echo 'IMAGE_MODEL=gemini-3.1-flash-image-preview' >> .env
```

### Generate

```bash
# Korean ebook with legal domain plugin
/generate "Claude Code for Lawyers" --plugin legal --author "Author Name"

# English ebook, general purpose
/generate "Introduction to Python" --language en --author "Author Name"

# Resume an interrupted pipeline
/resume
```

---

## Project Structure

```
.
├── CLAUDE.md                              # Orchestrator — pipeline state machine
│
├── .claude/
│   ├── agents/
│   │   ├── researcher/AGENT.md            # Research conductor
│   │   ├── architect/AGENT.md             # Outline designer
│   │   ├── writer/AGENT.md                # Chapter writer (parallel)
│   │   ├── editor/AGENT.md                # Quality reviewer + artifact detector
│   │   └── translator/AGENT.md            # Bidirectional KO/EN translator
│   │
│   ├── skills/
│   │   ├── web-research/                  # Web search strategies
│   │   ├── reference-analyzer/scripts/    # .md/.pdf/.docx parser
│   │   ├── code-example-validator/scripts/# Syntax validation
│   │   ├── quality-checker/               # Quality rubric
│   │   ├── image-generator/scripts/       # Gemini API image pipeline
│   │   ├── pdf-builder/scripts/           # WeasyPrint book-grade PDF
│   │   └── web-viewer-builder/scripts/    # PDF.js browser viewer
│   │
│   ├── plugins/
│   │   └── legal/                         # Legal domain plugin (example)
│   │       ├── PLUGIN.md
│   │       ├── research_sources.md
│   │       ├── quality_criteria.md
│   │       └── references/
│   │
│   └── commands/
│       ├── generate.md                    # /generate entry point
│       └── resume.md                      # /resume entry point
│
├── input/references/                      # User-provided source materials
├── output/                                # Pipeline outputs (gitignored)
├── docs/                                  # GitHub Pages deployment
└── requirements.txt
```

---

## How to Create a Domain Plugin

1. Copy `.claude/plugins/legal/` &rarr; `.claude/plugins/your-domain/`
2. Edit **`PLUGIN.md`** &mdash; domain description, target audience, writing guidelines
3. Edit **`research_sources.md`** &mdash; domain-specific research questions and sources
4. Edit **`quality_criteria.md`** &mdash; terminology standards, required disclaimers, validation rules
5. Add reference materials to **`references/`**
6. Run: `/generate "Your Topic" --plugin your-domain`

---

## License

MIT
