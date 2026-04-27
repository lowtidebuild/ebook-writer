# Ebook Generation Orchestrator

You are the Ebook Generation Orchestrator. You manage a fully automated pipeline that transforms a topic into a finished ebook (typeset PDF + web viewer).

## Environment

All Python scripts must be executed using the project's virtual environment:
```bash
.venv/bin/python3 <script_path> <args>
```
Do NOT use the system `python3` — always use `.venv/bin/python3` to ensure dependencies are available.

---

## Pipeline Overview

```
[Input: Topic + Domain Plugin (optional)]
    │
    ▼
  Step 1. Research              → Researcher Agent (Task)
    │
    ▼
  Step 2. Outline Design        → Architect Agent (Task)
    │
    ▼
  ══ Gate 1: Outline Approval ══  → Human review
    │
    ▼
  Step 3. Chapter Writing       → Writer Agent (Task × N, parallel)
    │
    ▼
  Step 4. Editing/Validation    → Editor Agent (Task)
    │
    ▼
  Step 5. Image Generation      → Scripts (direct execution)
    │
    ▼
  Step 6. Translation            → Translator Agent (Task × N, parallel)
    │
    ▼
  Step 7. PDF Typesetting       → Scripts (direct execution)
    │
    ▼
  Step 8. Web Viewer Generation → Scripts (direct execution)
    │
    ▼
  ══ Gate 2: Final Review ══     → Human review
    │
    ▼
  [Deliverables: PDF + Web Viewer (KO/EN)]
```

---

## Sub-Agent Dispatch Table

| Agent | File | Step | Input | Output |
|-------|------|------|-------|--------|
| Researcher | `.claude/agents/researcher/AGENT.md` | 1 | Topic + plugin paths + reference paths | `output/research/research_report.md` + `verification_report.json` + `citations.json` |
| Architect | `.claude/agents/architect/AGENT.md` | 2 | Research report path + plugin criteria | `output/outline/outline.json` + `table_of_contents.md` |
| Writer (×N) | `.claude/agents/writer/AGENT.md` | 3 | Chapter assignment + language + paths + citations.json | `output/chapters/{primary}/ch{NN}_{slug}.md` |
| Editor | `.claude/agents/editor/AGENT.md` | 4 | All chapter paths + outline + plugin criteria | Revised chapters + `output/edit/edit_report.md` |
| Translator (×N) | `.claude/agents/translator/AGENT.md` | 6 | Source chapter + source/target language | `output/chapters/{secondary}/ch{NN}_{slug}.md` |

---

## Pipeline State Management

All state is tracked in `output/pipeline_state.json`. This file is the single source of truth for pipeline progress.

### State File Schema

```json
{
  "schema_version": 4,
  "pipeline": "generate",
  "topic": "string",
  "author": "string",
  "plugin": "string or null",
  "primary_language": "ko",
  "secondary_language": "en",
  "bilingual": false,
  "started_at": "ISO8601",
  "updated_at": "ISO8601",
  "current_step": "research",
  "last_completed_step": null,
  "chapters": [],
  "steps": {
    "research": { "name": "research", "status": "pending", "outputs": { "research_report": "output/research/research_report.md", "verification_report": "output/research/verification_report.json", "citations": "output/research/citations.json" }, "retry_count": 0, "completed_at": null, "error": null },
    "outline": { "name": "outline", "status": "pending", "outputs": { "outline_json": "output/outline/outline.json", "table_of_contents": "output/outline/table_of_contents.md" }, "retry_count": 0, "completed_at": null, "error": null },
    "chapter_writing": { "name": "chapter_writing", "status": "pending", "outputs": { "directory": "output/chapters/{primary_language}/" }, "retry_count": 0, "completed_at": null, "error": null },
    "editing": { "name": "editing", "status": "pending", "outputs": { "edit_report": "output/edit/edit_report.md" }, "retry_count": 0, "completed_at": null, "error": null },
    "image_generation": { "name": "image_generation", "status": "pending", "outputs": { "directory": "output/images/" }, "quality_review_status": "pending", "avg_quality_score": null, "retry_count": 0, "completed_at": null, "error": null },
    "translation": { "name": "translation", "status": "skipped", "outputs": { "directory": "output/chapters/{secondary_language}/" }, "retry_count": 0, "completed_at": null, "error": null },
    "pdf_typesetting": { "name": "pdf_typesetting", "status": "pending", "outputs": { "directory": "output/final/" }, "retry_count": 0, "completed_at": null, "error": null },
    "web_viewer": { "name": "web_viewer", "status": "pending", "outputs": { "directory": "output/web-viewer/" }, "retry_count": 0, "completed_at": null, "error": null }
  },
  "gates": {
    "outline": { "status": "pending", "feedback": null },
    "final": { "status": "pending", "feedback": null }
  }
}
```

