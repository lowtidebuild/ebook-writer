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
| Input — Domain plugin | Plugin directory | `/.claude/plugins/{domain}/` | Optional. Without it, runs in general-purpose mode |
| Input — Reference materials | .md, .pdf, .docx | `/input/references/` | Source materials specified by plugin |
| Output — Markdown manuscripts | .md (per chapter) | `/output/chapters/ko/`, `/output/chapters/en/` | Korean original + English translation |
| Output — Images | .png/.svg | `/output/images/` | Infographics, diagrams per chapter |
| Output — PDF | .pdf | `/output/final/book_ko.pdf`, `book_en.pdf` | Typeset final book |
| Output — Web viewer | HTML/CSS/JS | `/output/web-viewer/` | For GitHub Pages deployment |

### 1.4 Constraints

- **Quality first**: Time/token cost is not a constraint. Each step must work thoroughly with proper validation; quality takes priority over speed
- **Minimal human intervention**: Only two gates — outline approval + final review
- **Image generation API dependency**: Dependent on external image generation API (Gemini etc.) availability and rate limits
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

- **Executor**: LLM (web search + reference material analysis)
- **Input**: Topic (natural language), plugin research source list (if present), reference materials in `/input/references/`
- **Processing**:
  1. Decompose topic into granular research questions (e.g., "What is Claude Code?", "Current state of AI in legal practice", "How to install Claude Code")
  2. Collect latest information via web search
  3. If plugin exists, collect additional information from plugin-specified sources (e.g., legal plugin → legislation/case law)
  4. If reference materials exist, analyze and extract key content
  5. Structure collected information by topic into a research report
- **Output**: `/output/research/research_report.md` — research results organized by topic, with sources
- **Success criteria**: Minimum research question count met; each question has at least one source-backed answer
- **Validation method**: LLM self-check — read the research report and judge "Is there sufficient information to design a book outline on this topic?"
- **On failure**: Generate additional research questions for information-sparse areas and re-collect (max 2 retries)

#### Step 2: Outline Design

- **Executor**: LLM
- **Input**: `/output/research/research_report.md`, plugin quality criteria (if present)
- **Processing**:
  1. Design part/chapter/section structure based on research report
  2. Specify per-chapter summary (2–3 sentences), key content to cover, estimated length
  3. Specify inter-chapter dependencies (where a chapter references prior chapter content)
  4. Design difficulty progression appropriate to reader level (easy → hard)
- **Output**: `/output/outline/table_of_contents.md`
- **Success criteria**: All major topics from the research report are placed; logical flow exists between chapters; each chapter includes summary/key content/estimated length
- **Validation method**: LLM self-check — "Are there topics covered in research that are missing from the outline?", "Would a reader progressing from Chapter 1 onward find the flow natural?"
- **On failure**: Supplement missing topics and regenerate (max 2 retries)

**═══ Gate 1: Outline Approval ═══**
- Present outline to user
- If approved, proceed to Step 3
- If revision requested, re-execute Step 2 with feedback (research results preserved)

#### Step 3: Chapter Writing (parallel)

- **Executor**: LLM (parallel Tasks per chapter)
- **Input**: `/output/outline/table_of_contents.md`, `/output/research/research_report.md`, chapter-specific reference materials (if present), preceding chapter manuscripts (if dependency exists)
- **Processing**:
  1. Chapters with no dependencies start writing in parallel
  2. Chapters with dependencies execute sequentially after their prerequisite completes
  3. Each chapter is written based on the outline's summary/key content
  4. Include working code examples where needed
  5. Mark image-needed locations with `[IMAGE: description]` markers at end of chapter
- **Output**: `/output/chapters/ko/ch{NN}_{slug}.md` (per-chapter markdown)
- **Success criteria**: All key content specified in outline is covered; explanation level matches target reader (zero coding experience); code examples are syntactically valid
- **Validation method**: Rule-based — keyword inclusion check against outline's key content, markdown structure validity, code block syntax check
- **On failure**: Rewrite the failing chapter (max 2 retries)

#### Step 4: Editing/Validation

