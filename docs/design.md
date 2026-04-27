# Ebook Generation Agent System — Design Document

## 1. Overview

### 1.1 Purpose

An automated ebook generation agent system that takes a topic as input and produces finished deliverables (typeset PDF book + web viewer) through a fully automated pipeline: research → outline → chapter writing → editing/validation → image generation → PDF typesetting → web viewer. A general-purpose engine handles the entire book creation pipeline, while domain plugins inject domain-specific expertise (e.g., legal, technical) at designated intervention points. The first application is "Claude Code for Lawyers."

### 1.2 Scope

- **In scope**: Research, outline design, chapter writing, editing/validation, image generation, PDF typesetting, web viewer generation, Korean→English translation pipeline, domain plugin architecture (including legal plugin)
- **Out of scope**: Ebook distribution platform integration (ePub/Kindle), print-ready typesetting (CMYK, bleed marks), real-time collaborative editing, reader feedback collection

### 1.3 Input/Output Definition

| Type | Format | Source/Destination | Notes |
|------|--------|-------------------|-------|
| Input — Topic | Natural language text | User CLI input | e.g., "Claude Code for Lawyers" |
| Input — Domain plugin | Plugin directory | `/.claude/plugins/{domain}/` | Optional and explicit (`--plugin <domain>`). Without it, runs in general-purpose mode |
| Input — Reference materials | .md, .txt, .pdf, .docx | `/input/references/` | User or plugin-provided source materials; chunked before agent use |
| Output — Markdown manuscripts | .md (per chapter) | `/output/chapters/ko/`, `/output/chapters/en/` | Korean original + English translation |
| Output — Images | .png/.svg | `/output/images/` | Infographics, diagrams per chapter |
| Output — PDF | .pdf | `/output/final/book_ko.pdf`, `book_en.pdf` | Typeset final book |
| Output — Web viewer | HTML/CSS/JS | `/output/web-viewer/` | For GitHub Pages deployment |

### 1.4 Constraints

- **Quality first with bounded context**: Each step must validate outputs thoroughly, while large references and cross-step context are summarized or chunked before agent use
- **Minimal human intervention**: Only two gates — outline approval + final review
- **Image generation provider dependency**: Text-heavy diagrams are rendered locally as SVG by default. Gemini/OpenAI/Codex are optional external providers and subject to their own availability/rate limits; Codex is an unsupported override path
- **Claude Code environment**: Agent operates on Claude Code's Task tool (sub-agents), file system, and web search

### 1.5 Terminology

| Term | Definition |
|------|-----------|
| **General-purpose engine** | Core system that executes the "topic → book" pipeline regardless of domain |
| **Domain plugin** | Extension module that injects domain-specific research sources, quality criteria, and reference materials into the engine |
| **Gate** | Pipeline pause point that waits for human approval |
| **Reference materials** | Existing documents specified by a plugin, used as source material during chapter writing |

---

## 2. Workflow

### 2.1 Overall Flow

```
[Input: Topic + Domain Plugin (optional)]
        │
        ▼
   Step 1. Research
        │
        ▼
   Step 2. Outline Design
        │
        ▼
   ══ Gate 1: Outline Approval ══
        │
        ▼
   Step 3. Chapter Writing (parallel)
        │
        ▼
   Step 4. Editing/Validation
        │
        ▼
   Step 5. Image Generation
        │
        ▼
   Step 6. Translation (KO→EN)
        │
        ▼
   Step 7. PDF Typesetting
        │
        ▼
   Step 8. Web Viewer Generation
        │
        ▼
   ══ Gate 2: Final Review ══
        │
        ▼
   [Deliverables: PDF + Web Viewer (KO/EN)]
```

### 2.2 Branching and State Transitions

