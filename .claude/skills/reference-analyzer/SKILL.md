# Reference Analyzer Skill

## Purpose
Parse and extract key content from reference materials in various formats (.md, .pdf, .txt, .docx).

## Capabilities
1. File type detection and appropriate parsing
2. Key content extraction (concepts, methodologies, insights)
3. Structured output for integration with research report

## Scripts
- `scripts/parse_references.py` — Parse reference files and extract text content

## Usage
```bash
python3 .claude/skills/reference-analyzer/scripts/parse_references.py <file_path>
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

## When to Use
- Researcher Agent processes files in `input/references/`
- When a domain plugin specifies reference materials

## Failure Handling
- PDF parsing failure → attempt `textutil` conversion (macOS)
- DOCX parsing failure → attempt raw XML extraction
- If all parsing methods fail → return status "failed" with error message
- Never block the pipeline on a single reference file failure