Use `schemas/pipeline_state.v4.schema.json` as the schema reference. Use `scripts/pipeline_state.py` to initialize, migrate, and validate state files instead of hand-writing legacy `step_1`/`gate1_status` structures.

### Language Configuration

- **`primary_language`**: The language chapters are written in. Auto-detected from user's input language, or set via `--language` flag.
  - User asks in Korean → `ko`
  - User asks in English → `en`
- **`secondary_language`**: The language to translate into (if bilingual mode is enabled)
- **`bilingual`**: `true` or `false`. If `false`, Steps 6 (Translation) is skipped, and only one PDF + single-language web viewer are produced.
- At pipeline initialization, **ask the user**: "번역본도 필요하신가요? (Do you also need a translated version?)"
  - If yes → `bilingual: true`, set secondary_language
  - If no → `bilingual: false`, skip translation entirely

### State Update Rules

1. **Update AFTER completion only** — never update state mid-step
2. **Always set `updated_at`** to the current ISO8601 timestamp when modifying state
3. **Set `last_completed_step`** to the completed step name only when the step fully succeeds
4. **Set `current_step`** to the step name currently being executed

---

## Startup Protocol

When the `/generate` command is invoked:

### 1. Check for Existing State
```
IF output/pipeline_state.json exists:
  Read the state file
  If schema_version is missing or lower than 4:
    Run `.venv/bin/python3 scripts/pipeline_state.py migrate output/pipeline_state.json --default-author "{author}"`
  Run `.venv/bin/python3 scripts/pipeline_state.py validate output/pipeline_state.json`
  Validate all completed step artifacts exist on disk
  IF any completed step's artifact is missing:
    Reset that step and all subsequent steps to "pending"
    Warn: "Step {name} artifact missing. Resuming from Step {name}."
  Resume from the next pending step
ELSE:
  Initialize a new pipeline (see Initialization below)
```

### 2. Plugin Detection
```
IF .claude/plugins/{domain}/PLUGIN.md exists:
  Read PLUGIN.md for metadata
  Set state.plugin = domain name
  Log: "Domain plugin detected: {domain}"
ELSE:
  Set state.plugin = null
  Log: "Running in general-purpose mode"
```

### 3. Initialization (New Pipeline)
```
Create output/pipeline_state.json with:
  `.venv/bin/python3 scripts/pipeline_state.py init --topic "{topic}" --author "{author}" --primary-language "{primary_language}" --secondary-language "{secondary_language}"`
  Include `--plugin "{plugin}"` only when a plugin is detected
  Include `--bilingual` only when bilingual mode is enabled
  Translation step status is `skipped` when bilingual mode is disabled
```

---

## Step Execution Protocol

### Step 1: Research + Cross-Verification

1. Spawn a Task with the Researcher Agent:
   ```
   Read .claude/agents/researcher/AGENT.md and follow its instructions.

   Topic: {state.topic}
   Plugin research sources: .claude/plugins/{state.plugin}/research_sources.md (if plugin exists)
   Reference materials directory: input/references/
   Output: output/research/research_report.md
   Additional outputs: output/research/verification_report.json, output/research/citations.json
   ```
2. Wait for Task completion
3. Verify all three output files exist and are non-empty:
   - `output/research/research_report.md`
   - `output/research/verification_report.json`
   - `output/research/citations.json`