- **Domain plugin presence branching**: In Step 1 (Research) and Step 4 (Editing/Validation), if a plugin exists, apply the plugin's sources/quality criteria; otherwise use general-purpose defaults. Not a separate path — plugin settings are injected into the same pipeline.
- **Gate 1 rejection**: Re-execute Step 2 (Outline Design) incorporating user feedback. Research results are preserved.
- **Gate 2 rejection**: Re-execute from Step 4 (Editing/Validation) only for the chapters/sections flagged by the user. Not a full regeneration — partial correction only.
- **Editing/validation failure loop**: If quality criteria are not met in Step 4, rewrite the failing chapter up to 2 times. If still failing after 2 attempts, log the reason and let the human decide at Gate 2.

### 2.3 Step Details

#### Step 1: Research

- **Executor**: LLM (web search + bounded reference chunk analysis)
- **Input**: Topic (natural language), plugin research source list (if explicitly selected), reference chunk manifest from `/output/research/reference_chunks/`
- **Processing**:
  1. Decompose topic into granular research questions (e.g., "What is Claude Code?", "Current state of AI in legal practice", "How to install Claude Code")
  2. Collect latest information via web search
  3. If plugin exists, collect additional information from plugin-specified sources (e.g., legal plugin → legislation/case law)
  4. If reference materials exist, select relevant chunks from the manifest instead of loading full files
  5. Structure collected information into a research report, citations DB, verification report, and claim ledger
  6. Build `source_cache.json` and `research_summary_for_outline.md`
- **Output**: `/output/research/research_report.md`, `verification_report.json`, `citations.json`, `claim_ledger.json`, `source_cache.json`, `research_summary_for_outline.md`
- **Success criteria**: Minimum research question count met; key factual claims have valid source IDs; claim ledger validates against citations
- **Validation method**: Script + LLM self-check — `validate_claims.py ledger` plus research coverage review
- **On failure**: Generate additional research questions for information-sparse areas and re-collect (max 2 retries)

#### Step 2: Outline Design

- **Executor**: LLM
- **Input**: `/output/research/research_summary_for_outline.md`, full research report as fallback, plugin quality criteria (if present)
- **Processing**:
  1. Design part/chapter/section structure based on research report
  2. Specify per-chapter summary (2–3 sentences), key content to cover, estimated length
  3. Emit structured `outline.json` with stable chapter IDs, slugs, key content, word estimates, and dependency IDs
  4. Render `table_of_contents.md` from the JSON source of truth
- **Output**: `/output/outline/outline.json`, `/output/outline/table_of_contents.md`
- **Success criteria**: All major topics from the research summary are placed; dependency graph is valid; JSON and Markdown match
- **Validation method**: Script — `validate_outline.py` checks required fields, duplicate IDs/slugs, bad dependencies, cycles, and rendered Markdown consistency
- **On failure**: Supplement missing topics and regenerate (max 2 retries)

**═══ Gate 1: Outline Approval ═══**
- Present outline to user
- If approved, proceed to Step 3
- If revision requested, re-execute Step 2 with feedback (research results preserved)

#### Step 3: Chapter Writing (parallel)

- **Executor**: LLM (parallel Tasks per chapter)
- **Input**: `/output/outline/outline.json`, chapter pack JSON, dependency summaries, plugin path if explicitly selected
- **Processing**:
  1. Chapters with no dependencies start writing in parallel
  2. Chapters with dependencies execute sequentially after their prerequisite completes
  3. Each chapter is written from its outline object and chapter evidence pack
  4. Include only pack-allowed factual claims and source IDs
  5. Include runnable code examples only when self-contained and expected output is specified
  6. Mark image-needed locations with `[IMAGE: description]` markers sparingly
- **Output**: `/output/chapters/ko/ch{NN}_{slug}.md` (per-chapter markdown)
- **Success criteria**: All key content specified in outline is covered; claim usage stays within the chapter pack; code examples are syntactically valid and runnable examples pass execution checks
- **Validation method**: Script — `validate_claims.py chapter`, code-example validator, chapter structure validator
- **On failure**: Rewrite the failing chapter (max 2 retries)

