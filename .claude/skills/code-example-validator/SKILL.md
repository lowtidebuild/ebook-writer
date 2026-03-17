# Code Example Validator Skill

## Purpose
Validate syntax correctness of code examples embedded in chapter markdown files.

## Capabilities
1. Extract fenced code blocks from markdown files
2. Validate syntax per language (Python, JavaScript, Bash, etc.)
3. Report validation results as JSON

## Scripts
- `scripts/validate_code.py` — Extract and validate code blocks from a markdown file

## Usage
```bash
python3 .claude/skills/code-example-validator/scripts/validate_code.py <markdown_file>
```

Output: JSON to stdout
```json
{
  "file": "ch01_introduction.md",
  "total_blocks": 5,
  "valid": 4,
  "invalid": 1,
  "errors": [
    {
      "block_index": 3,
      "language": "python",
      "line_in_file": 45,
      "error": "SyntaxError: unexpected EOF while parsing"
    }
  ]
}
```

## When to Use
- Writer Agent after completing a chapter (Step 3)
- Editor Agent during validation (Step 4)

## Supported Languages
- Python: `ast.parse()` validation
- JavaScript: `node --check` if available
- Bash/Shell: `bash -n` syntax check
- Other languages: skip validation, report as "unchecked"

## Failure Handling
- If a language validator is not available (e.g., node not installed): skip, mark as "unchecked"
- Never fail the entire validation because of one unsupported language