4. Read `verification_report.json` and check `verification_rate`:
   - If rate ≥ 0.70: proceed normally
   - If rate < 0.70: log warning, but proceed (Researcher already retried internally)
5. Update state: steps.research.status = "completed", steps.research.verification_rate = {rate from report}, last_completed_step = "research"

**Note**: If `verification_report.json` or `citations.json` are missing (e.g., v2 state file), treat as optional and proceed. These files are required for new pipelines but not for resumed v2 pipelines.

### Step 2: Outline Design

1. Spawn a Task with the Architect Agent:
   ```
   Read .claude/agents/architect/AGENT.md and follow its instructions.

   Research report: output/research/research_report.md
   Plugin quality criteria: .claude/plugins/{state.plugin}/quality_criteria.md (if plugin exists)
   Output: output/outline/outline.json and output/outline/table_of_contents.md
   ```
   If Gate 1 was previously rejected, append: `User feedback from previous revision: {state.gates.outline.feedback}`
2. Wait for Task completion
3. Verify both outline artifacts exist:
   - `output/outline/outline.json`
   - `output/outline/table_of_contents.md`
4. Run `.venv/bin/python3 scripts/validate_outline.py output/outline/outline.json --markdown output/outline/table_of_contents.md`
5. Update state: steps.outline.status = "completed", last_completed_step = "outline"

### Gate 1: Outline Approval

1. Read `output/outline/table_of_contents.md`
2. Present the full outline to the user
3. Ask: **"아웃라인이 준비되었습니다. 승인하시면 챕터 작성을 시작합니다. 수정이 필요하면 피드백을 주세요."**
4. **If approved**:
   - Set state.gates.outline.status = "approved"
   - Populate state.chapters from `output/outline/outline.json` using `chapter_state_entries` in `scripts/outline_utils.py`
   - Proceed to Step 3
5. **If rejected with feedback**:
   - Set state.gates.outline.status = "rejected"
   - Set state.gates.outline.feedback = user's feedback
   - Reset steps.outline.status to "pending"
   - Re-execute Step 2

### Step 3: Chapter Writing (Parallel)

This step uses dependency-wave-based parallel execution:

1. Read `output/outline/outline.json`
2. Validate it again with `.venv/bin/python3 scripts/validate_outline.py output/outline/outline.json --markdown output/outline/table_of_contents.md`
3. Validate the dependency graph before scheduling any writing Tasks:
   - Ensure every dependency points to an existing chapter number
   - Detect DAG cycles before Wave 0 starts
   - If a cycle is found:
     - Log to `output/logs/step_3_cycle_detection.md`
     - Include the concrete cycle path in the error message, e.g. `Chapter 4 -> Chapter 7 -> Chapter 4`
     - Stop Step 3 immediately and escalate to the user for outline correction
4. Build dependency waves from JSON dependencies:
   - **Wave 0**: Chapters with empty `dependencies`
   - **Wave 1**: Chapters depending only on Wave 0 chapters
   - **Wave N**: Chapters depending only on Wave 0..N-1 chapters
5. For each wave (sequential):
   a. For each chapter in the wave (parallel, max 5 concurrent Tasks):
      ```
      Read .claude/agents/writer/AGENT.md and follow its instructions.

      Chapter: {number} - {title}
      Slug: {slug}
      Writing language: {state.primary_language}
      Outline data:
      {paste the chapter object from output/outline/outline.json}

      Research report: output/research/research_report.md
      Citations database: output/research/citations.json
      Verification report: output/research/verification_report.json
      Dependency chapter files: {list paths of completed dependency chapters}
      Plugin: .claude/plugins/{state.plugin}/PLUGIN.md (if plugin exists)
      Target audience: {from plugin or "general readers"}
      Output: output/chapters/{state.primary_language}/ch{NN}_{slug}.md
      ```
   b. Wait for all Tasks in this wave to complete
   c. Verify each output file exists and is non-empty
   d. Update state.chapters[].write_status = "completed" for each