#### Step 4: Editing/Validation

- **Executor**: LLM
- **Input**: Chapter directory, outline JSON/Markdown, chapter packs, dependency summaries, citations DB, claim validation results, cross-reference results, code execution results, plugin quality criteria if explicitly selected
- **Processing**:
  1. Per-chapter quality review: content accuracy, clarity of explanation, reader-level appropriateness
  2. Apply domain plugin quality criteria (e.g., legal terminology accuracy, citation format)
  3. Cross-chapter consistency review: terminology unification, cross-reference integrity, tone consistency
  4. Remove visible production artifacts (`[IMAGE:]`, failed image markers, TODO/TBD, generator credit)
  5. Directly fix issues by overwriting chapter files
  6. Generate edit report (change log, remaining issues)
- **Output**: Revised `/output/chapters/ko/ch{NN}_{slug}.md` files + `/output/edit/edit_report.md`
- **Success criteria**: Edit report states "no blocking issues"
- **Validation method**: Script + LLM self-check — automated validators first, then editor review focused on blocking issues
- **On failure**: Return chapters with blocking issues to Step 3 for rewrite (max 2 retries). After 2 retries, log the issue and let the human decide at Gate 2

#### Step 5: Image Generation

- **Executor**: Script pipeline (marker extraction, prompt templating, provider dispatch, validation)
- **Input**: `[IMAGE: description]` markers from edited chapters
- **Processing**:
  1. Script extracts all `[IMAGE: ...]` markers from all chapters into a list
  2. Classify image type and apply prompt templates
  3. Route text-heavy diagrams to local SVG `diagram` provider by default; use Gemini/OpenAI/Codex only when configured
  4. Insert completed images using manifest `output_path`; failed entries receive neutral caption fallback text
  5. Validate the manifest and chapter replacements
- **Output**: `/output/images/*.{svg,png}` + chapters with images or neutral captions inserted
- **Success criteria**: No raw `[IMAGE: ...]` markers remain; completed image files exist; unresolved failed/pending entries are surfaced before final review
- **Validation method**: Script — `validate_images.py`, `validate_chapters.py`, and final preflight
- **On failure**: Continue the pipeline with neutral captions, but keep unresolved manifest entries blocking unless explicitly approved

#### Step 6: Translation (KO→EN)

- **Executor**: LLM (parallel Tasks per chapter)
- **Input**: Image-inserted `/output/chapters/ko/` (all chapters)
- **Processing**:
  1. Translate chapters in parallel
  2. Technical terms: keep original or use standard English equivalents
  3. Code examples: do not translate (translate comments only)
  4. Image paths: shared (same images used)
- **Output**: `/output/chapters/en/ch{NN}_{slug}.md`
- **Success criteria**: 1:1 structural correspondence with Korean original; code blocks preserved; image references maintained
- **Validation method**: Script — KO/EN chapter count, heading structure, code block count, image reference count, and footnote marker preservation. LLM self-check — quality review of 1–2 sample chapters
- **On failure**: Re-translate structurally mismatched chapters (max 2 retries)

#### Step 7: PDF Typesetting

- **Executor**: Script
- **Input**: `/output/chapters/ko/`, `/output/chapters/en/`, `/output/images/`
- **Processing**:
  1. Markdown → PDF conversion (fonts: Pretendard for Korean, default sans-serif for English)
  2. Cover page generation
  3. Auto-generate table of contents page
  4. Insert page numbers, headers/footers
  5. Image placement and sizing
- **Output**: `/output/final/book_ko.pdf`, `/output/final/book_en.pdf`
- **Success criteria**: PDF files generated, page count > 0, all images rendered
- **Validation method**: Script — PDF file existence, page count check, file size threshold
- **On failure**: Output error log and escalate (typesetting failures are hard to auto-recover)

