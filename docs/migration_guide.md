# Migration Guide

This guide summarizes the behavioral changes introduced by the v4 pipeline hardening work.

## Pipeline State

- Pipeline state now uses schema version 4 in `output/pipeline_state.json`.
- If an older state file exists, resume with:

```bash
.venv/bin/python3 scripts/pipeline_state.py migrate output/pipeline_state.json --default-author "Author Name"
.venv/bin/python3 scripts/pipeline_state.py validate output/pipeline_state.json
```

- New state files store `author`, `bilingual`, named steps, gates, and chapter status entries.

## Plugin Selection

- Domain plugins are no longer auto-detected from `.claude/plugins/`.
- Use `--plugin <domain>` to activate a plugin.
- Without `--plugin`, the pipeline runs in general-purpose mode even if plugin directories exist.

```bash
/generate "Claude Code for Lawyers" --plugin legal --author "Author Name"
/generate "General AI Workflow" --author "Author Name"
```

## Reference Materials

- Files under `input/references/` are ignored by git by default.
- Reference files are chunked before agent use to avoid injecting full private documents into context.

```bash
.venv/bin/python3 scripts/chunk_references.py input/references/ --output-dir output/research/reference_chunks/
```

- `parse_references.py --output-dir ...` writes chunk files and prints only status/manifest metadata to stdout.

## Code Execution Validation

- `:runnable` code blocks execute through Docker when available.
- Local process execution is disabled unless explicitly allowed for trusted examples.

```bash
.venv/bin/python3 .claude/skills/code-example-validator/scripts/validate_code.py \
  --execute \
  --sandbox process \
  --allow-unsafe-process \
  output/chapters/ko/
```

- Obvious network usage (`requests`, `urllib`, `socket`, `http.client`, `curl`, `wget`, `nc`, `ssh`) is rejected before execution.

## Image Generation

- Text-heavy diagrams default to local SVG generation through the `diagram` provider.
- Gemini remains available for illustrative image types.
- OpenAI and Codex/god-tibo-imagen are explicit override paths only.

```bash
IMAGE_PROVIDER=diagram
IMAGE_PROVIDER=gemini
IMAGE_PROVIDER=openai
IMAGE_PROVIDER=codex
```

- Failed or pending image entries are not silently accepted. They receive neutral caption fallback text in chapters but remain blocking in final validation unless explicitly approved.

## Final Validation

Before Gate 2, run the final preflight path from `CLAUDE.md`. It validates chapter artifacts, images, PDFs, and the web viewer before the user sees the final deliverables.
