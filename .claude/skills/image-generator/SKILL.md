# Image Generator Skill

## Purpose

Extract `[IMAGE: ...]` markers from generated chapter files, generate matching images via the Google Gemini API, and insert the resulting images back into the markdown chapters. The pipeline is non-blocking: if image generation fails for any entry, a placeholder is inserted instead so the ebook build can proceed without interruption.

## Pipeline

The skill operates as a 3-step script pipeline executed in order:

### Step 1: Extract Markers (`extract_markers.py`)

Scans all `.md` chapter files for `[IMAGE: description]` patterns and produces an `image_manifest.json` listing every marker with its location, description, and a pending status.

```bash
python3 scripts/extract_markers.py output/chapters/ko/ output/images/image_manifest.json
```

Between Step 1 and Step 2 the agent should review the manifest and fill in the `prompt` field for each entry. The prompt should follow the style guide in `references/image_style_guide.md`. Entries left with `"prompt": null` will be skipped during generation.

### Step 2: Generate Images (`generate_images.py`)

Reads the manifest, calls the Gemini image generation API for every pending entry that has a non-null prompt, saves the resulting PNG, and updates each entry's status to `completed` or `failed`.

```bash
python3 scripts/generate_images.py output/images/image_manifest.json
```

Requires the `GEMINI_API_KEY` environment variable. The model defaults to `imagen-3.0-generate-002` and can be overridden with the `IMAGE_MODEL` environment variable.

### Step 3: Insert Images (`insert_images.py`)

Replaces every `[IMAGE: ...]` marker in the chapter files with either the generated image link or a failure placeholder.

```bash
python3 scripts/insert_images.py output/images/image_manifest.json output/chapters/ko/
```

## When to Use

Run this skill at **Step 5** of the ebook generation pipeline, after all chapters have been written and reviewed but before final PDF assembly.

## Failure Handling

The pipeline is designed to be **non-blocking**:

- If the Gemini API returns an error (quota exceeded, content policy violation, network failure), the entry's status is set to `failed` with an error message and processing continues with the next entry.
- During insertion, failed entries receive a visible placeholder block in the markdown so the author can address them manually:
  ```
  > [이미지 생성 실패] description of the intended image
  ```
- The manifest is saved after every generation attempt, so the pipeline can be re-run to retry only the failed entries.