#### Step 8: Web Viewer Generation

- **Executor**: Script
- **Input**: primary PDF, optional secondary PDF, viewer template
- **Processing**:
  1. Build a PDF.js HTML viewer from the finalized PDF files
  2. Extract chapter TOC data from PDFs at build time
  3. Include language toggle only when a secondary PDF exists
  4. Support mobile touch + desktop keyboard navigation
  5. Output as GitHub Pages-deployable static files
- **Output**: `/output/web-viewer/` (index.html + assets)
- **Success criteria**: index.html renders correctly locally; chapter navigation works; KO/EN toggle works
- **Validation method**: Script — `validate_web_viewer.py` checks template placeholders, PDF references, PDF.js presence, and single-language toggle behavior
- **On failure**: Output error log and escalate

**═══ Gate 2: Final Review ═══**
- Present PDF and web viewer to user
- If approved, pipeline complete
- If revision requested, re-execute from Step 4 (Editing/Validation) for flagged chapters/sections only (not full regeneration)

---

## 3. Agent Architecture

### 3.1 Architecture Choice: Multi-Agent

**Rationale:** Single agent is the default, but this system meets the criteria for sub-agent introduction.

1. **Context window optimization**: Loading research guidelines, writing style guides, editing checklists, and typesetting script guides all at once for every step is inefficient. Each step's specialized instructions load only in its sub-agent.
2. **Parallel execution**: Step 3 (chapter writing) and Step 6 (translation) require per-chapter parallel Tasks. The main agent spawns Tasks.
3. **Domain isolation**: General-purpose engine logic and domain plugin logic must be cleanly separated for reusability.

### 3.2 Agent Topology

```
CLAUDE.md (Main Orchestrator)
    │
    ├── [Task] Researcher Agent
    │
    ├── [Task] Architect Agent
    │
    ├── [Task × N] Writer Agent (parallel per chapter)
    │
    ├── [Task] Editor Agent
    │
    ├── [Task × N] Translator Agent (parallel per chapter)
    │
    └── (Direct script execution: image generation, PDF typesetting, web viewer)
```

**Main Agent (CLAUDE.md)**
- Role: Pipeline orchestrator
- Responsibilities:
  - Pipeline state management (`/output/pipeline_state.json`)
  - Spawn each sub-agent as a Task and receive results
  - Present deliverables at gates and wait for user approval
  - Detect domain plugin presence and inject configuration
  - Directly execute script steps (image generation, PDF typesetting, web viewer)
  - Decide retry/escalation on failure

**Sub-agent: Researcher**
- File: `/.claude/agents/researcher/AGENT.md`
- Role: Conduct comprehensive research on the topic and produce a structured report
- Trigger: Main spawns as Task in Step 1
- Input: Topic, plugin research source list, reference material paths
- Output: `/output/research/research_report.md`
- Skills used: `web-research`, `reference-analyzer`

**Sub-agent: Architect**
- File: `/.claude/agents/architect/AGENT.md`
- Role: Design book outline structure based on research results
- Trigger: Main spawns as Task in Step 2
- Input: `/output/research/research_report.md`, plugin quality criteria
- Output: `/output/outline/table_of_contents.md`
- Skills used: None (pure LLM judgment task)

**Sub-agent: Writer**
- File: `/.claude/agents/writer/AGENT.md`
- Role: Write a single chapter
- Trigger: Main spawns per-chapter Tasks in Step 3 (parallel)
- Input: Assigned chapter's outline section, research report, chapter-specific reference materials, preceding chapter manuscripts (if dependency)
- Output: `/output/chapters/ko/ch{NN}_{slug}.md`
- Skills used: `code-example-validator`

**Sub-agent: Editor**
- File: `/.claude/agents/editor/AGENT.md`
- Role: Quality validation and editing of the full manuscript
- Trigger: Main spawns as Task in Step 4
- Input: All chapters in `/output/chapters/ko/`, outline, plugin quality criteria
- Output: Revised chapter files + `/output/edit/edit_report.md`
- Skills used: `quality-checker`

