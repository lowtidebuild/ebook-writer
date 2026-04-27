# Reference Analyzer Skill

## Purpose
Parse and extract key content from reference materials in various formats (.md, .pdf, .txt, .docx).

## Capabilities
1. File type detection and appropriate parsing
2. Key content extraction (concepts, methodologies, insights)
3. Structured output for integration with research report
4. Bounded chunk-file output to avoid injecting full references into agent context

## Scripts
- `scripts/parse_references.py` — Parse reference files and extract text content

## Usage
```bash
.venv/bin/python3 .claude/skills/reference-analyzer/scripts/parse_references.py <file_path>
.venv/bin/python3 .claude/skills/reference-analyzer/scripts/parse_references.py <file_path> \
  --output-dir output/research/reference_chunks/<source_name>/
```

Output: JSON to stdout
```json
{
  "filename": "reference.pdf",
  "content_type": "pdf",
  "extracted_text": "...",
  "word_count": 1500,
  "status": "success"
}
```

Prefer `--output-dir` in the ebook pipeline. In that mode stdout contains only
status, word count, chunk count, and manifest path; extracted text is written to
bounded chunk JSON files under `output/research/reference_chunks/`.

Chunked stdout example:
```json
{
  "filename": "reference.pdf",
  "content_type": "pdf",
  "word_count": 1500,
  "chunk_count": 3,
  "manifest_path": "output/research/reference_chunks/reference_pdf/manifest.json",
  "status": "success"
}
```

## When to Use
- Researcher Agent processes files in `input/references/`
- When a domain plugin specifies reference materials

## Failure Handling
- PDF parsing failure → attempt `textutil` conversion (macOS)
- DOCX parsing failure → attempt raw XML extraction
- If all parsing methods fail → return status "failed" with error message
- Never block the pipeline on a single reference file failure