- **Executor**: LLM
- **Input**: All chapters in `/output/chapters/ko/`, `/output/outline/table_of_contents.md`, plugin quality criteria (if present)
- **Processing**:
  1. Per-chapter quality review: content accuracy, clarity of explanation, reader-level appropriateness
  2. Apply domain plugin quality criteria (e.g., legal terminology accuracy, citation format)
  3. Cross-chapter consistency review: terminology unification, cross-reference integrity, tone consistency
  4. Directly fix issues by overwriting chapter files
  5. Generate edit report (change log, remaining issues)
- **Output**: Revised `/output/chapters/ko/ch{NN}_{slug}.md` files + `/output/edit/edit_report.md`
- **Success criteria**: Edit report states "no blocking issues"
- **Validation method**: LLM self-check — assess whether remaining issues in the edit report are blocking-level
- **On failure**: Return chapters with blocking issues to Step 3 for rewrite (max 2 retries). After 2 retries, log the issue and let the human decide at Gate 2

#### Step 5: Image Generation

- **Executor**: Script (image generation API calls) + LLM (prompt writing)
- **Input**: `[IMAGE: description]` markers from edited chapters
- **Processing**:
  1. Script extracts all `[IMAGE: ...]` markers from all chapters into a list
  2. LLM writes image generation prompts for each marker (matching book's tone/style)
  3. Script calls image generation API (with rate limit management)
  4. Insert generated images into chapter markdown (`[IMAGE: ...]` → `![alt](path)`)
- **Output**: `/output/images/ch{NN}_img{NN}.png` + chapters with images inserted
- **Success criteria**: All `[IMAGE: ...]` markers replaced with actual images; image files are not corrupted (file size > 0)
- **Validation method**: Script — check for remaining markers, verify image file existence/size
- **On failure**: Revise prompt and regenerate for failed images (max 2 retries). If still failing, insert placeholder text + log

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
- **Validation method**: Script — KO/EN chapter count match, code block count match, image reference count match. LLM self-check — quality review of 1–2 sample chapters
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

- **Executor**: Script + LLM (viewer code generation)
- **Input**: `/output/chapters/ko/`, `/output/chapters/en/`, `/output/images/`
- **Processing**:
  1. LLM generates web viewer HTML/CSS/JS with page-flip animation
  2. Convert markdown chapters to web-viewer-insertable format
  3. Include KO/EN language toggle
  4. Support mobile touch + desktop mouse
  5. Output as GitHub Pages-deployable structure
- **Output**: `/output/web-viewer/` (index.html + assets)
- **Success criteria**: index.html renders correctly locally; chapter navigation works; KO/EN toggle works
- **Validation method**: Script — HTML file existence, basic structure check (all chapter file references present)
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

**Decision 4: Image generation — Gemini API**
- **Alternative**: DALL-E, local Stable Diffusion, SVG/Mermaid code generation
- **Rejected because**: SVG/Mermaid has infographic quality limits. Local Stable Diffusion has environment setup burden. DALL-E is also viable but Gemini is currently accessible
- **Trade-off**: External API dependency, rate limit management needed, image style consistency must be controlled via prompts

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

- **Image style consistency**: To unify image tone/style across the entire book, standardize a style prefix in image generation prompts. Adjust prompt templates after reviewing first run results
- **Code example execution validation**: Current design only validates syntax. A step to actually execute and verify behavior could be added later (sandbox execution in Claude Code environment)
- **Auto-detection of inter-chapter dependencies**: Currently the Architect explicitly specifies dependencies during outline design. Future enhancement: auto-detect via research report analysis
- **Additional domain plugins**: Plugins for other domains (medical, finance, engineering) can be added using the same structure. Plugin authoring guide documentation needed
- **Incremental updates**: A partial regeneration pipeline for updating specific chapters post-publication and re-typesetting. Currently Gate 2 rejection supports partial fixes, but an independent update mode is not yet implemented
- **ePub/Kindle output**: Excluded from current scope, but since markdown is the intermediate format, an epub-builder skill can be added following the same pattern as pdf-builder
- **Multilingual expansion**: Currently supports KO→EN translation only. For additional languages, reuse the Translator agent with target language as a parameter