**Sub-agent: Translator**
- File: `/.claude/agents/translator/AGENT.md`
- Role: Translate a single chapter KO→EN
- Trigger: Main spawns per-chapter Tasks in Step 6 (parallel)
- Input: Single Korean chapter markdown
- Output: `/output/chapters/en/ch{NN}_{slug}.md`
- Skills used: None (pure LLM translation task)

**Script Steps (executed directly by Main Agent)**
- Image marker extraction, image generation API calls, PDF typesetting, and web viewer generation are handled by scripts within skills — not sub-agents. LLM involvement is limited to writing image prompts and generating web viewer code.

### 3.3 Skill Inventory

| Attribute | `web-research` | `reference-analyzer` | `code-example-validator` | `quality-checker` | `image-generator` | `pdf-builder` | `web-viewer-builder` |
|-----------|---|---|---|---|---|---|---|
| **Path** | `/.claude/skills/web-research/` | `/.claude/skills/reference-analyzer/` | `/.claude/skills/code-example-validator/` | `/.claude/skills/quality-checker/` | `/.claude/skills/image-generator/` | `/.claude/skills/pdf-builder/` | `/.claude/skills/web-viewer-builder/` |
| **Role** | Collect and structure information by topic via web search | Read reference .md/.pdf files and extract key content | Validate syntax of code examples in chapters | Validate manuscript against domain plugin criteria + general criteria | Extract image markers → generate prompts → call API → insert images | Convert markdown → PDF (cover, TOC, fonts, page numbers) | Generate page-flip web viewer from markdown |
| **Trigger** | Researcher processes research questions | Researcher analyzes reference materials | Writer completes a chapter containing code examples | Editor performs editing/validation | Main executes in Step 5 | Main executes in Step 7 | Main executes in Step 8 |
| **Scripts** | None (uses LLM web search tool) | File reading/parsing scripts | Language-specific linter execution scripts | None (LLM judgment task) | Marker extraction, API call, marker replacement scripts | Markdown→PDF conversion script (WeasyPrint etc.) | HTML/CSS/JS templates, markdown→HTML conversion script |
| **References** | None | None | None | Domain plugin quality criteria file | Image generation API guide | Typesetting style config file | Viewer design spec |
| **Used by** | Researcher | Researcher | Writer | Editor | Main | Main | Main |

### 3.4 Domain Plugin Structure

Plugins reside in `/.claude/plugins/{domain}/` with the following files:

| File | Role | Used at |
|------|------|---------|
| `PLUGIN.md` | Plugin metadata (domain name, description) | Read by Main agent on load |
| `research_sources.md` | Domain-specific source list and search strategies for research | Step 1 → Researcher |
| `quality_criteria.md` | Domain-specific quality criteria (terminology accuracy, citation format, prohibited expressions, etc.) | Step 4 → Editor (via quality-checker skill) |
| `/references/` | Source material files (.md, .pdf, etc.) | Step 1 → Researcher, Step 3 → Writer |

**Legal Plugin Example** (`/.claude/plugins/legal/`):
- `research_sources.md`: How to access legislation DBs, case law search strategies, legal news sources
- `quality_criteria.md`: Legal terminology standards, statute citation format, disclaimer requirements
- `/references/`: Contract review agent design doc, legal research agent design doc, legal writing agent design doc, etc.

### 3.5 Data Flow

