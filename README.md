<div align="center">

<br>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/%F0%9F%93%96_Ebook_Writer_Agent-white?style=for-the-badge&labelColor=1a1a2e&color=0f3460">
  <img alt="Ebook Writer Agent" src="https://img.shields.io/badge/%F0%9F%93%96_Ebook_Writer_Agent-white?style=for-the-badge&labelColor=1a1a2e&color=0f3460">
</picture>

### A multi-agent system that transforms a topic into a professional, print-ready ebook.

**One command. Research, write, edit, illustrate, translate, typeset, publish.**

<br>

[![Built with Claude Code](https://img.shields.io/badge/Built_with-Claude_Code-7c3aed?style=flat-square&logo=anthropic&logoColor=white)](https://claude.ai/claude-code)
[![PDF Engine](https://img.shields.io/badge/PDF-WeasyPrint-2563eb?style=flat-square)](https://weasyprint.org/)
[![Images](https://img.shields.io/badge/Images-Diagram_%2B_Gemini-f59e0b?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev/)
[![Viewer](https://img.shields.io/badge/Viewer-PDF.js-e11d48?style=flat-square)](https://mozilla.github.io/pdf.js/)
[![License](https://img.shields.io/badge/License-Apache_2.0-22c55e?style=flat-square)](LICENSE)

[**한국어**](README_KO.md) ·
[**Quick Start**](#-quick-start)

<br>

</div>

---

## ✨ What This Does

```
You say:    /generate "Claude Code for Lawyers" --plugin legal --author "Author"

You get:    📄 book.pdf       (250+ page typeset book in your input language)
            🌐 web-viewer/    (browser-based reader with page-flip)
            📄 book_xx.pdf    (translated version — only if you want it)
```

Language is **auto-detected** from your input (Korean input → Korean book, English input → English book). Translation is **optional** — the system asks if you need it.

The pipeline runs automatically with only **two human checkpoints**:

| Gate | When | What Happens |
|:----:|------|-------------|
| **Gate 1** | After outline | Review chapter structure. Approve or request changes. |
| **Gate 2** | After final build | Review PDF + web viewer. Approve or flag specific chapters. |

<br>

---

<br>

## 🛡 Implemented Quality Controls

Implemented checks that reduce hallucinations, visible artifacts, and broken final outputs:

| Feature | How It Works |
|---------|-------------|
| **Cross-Verification** | Researcher validates key claims (stats, dates, legal refs) against 2+ independent sources. Confidence scores in `verification_report.json`. |
| **Citation Tracking** | `citations.json` master DB flows through Writer (`[^N]` footnotes) &rarr; Editor (validation) &rarr; Translator (preservation) &rarr; PDF (bibliography). |
| **Code Execution** | `:runnable` blocks run in Docker isolation when available. Local process execution requires explicit `--allow-unsafe-process`; obvious network usage is blocked before execution. |
| **Reference Validation** | `validate_references.py` catches broken chapter cross-references and can validate inline citation IDs against `citations.json`. |
| **Image Pipeline** | Text-heavy diagrams use deterministic local SVG rendering by default; illustrative images can use Gemini; OpenAI/Codex are explicit overrides. |
| **Final Preflight** | Final validators block unresolved image entries, visible placeholders, malformed PDFs, and broken viewer output before Gate 2. |

<br>

---

<br>

## 🏗 Architecture

```mermaid
graph TD
    O["🧠 CLAUDE.md<br/>Orchestrator"]

    O --> R["🔍 Researcher<br/>Agent"]
    O --> A["📐 Architect<br/>Agent"]
    O --> W["✍️ Writer<br/>Agent ×N"]
    O --> Ed["🔎 Editor<br/>Agent"]
    O --> Tr["🌐 Translator<br/>Agent ×N"]

    R --> RR["Research Report"]
    A --> ToC["Outline (ToC)"]
    W --> Ch["Chapters<br/>(parallel)"]
    Ed --> VC["Validated<br/>Chapters"]
    Tr --> TC["Translated<br/>Chapters"]

    Ch --> IG["🎨 Image Generator<br/>(Diagram + Gemini)"]
    Ch --> PB["📕 PDF Builder<br/>(WeasyPrint)"]
    Ch --> WV["💻 Web Viewer<br/>(PDF.js)"]

    style O fill:#1a1a2e,color:#fff,stroke:#0f3460
    style R fill:#2563eb,color:#fff
    style A fill:#2563eb,color:#fff
    style W fill:#7c3aed,color:#fff
    style Ed fill:#2563eb,color:#fff
    style Tr fill:#7c3aed,color:#fff
    style IG fill:#f59e0b,color:#000
    style PB fill:#e11d48,color:#fff
    style WV fill:#e11d48,color:#fff
```

<br>

### 🧠 Orchestrator — `CLAUDE.md`

The brain of the system:

| Capability | Description |
|:----------:|-------------|
| **State Machine** | `pipeline_state.json` — checkpoint & resume on interruption |
| **Parallel Dispatch** | Writers & translators run as concurrent Tasks per chapter |
| **Dependency Waves** | Independent chapters write in parallel; dependent chapters wait |
| **Quality Gates** | Pauses for human approval at outline and final review |
| **Auto-Retry** | Up to 2 retries per step, then escalation |
| **Plugin Injection** | Detects domain plugins, injects config at relevant steps |

<br>

### 🤖 Sub-Agents (5)

Each agent has a focused role and its own `AGENT.md` instruction file:

| | Agent | What It Does | Execution |
|:--:|-------|-------------|:---------:|
| 🔍 | **Researcher** | Web search + reference analysis + **cross-verification** &rarr; structured report + citations DB | Single |
| 📐 | **Architect** | Research &rarr; outline with chapter dependencies | Single |
| ✍️ | **Writer** | Outline section &rarr; full chapter with **inline citations** + `:runnable` code tags | **Parallel** |
| 🔎 | **Editor** | 2-pass review + **automated reference/code validation** + artifact detection | Single |
| 🌐 | **Translator** | Bidirectional KO&harr;EN, preserving code, structure & **footnotes** | **Parallel** |

<br>

### ⚡ Skills (7)

Reusable capabilities invoked by agents and the orchestrator:

| | Skill | Purpose | Scripts |
|:--:|-------|---------|:-------:|
| 🌍 | `web-research` | Search strategy, source credibility ranking | — |
| 📄 | `reference-analyzer` | Parse .md / .pdf / .docx files | `parse_references.py` |
| ✅ | `code-example-validator` | Syntax validation + **`:runnable` execution** + **cross-reference checking** | `validate_code.py` `validate_references.py` |
| 📋 | `quality-checker` | Quality rubric + domain criteria | — |
| 🎨 | `image-generator` | `[IMAGE:]` &rarr; **auto-classify** &rarr; **template prompts** &rarr; **type-routed providers** (diagram/Gemini/OpenAI/Codex) &rarr; **final validation** | 4 scripts + 6 templates |
| 📕 | `pdf-builder` | Markdown &rarr; HTML &rarr; WeasyPrint (B5) + **footnotes** + **bibliography** | `build_pdf.py` |
| 💻 | `web-viewer-builder` | PDF.js viewer with sidebar (PyMuPDF TOC extraction) | `build_viewer.py` |

<br>

---

<br>

## 🔄 Pipeline

```mermaid
flowchart LR
    S1["🔍 Research<br/>+ Verify"] --> S2["📐 Outline"]
    S2 --> G1{{"⏸ Gate 1"}}
    G1 -->|Approve| S3["✍️ Write ×N<br/>+ Citations"]
    G1 -.->|Revise| S2
    S3 --> S4["🔎 Edit<br/>+ Validate"]
    S4 --> S5["🎨 Images<br/>+ QA"]
    S5 --> S6["🌐 Translate ×N"]
    S6 --> S7["📕 PDF"]
    S7 --> S8["💻 Viewer"]
    S8 --> G2{{"⏸ Gate 2"}}
    G2 -->|Approve| Done["✅ Done"]
    G2 -.->|Revise| S4

    style G1 fill:#f59e0b,color:#000,stroke:#f59e0b
    style G2 fill:#f59e0b,color:#000,stroke:#f59e0b
    style Done fill:#22c55e,color:#fff
    style S6 stroke-dasharray:5 5
```

> **Step 6 (Translate) is optional** — only runs if you request bilingual output
>
> **Gate 1 rejected?** &rarr; Re-run outline only (research preserved)
>
> **Gate 2 rejected?** &rarr; Re-edit only flagged chapters (partial regen)
>
> **Image failed?** &rarr; Neutral caption inserted, but final validation still blocks unresolved image entries

<br>

---

<br>

## 📕 PDF Typesetting

The output targets **Korean book publishing standards**:

<table>
<tr><td width="200"><b>Page size</b></td><td>B5 (176 × 250 mm)</td></tr>
<tr><td><b>Margins</b></td><td>Asymmetric — inner 22mm > outer 18mm (binding)</td></tr>
<tr><td><b>Body font</b></td><td>Noto Serif CJK KR · 10pt · line-height 1.75</td></tr>
<tr><td><b>Heading font</b></td><td>Pretendard (sans-serif contrast)</td></tr>
<tr><td><b>Code font</b></td><td>Fira Code · 9pt</td></tr>
<tr><td><b>Chapter openings</b></td><td>Recto page · 30% top space · number + title + rule</td></tr>
<tr><td><b>Running headers</b></td><td>Even: book title (left) · Odd: chapter title (right)</td></tr>
<tr><td><b>Page numbers</b></td><td>Even: bottom-left · Odd: bottom-right</td></tr>
<tr><td><b>TOC</b></td><td>Dot leaders with page numbers</td></tr>
<tr><td><b>Body text</b></td><td>Justified · <code>word-break: keep-all</code> · indent 1em</td></tr>
<tr><td><b>Tables</b></td><td>Horizontal rules only (no vertical borders)</td></tr>
<tr><td><b>Special pages</b></td><td>Cover · title page · copyright page</td></tr>
</table>

<br>

---

<br>

## 🔌 Domain Plugins

Plugins inject **domain-specific expertise** without modifying the core engine:

```
.claude/plugins/legal/
  ├── PLUGIN.md              ← target audience, writing guidelines
  ├── research_sources.md    ← domain-specific research questions
  ├── quality_criteria.md    ← terminology, citation format, disclaimers
  └── references/            ← source materials (.md, .pdf, .docx)
```

The included **`legal`** plugin adds ethics guidelines, legal terminology validation, and citation format checking.

> **Make your own:** Copy `legal/` &rarr; rename &rarr; edit the 3 `.md` files for your domain (medical, finance, engineering, etc.)

<br>

---

<br>

## 🚀 Quick Start

### 1. Clone & setup

```bash
git clone https://github.com/lowtidebuild/ebook-writer.git
cd ebook-writer
./setup.sh
```

> The setup script automatically installs system libraries, fonts, Python venv, and creates a `.env` template.
>
> <details><summary>Manual installation</summary>
>
> ```bash
> # macOS
> brew install pango cairo gdk-pixbuf
> brew install --cask font-noto-serif-cjk-kr font-noto-sans-cjk-kr font-fira-code
>
> # Python
> python3 -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt
> ```
> </details>

### 2. Set up image generation (optional)

The image-generator routes each image to a provider based on its type:

- **`diagram`** — default for text-heavy diagrams (architecture / process flow / comparison table). Deterministic local SVG, no API key.
- **`gemini`** — default for illustrative images (concept diagrams, metaphors).
- **`openai`** — paid Images API (`gpt-image-*`), explicit override only.
- **`codex`** — optional [god-tibo-imagen](https://github.com/NomaDamas/god-tibo-imagen) path through local Codex CLI auth. Unsupported backend; explicit override only.

```bash
# Edit .env (created by setup.sh)
GEMINI_API_KEY=your-key-here       # required if any image uses provider=gemini
OPENAI_API_KEY=your-key-here       # required only for the openai override path
# CODEX_IMAGE_MODEL=gpt-5.4        # optional; codex override only
# IMAGE_PROVIDER=diagram|gemini|openai|codex  # optional global override
```

The default path does not require Codex image credentials. The optional `codex` provider requires `codex login` on an account with image generation entitlement.

### 3. Generate

```bash
# Korean book with legal plugin
/generate "Claude Code for Lawyers" --plugin legal --author "Author Name"

# English book, general purpose
/generate "Introduction to Python" --language en --author "Author Name"

# Resume interrupted pipeline
/resume
```

<br>

---

<br>

## 📁 Project Structure

```
.
├── CLAUDE.md                               ← Orchestrator (pipeline state machine)
│
├── .claude/
│   ├── agents/
│   │   ├── researcher/AGENT.md             ← Research conductor
│   │   ├── architect/AGENT.md              ← Outline designer
│   │   ├── writer/AGENT.md                 ← Chapter writer (parallel)
│   │   ├── editor/AGENT.md                 ← Quality reviewer + artifact detector
│   │   └── translator/AGENT.md             ← Bidirectional KO↔EN translator
│   │
│   ├── skills/
│   │   ├── web-research/                   ← Search strategies
│   │   ├── reference-analyzer/             ← .md/.pdf/.docx parser
│   │   ├── code-example-validator/         ← Syntax validation
│   │   ├── quality-checker/                ← Quality rubric
│   │   ├── image-generator/                ← Diagram/Gemini/OpenAI/Codex pipeline
│   │   ├── pdf-builder/                    ← WeasyPrint book-grade PDF
│   │   └── web-viewer-builder/             ← PDF.js browser viewer
│   │
│   ├── plugins/
│   │   └── legal/                          ← Legal domain plugin (example)
│   │
│   └── commands/
│       ├── generate.md                     ← /generate entry point
│       └── resume.md                       ← /resume entry point
│
├── input/references/                       ← User-provided source materials
├── output/                                 ← Pipeline outputs (gitignored)
├── docs/                                   ← GitHub Pages (live demo)
└── requirements.txt
```

<br>

---

<br>

<div align="center">

**Built with [Claude Code](https://claude.ai/claude-code)**

Apache License 2.0

</div>
