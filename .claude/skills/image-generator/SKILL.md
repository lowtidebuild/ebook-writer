# Image Generator Skill

## Purpose

Extract `[IMAGE: ...]` markers from generated chapter files, generate matching images via a per-entry image provider, and insert the resulting images back into the markdown chapters. Four providers are supported and each entry is routed by `image_type`:

- **`diagram`** (default for text-heavy diagrams: `architecture`, `process_flow`, `comparison_table`) — deterministic local SVG renderer. No API key, network, or private backend required.
- **`gemini`** (default for illustrative types: `concept_diagram`, `metaphor`) — Google Gemini multimodal image output. Cheap, stable.
- **`openai`** (explicit override only) — paid OpenAI Images API (`gpt-image-*`). Available when callers want the supported public API.
- **`codex`** (explicit override only) — routes through [god-tibo-imagen](https://github.com/NomaDamas/god-tibo-imagen) using local Codex CLI auth (`~/.codex/auth.json`). Backend is unsupported by OpenAI and may break without warning.

Failed entries remain blocking in final preflight. Insertion uses a neutral caption fallback instead of a visible `[이미지 생성 실패]` production artifact.

## Pipeline

The skill operates as a 4-step script pipeline executed in order:

### Step 1: Extract Markers (`extract_markers.py`)

Scans all `.md` chapter files for `[IMAGE: description]` patterns and produces an `image_manifest.json` listing every marker with its location, description, and a pending status.

```bash
python3 scripts/extract_markers.py output/chapters/ko/ output/images/image_manifest.json
```

### Step 2: Classify & Generate Prompts (`generate_prompts.py`)

The orchestrator first classifies each marker's `image_type` (concept_diagram, process_flow, comparison_table, architecture, metaphor) based on the description. Then `generate_prompts.py` applies type-specific prompt templates from `references/prompt_templates/` to generate prompts, assigns each entry a `provider`, and fills `output_path` with the provider-specific extension. Set `IMAGE_PROVIDER=diagram|codex|gemini|openai` to override globally.

```bash
python3 scripts/generate_prompts.py \
  --manifest output/images/image_manifest.json \
  --templates references/prompt_templates/ \
  --style-guide references/image_style_guide.md
```

This replaces the previous manual prompt writing step. Template files: `concept_diagram.txt`, `process_flow.txt`, `comparison_table.txt`, `architecture.txt`, `metaphor.txt`, `generic.txt` (fallback).

### Step 3: Generate Images (`generate_images.py`)

Reads the manifest and dispatches every pending entry to the backend named by its `provider` field — `diagram` (local SVG), `gemini` (Google Gemini), `openai` (paid Images API), or `codex` (optional god-tibo-imagen via Codex CLI auth). Saves each file and marks the entry `completed` or `failed`.

```bash
python3 scripts/generate_images.py output/images/image_manifest.json
```

Provider requirements:

- **diagram**: no external dependency. Produces SVG.
- **codex**: `pip install god-tibo-imagen` and a working `codex login` (`~/.codex/auth.json`). No API key. Model defaults to `gpt-5.4`; override with `CODEX_IMAGE_MODEL`.
- **gemini**: `GEMINI_API_KEY` env var. Model defaults to `gemini-3.1-flash-image-preview`; override with `IMAGE_MODEL`.
- **openai**: `OPENAI_API_KEY` env var. Model defaults to `gpt-image-1`; override with `OPENAI_IMAGE_MODEL`. Size and quality via `OPENAI_IMAGE_SIZE` / `OPENAI_IMAGE_QUALITY`.

Set `IMAGE_PROVIDER=diagram|codex|gemini|openai` to force one provider for the whole run.

**Step 3.5: Quality Review** (orchestrator-driven, for `architecture` and `process_flow` types only)

The orchestrator reads each generated image and evaluates it against the style guide (score 1-10). Images scoring below 7 get their prompt revised and regenerated (max 2 retries). Results are recorded in the manifest as `quality_score` and `review_notes`.

### Step 4: Insert Images (`insert_images.py`)

Replaces every `[IMAGE: ...]` marker in the chapter files with either the generated image link or a neutral caption fallback. Completed entries use the manifest's `output_path` directly, so provider-specific file extensions such as `.png` and `.svg` are preserved.

```bash
python3 scripts/insert_images.py output/images/image_manifest.json output/chapters/ko/
```

## When to Use

Run this skill at **Step 5** of the ebook generation pipeline, after all chapters have been written and reviewed but before final PDF assembly.

## Failure Handling

Generation is resilient, but final review is strict:

- If a provider returns an error (quota exceeded, content policy violation, network failure, expired Codex auth, broken codex backend, etc.), the entry's status is set to `failed` with an error message and processing continues with the next entry.
- During insertion, failed entries receive a neutral caption fallback, not a production failure marker.
- Final preflight fails while the manifest contains `failed` or `pending` entries unless explicitly overridden.
- The manifest is saved after every generation attempt, so the pipeline can be re-run to retry only the failed entries.