| Segment | Method | Format | Path |
|---------|--------|--------|------|
| Main → Researcher | Inline at Task spawn | Topic text + plugin paths | — |
| Researcher → Main | File-based | Markdown | `/output/research/research_report.md` |
| Main → Architect | File path passed at Task spawn | Path reference | — |
| Architect → Main | File-based | Markdown | `/output/outline/table_of_contents.md` |
| Main → Writer (×N) | Inline at Task spawn | Chapter number + outline section + file paths | — |
| Writer → Main | File-based | Markdown | `/output/chapters/ko/ch{NN}_{slug}.md` |
| Main → Editor | File path passed at Task spawn | Path reference | — |
| Editor → Main | File-based | Markdown | Revised chapters + `/output/edit/edit_report.md` |
| Main → Translator (×N) | File path passed at Task spawn | Path reference | — |
| Translator → Main | File-based | Markdown | `/output/chapters/en/ch{NN}_{slug}.md` |
| Inter-step state | File-based | JSON | `/output/pipeline_state.json` |

---

## 4. Folder Structure

```
/project-root
├── CLAUDE.md                          # Main orchestrator instructions
├── /.claude/
│   ├── /agents/
│   │   ├── /researcher/
│   │   │   └── AGENT.md               # Research agent instructions
│   │   ├── /architect/
│   │   │   └── AGENT.md               # Outline design agent instructions
│   │   ├── /writer/
│   │   │   └── AGENT.md               # Chapter writing agent instructions
│   │   ├── /editor/
│   │   │   └── AGENT.md               # Editing/validation agent instructions
│   │   └── /translator/
│   │       └── AGENT.md               # Translation agent instructions
│   ├── /skills/
│   │   ├── /web-research/
│   │   │   └── SKILL.md
│   │   ├── /reference-analyzer/
│   │   │   ├── SKILL.md
│   │   │   └── /scripts/              # File parsing scripts
│   │   ├── /code-example-validator/
│   │   │   ├── SKILL.md
│   │   │   └── /scripts/              # Linter execution scripts
│   │   ├── /quality-checker/
│   │   │   └── SKILL.md
│   │   ├── /image-generator/
│   │   │   ├── SKILL.md
│   │   │   ├── /scripts/              # Marker extraction, API call, marker replacement scripts
│   │   │   └── /references/           # Image generation API guide
│   │   ├── /pdf-builder/
│   │   │   ├── SKILL.md
│   │   │   ├── /scripts/              # Markdown→PDF conversion scripts
│   │   │   └── /references/           # Typesetting style config, font files
│   │   └── /web-viewer-builder/
│   │       ├── SKILL.md
│   │       ├── /scripts/              # Markdown→HTML conversion scripts
│   │       └── /references/           # Viewer HTML/CSS/JS templates
│   └── /plugins/
│       └── /legal/                    # Legal domain plugin (example)
│           ├── PLUGIN.md
│           ├── research_sources.md
│           ├── quality_criteria.md
│           └── /references/           # Existing agent design docs, etc.
├── /input/
│   └── /references/                   # User-provided general reference materials
├── /output/
│   ├── /research/                     # Step 1 output
│   │   └── research_report.md
│   ├── /outline/                      # Step 2 output
│   │   └── table_of_contents.md
│   ├── /chapters/
│   │   ├── /ko/                       # Step 3–4 output (Korean original)
│   │   └── /en/                       # Step 6 output (English translation)
│   ├── /images/                       # Step 5 output
│   ├── /edit/                         # Step 4 edit report
│   │   └── edit_report.md
│   ├── /final/                        # Step 7 output
│   │   ├── book_ko.pdf
│   │   └── book_en.pdf
│   ├── /web-viewer/                   # Step 8 output
│   │   └── index.html
│   ├── /logs/                         # Failure/skip logs
│   └── pipeline_state.json            # Pipeline state tracking
└── /docs/
    └── design.md                      # This design document
```

---

## 5. Technical Decisions

**Decision 1: Sub-agent execution — Claude Code Task tool**
- **Alternative**: Run multiple Claude Code instances as separate processes
- **Rejected because**: Task tool natively supports parallel execution within Claude Code; no external orchestration needed
- **Trade-off**: Dependent on Task tool's concurrent execution limits

