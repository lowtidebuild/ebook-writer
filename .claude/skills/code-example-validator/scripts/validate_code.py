#!/usr/bin/env python3
"""Validate code examples in markdown chapter files.

Usage:
    python3 validate_code.py <markdown_file>

Extracts fenced code blocks and validates syntax per language.
Output: JSON to stdout
"""

import ast
import json
import os
import re
import subprocess
import sys
import tempfile


def extract_code_blocks(markdown_text: str) -> list[dict]:
    """Extract fenced code blocks with language tags and line numbers."""
    blocks = []
    pattern = re.compile(r"^```(\w+)?\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)

    for i, match in enumerate(pattern.finditer(markdown_text)):
        language = match.group(1) or "unknown"
        code = match.group(2)
        # Calculate line number in the original file
        line_number = markdown_text[: match.start()].count("\n") + 1
        blocks.append({
            "block_index": i,
            "language": language.lower(),
            "code": code,
            "line_in_file": line_number,
        })

    return blocks


def validate_python(code: str) -> str | None:
    """Validate Python syntax using ast.parse()."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"SyntaxError: {e.msg} (line {e.lineno})"


def validate_javascript(code: str) -> str | None:
    """Validate JavaScript syntax using node --check."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            tmp_path = f.name
        result = subprocess.run(
            ["node", "--check", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        os.unlink(tmp_path)
        if result.returncode != 0:
            return result.stderr.strip().split("\n")[0]
        return None
    except FileNotFoundError:
        return None  # node not available, skip
    except subprocess.TimeoutExpired:
        return "Validation timed out"
    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def validate_bash(code: str) -> str | None:
    """Validate Bash syntax using bash -n."""
    try:
        result = subprocess.run(
            ["bash", "-n"],
            input=code,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return result.stderr.strip().split("\n")[0]
        return None
    except subprocess.TimeoutExpired:
        return "Validation timed out"


VALIDATORS = {
    "python": validate_python,
    "py": validate_python,
    "python3": validate_python,
    "javascript": validate_javascript,
    "js": validate_javascript,
    "typescript": validate_javascript,
    "ts": validate_javascript,
    "bash": validate_bash,
    "sh": validate_bash,
    "shell": validate_bash,
    "zsh": validate_bash,
}


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: validate_code.py <markdown_file>"}))
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(json.dumps({"error": f"File not found: {file_path}"}))
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = extract_code_blocks(content)
    errors = []
    valid_count = 0
    unchecked_count = 0

    for block in blocks:
        language = block["language"]
        validator = VALIDATORS.get(language)

        if validator is None:
            unchecked_count += 1
            continue

        error = validator(block["code"])
        if error is None:
            valid_count += 1
        else:
            errors.append({
                "block_index": block["block_index"],
                "language": language,
                "line_in_file": block["line_in_file"],
                "error": error,
            })

    result = {
        "file": os.path.basename(file_path),
        "total_blocks": len(blocks),
        "valid": valid_count,
        "invalid": len(errors),
        "unchecked": unchecked_count,
        "errors": errors,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