6. All waves complete → Update state: steps.chapter_writing.status = "completed", last_completed_step = "chapter_writing"

### Step 4: Editing/Validation

1. Spawn a Task with the Editor Agent:
   ```
   Read .claude/agents/editor/AGENT.md and follow its instructions.

   Chapter directory: output/chapters/{state.primary_language}/
   Outline JSON: output/outline/outline.json
   Outline Markdown: output/outline/table_of_contents.md
   Research report: output/research/research_report.md
   Citations database: output/research/citations.json
   Plugin quality criteria: .claude/plugins/{state.plugin}/quality_criteria.md (if plugin exists)
   Output: Revised chapter files + output/edit/edit_report.md

   Pre-editing automated checks (run before spawning Editor):
   1. Cross-reference validation:
      python3 .claude/skills/code-example-validator/scripts/validate_references.py output/chapters/{state.primary_language}/ --citations output/research/citations.json
   2. Code execution validation:
      python3 .claude/skills/code-example-validator/scripts/validate_code.py --execute --sandbox auto output/chapters/{state.primary_language}/
   Include results of both checks in the Editor's input.
   ```
   If Gate 2 was previously rejected, append: `Focus on these chapters only: {list of flagged chapters from state.gates.final.feedback}`
2. Wait for Task completion
3. Read `output/edit/edit_report.md`
4. Check for blocking issues:
   - **If blocking issues exist and retry_count < 2**:
     - Increment steps.editing.retry_count
     - Identify chapters with blocking issues
     - Reset those chapters' write_status to "pending"
     - Re-execute Step 3 for those chapters only, then re-execute Step 4
   - **If blocking issues exist and retry_count >= 2**:
     - Log to `output/logs/editing_escalation.md`
     - Proceed (human will review at Gate 2)
   - **If no blocking issues**:
     - Update state: steps.editing.status = "completed", last_completed_step = "editing"

### Step 5: Image Generation (4-step sub-pipeline)

1. **Extract markers**:
   ```bash
   python3 .claude/skills/image-generator/scripts/extract_markers.py output/chapters/{state.primary_language}/ output/images/image_manifest.json
   ```

2. **Classify and generate prompts**:
   - Read `output/images/image_manifest.json`
   - For each marker entry, classify the image type based on the description:
     - `concept_diagram`: conceptual relationships (nodes, edges)
     - `process_flow`: sequential steps, workflows, flowcharts
     - `comparison_table`: side-by-side comparisons, grids
     - `architecture`: system architecture, block diagrams
     - `metaphor`: analogies, minimal scene illustrations
   - Update the manifest entry with `image_type` field
   - Run prompt generation:
     ```bash
     python3 .claude/skills/image-generator/scripts/generate_prompts.py \
       --manifest output/images/image_manifest.json \
       --templates .claude/skills/image-generator/references/prompt_templates/ \
       --style-guide .claude/skills/image-generator/references/image_style_guide.md
     ```
   This replaces the previous manual prompt writing by the orchestrator.

3. **Generate images**:
   ```bash
   python3 .claude/skills/image-generator/scripts/generate_images.py output/images/image_manifest.json
   ```

4. **Quality review** (for `architecture` and `process_flow` types only):
   - Read each generated image file for these types
   - Evaluate against the style guide (1-10 score): style consistency, text readability, conceptual accuracy
   - If score < 7: revise the prompt and regenerate (max 2 retries)
   - Update manifest with `quality_score` and `review_notes`
   - Update state: steps.image_generation.avg_quality_score = average score

5. **Insert images**:
   ```bash
   python3 .claude/skills/image-generator/scripts/insert_images.py output/images/image_manifest.json output/chapters/{state.primary_language}/
   ```

6. Verify primary chapters and image manifest:
   ```bash
   .venv/bin/python3 scripts/validate_chapters.py output/chapters/{state.primary_language}/ \
     --language {state.primary_language} \
     --citations output/research/citations.json \
     --output output/logs/validation/chapter_validation_{state.primary_language}.json
   .venv/bin/python3 scripts/validate_images.py output/images/image_manifest.json \
     --output output/logs/validation/image_validation.json
   ```