**Decision 2: Markdown as intermediate format**
- **Alternative**: HTML as intermediate format, or JSON structured documents
- **Rejected because**: Markdown is the format LLMs generate most naturally, and it converts easily to both PDF and HTML
- **Trade-off**: Complex layouts (multi-column, sidebars) are limited in pure markdown. Must supplement with CSS/templates at typesetting stage

**Decision 3: PDF typesetting — WeasyPrint (or equivalent Python-based tool)**
- **Alternative**: LaTeX, Pandoc + wkhtmltopdf, Puppeteer
- **Rejected because**: LaTeX has high installation/debugging complexity. Puppeteer requires headless Chrome dependency. Pandoc lacks fine-grained typesetting control
- **Trade-off**: Layout limited to WeasyPrint's CSS support range. Advanced print typesetting (kerning, ligatures) not supported

**Decision 4: Image generation — diagram-first type routing**
- **Alternative**: single-provider Gemini, single-provider Images API, local Stable Diffusion, Codex-only private backend, manual SVG/Mermaid authoring
- **Rationale**: Text-heavy diagrams need deterministic labels more than photorealistic rendering, so `architecture`, `process_flow`, and `comparison_table` default to the local SVG `diagram` provider. Illustrative images can use Gemini. OpenAI and Codex remain explicit overrides for users who accept their cost/support tradeoffs.
- **Rejected because**: Single-provider Gemini struggles with text-heavy diagrams. Single-provider paid OpenAI is unnecessarily expensive for default illustrative images. Codex/god-tibo-imagen depends on an unsupported private backend. Manual Mermaid/SVG generation is too rigid for every visual type.
- **Trade-off**: Local SVG diagrams are more reliable and cheaper but less visually rich than image models. External providers remain optional and failures are surfaced through final validation rather than hidden as visible production artifacts.

**Decision 5: Web viewer — single HTML file (turn.js or equivalent library)**
- **Alternative**: React SPA, Next.js SSG, PDF.js viewer
- **Rejected because**: Single file is simplest for GitHub Pages static deployment. No build step needed
- **Trade-off**: Single file size may grow with many chapters. Add per-chapter lazy loading if needed

**Decision 6: Translation — direct LLM translation (per chapter)**
- **Alternative**: DeepL API, Google Translate API + LLM post-editing
- **Rejected because**: LLM direct translation is superior for context preservation and terminology consistency in technical books. API translation + post-editing is two steps and more complex
- **Trade-off**: Higher token cost (but cost is not a constraint)

**Decision 7: Pipeline state management — JSON file-based**
- **Alternative**: SQLite, in-memory state
- **Rejected because**: File-based is simplest in Claude Code environment and easiest to debug. On interrupt and resume, just read the state file
- **Trade-off**: No concurrent write safety (but only the main agent writes, so not an issue)

---

## 6. Open Items / Future Considerations

- **Image style consistency**: Continue tuning prompt templates and local diagram styling after reviewing generated book outputs
- **Token budget measurement**: Measure actual context sizes for Researcher, Architect, Writer, and Editor after chunking/summaries to set hard payload budgets
- **Auto-detection of inter-chapter dependencies**: Currently the Architect explicitly specifies dependencies during outline design. Future enhancement: auto-detect via research report analysis
- **Additional domain plugins**: Plugins for other domains (medical, finance, engineering) can be added using the same structure. Plugin authoring guide documentation needed
- **Incremental updates**: A partial regeneration pipeline for updating specific chapters post-publication and re-typesetting. Currently Gate 2 rejection supports partial fixes, but an independent update mode is not yet implemented
- **ePub/Kindle output**: Excluded from current scope, but since markdown is the intermediate format, an epub-builder skill can be added following the same pattern as pdf-builder
- **Multilingual expansion**: Currently supports KO→EN translation only. For additional languages, reuse the Translator agent with target language as a parameter