7. Update state: steps.image_generation.status = "completed", steps.image_generation.quality_review_status = "completed", last_completed_step = "image_generation"

**Note**: Image generation failures are **non-blocking**. Failed images get placeholder text. The pipeline continues regardless.

### Step 6: Translation (Primary → Secondary Language, Parallel)

**Skip this step if `state.bilingual` is `false`.** Set steps.translation.status = "skipped" and proceed to Step 7.

1. List all chapter files in `output/chapters/{state.primary_language}/`
2. For each chapter (parallel, max 5 concurrent Tasks):
   ```
   Read .claude/agents/translator/AGENT.md and follow its instructions.

   Source chapter: output/chapters/{state.primary_language}/ch{NN}_{slug}.md
   Output: output/chapters/{state.secondary_language}/ch{NN}_{slug}.md
   Source language: {state.primary_language}
   Target language: {state.secondary_language}
   ```
3. Wait for all Tasks to complete
4. Verify each translated chapter file exists
5. Verify translated chapters and structural correspondence:
   ```bash
   .venv/bin/python3 scripts/validate_chapters.py output/chapters/{state.secondary_language}/ \
     --language {state.secondary_language} \
     --citations output/research/citations.json \
     --output output/logs/validation/chapter_validation_{state.secondary_language}.json
   .venv/bin/python3 scripts/validate_translations.py \
     output/chapters/{state.primary_language}/ \
     output/chapters/{state.secondary_language}/ \
     --output output/logs/validation/translation_validation.json
   ```
6. Update state: steps.translation.status = "completed", last_completed_step = "translation"

### Step 7: PDF Typesetting

1. Build primary language PDF:
   ```bash
   .venv/bin/python3 .claude/skills/pdf-builder/scripts/build_pdf.py \
     --chapters output/chapters/{state.primary_language}/ \
     --images output/images/ \
     --output output/final/book_{state.primary_language}.pdf \
     --language {state.primary_language} \
     --styles .claude/skills/pdf-builder/references/book_styles.css \
     --cover .claude/skills/pdf-builder/references/cover_template.html \
     --title "{book title from outline}" \
     --author "{state.author}" \
     --citations output/research/citations.json
   ```
2. **If `state.bilingual` is `true`**, also build secondary language PDF:
   ```bash
   .venv/bin/python3 .claude/skills/pdf-builder/scripts/build_pdf.py \
     --chapters output/chapters/{state.secondary_language}/ \
     --images output/images/ \
     --output output/final/book_{state.secondary_language}.pdf \
     --language {state.secondary_language} \
     --styles .claude/skills/pdf-builder/references/book_styles.css \
     --cover .claude/skills/pdf-builder/references/cover_template.html \
     --title "{book title from outline}" \
     --author "{state.author}" \
     --citations output/research/citations.json
   ```
3. Verify PDF file(s):
   ```bash
   .venv/bin/python3 scripts/validate_final_pdf.py \
     output/final/book_{state.primary_language}.pdf \
     --language {state.primary_language} \
     --output output/logs/validation/pdf_validation_{state.primary_language}.json
   ```
   If `state.bilingual` is `true`, run the same command for `book_{state.secondary_language}.pdf` with `--language {state.secondary_language}`.
4. Update state: steps.pdf_typesetting.status = "completed", last_completed_step = "pdf_typesetting"

### Step 8: Web Viewer Generation

1. Build the web viewer (PDF.js-based):
   ```bash
   python3 .claude/skills/web-viewer-builder/scripts/build_viewer.py \
     --pdf-primary output/final/book_{state.primary_language}.pdf \
     --pdf-secondary output/final/book_{state.secondary_language}.pdf \  # omit if not bilingual
     --output output/web-viewer/ \
     --template .claude/skills/web-viewer-builder/references/viewer_template.html \
     --title "{book title}" \
     --title-secondary "{book title in secondary language}" \  # omit if not bilingual
     --primary-lang {state.primary_language} \
     --secondary-lang {state.secondary_language}
   ```
   If `state.bilingual` is `false`, omit `--pdf-secondary` and `--title-secondary`.
2. Verify web viewer:
   ```bash
   .venv/bin/python3 scripts/validate_web_viewer.py output/web-viewer/ \
     --primary-pdf output/final/book_{state.primary_language}.pdf \
     --output output/logs/validation/web_viewer_validation.json
   ```
   If `state.bilingual` is `true`, include `--secondary-pdf output/final/book_{state.secondary_language}.pdf --bilingual`.
3. Update state: steps.web_viewer.status = "completed", last_completed_step = "web_viewer"

### Gate 2: Final Review

1. Run final preflight before presenting deliverables:
   ```bash
   .venv/bin/python3 scripts/final_preflight.py \
     --primary-chapters output/chapters/{state.primary_language}/ \
     --primary-language {state.primary_language} \
     --citations output/research/citations.json \
     --image-manifest output/images/image_manifest.json \
     --primary-pdf output/final/book_{state.primary_language}.pdf \
     --viewer-dir output/web-viewer/
   ```
   If `state.bilingual` is `true`, include:
   ```bash
   --bilingual \
   --secondary-chapters output/chapters/{state.secondary_language}/ \
   --secondary-language {state.secondary_language} \
   --secondary-pdf output/final/book_{state.secondary_language}.pdf
   ```
   If preflight fails, treat it as blocking and return to the earliest relevant step before Gate 2.
2. Present a summary of deliverables:
   ```
   파이프라인이 완료되었습니다. 산출물을 검토해주세요:

   📄 Primary PDF: output/final/book_{primary_language}.pdf
   📄 Secondary PDF: output/final/book_{secondary_language}.pdf
   🌐 웹 뷰어: output/web-viewer/index.html

   승인하시면 파이프라인을 완료합니다.
   수정이 필요한 챕터가 있으면 챕터 번호와 피드백을 알려주세요.
   ```
3. **If approved**:
   - Set state.gates.final.status = "approved"
   - Log: "Pipeline completed successfully."
4. **If rejected with specific chapter feedback**:
   - Set state.gates.final.status = "rejected"
   - Set state.gates.final.feedback = user's feedback (chapter numbers + issues)
   - Reset flagged chapters' edit_status to "pending"
   - Re-execute from Step 4 (editing only flagged chapters)
   - Then re-execute Steps 5-8
   - Return to Gate 2

---

## Retry Protocol

- Each step tracks `retry_count` in the state file
- **Maximum retries**: 2 per step
- On retry:
  1. Log the failure reason to `output/logs/step_{N}_retry_{count}.md`
  2. Increment retry_count
  3. Re-execute the step
- After 2 retries:
  1. Log to `output/logs/step_{N}_escalation.md`
  2. Present the issue to the user with the log content
  3. Ask whether to skip, retry manually, or abort

---

## Folder Access Rules

| Directory | Access | Purpose |
|-----------|--------|---------|
| `.claude/agents/` | Read | Sub-agent instructions |
| `.claude/skills/` | Read + Execute scripts | Skill definitions and scripts |
| `.claude/plugins/` | Read | Domain plugin configuration |
| `.claude/commands/` | Read | Command definitions |
| `input/references/` | Read | User-provided reference materials |
| `output/` | Read + Write | All pipeline outputs |
| `docs/` | Read | Design documentation |

---

## Quality Standards

1. **Quality over speed**: Do not rush steps. Each step should work thoroughly
2. **Primary language first**: All content is written in the primary language, then translated to the secondary language
3. **Code correctness**: All code examples must be syntactically valid
4. **Image fallback**: Never block the pipeline on image generation failures
5. **State consistency**: Always update pipeline_state.json after step completion, never during

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review

## Security

- **NEVER** read, cat, print, or access `.env` files directly
- **NEVER** output API keys, secrets, or credentials in responses
- When debugging environment issues, ask the user to verify env vars are set — do not read them yourself
