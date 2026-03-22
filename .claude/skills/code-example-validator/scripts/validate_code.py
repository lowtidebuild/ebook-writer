#!/usr/bin/env python3
"""Validate code examples in markdown chapter files.

Usage:
    python3 validate_code.py <markdown_file>              # Syntax validation
    python3 validate_code.py --execute <file_or_directory> # Execute :runnable blocks

Extracts fenced code blocks and validates syntax per language.
With --execute, runs :runnable tagged blocks and checks expected output.
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
    pattern = re.compile(r"^```(\w+)?(?::(\w+))?\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)

    for i, match in enumerate(pattern.finditer(markdown_text)):
        language = match.group(1) or "unknown"
        tag = match.group(2)  # e.g., "runnable" or None
        code = match.group(3)
        # Calculate line number in the original file
        line_number = markdown_text[: match.start()].count("\n") + 1
        blocks.append({
            "block_index": i,
            "language": language.lower(),
            "tag": tag,
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


def extract_expected_output(code: str) -> str | None:
    """Extract expected output from '# Expected output: ...' comment."""
    for line in reversed(code.strip().split("\n")):
        line = line.strip()
        if line.startswith("# Expected output:"):
            return line[len("# Expected output:"):].strip()
    return None


def execute_block(code: str, language: str) -> dict:
    """Execute a :runnable code block and return results."""
    executors = {"python": ["python3"], "py": ["python3"], "python3": ["python3"],
                 "bash": ["bash"], "sh": ["bash"], "shell": ["bash"], "zsh": ["bash"]}

    cmd = executors.get(language)
    if cmd is None:
        return {"status": "skipped", "reason": f"No executor for {language}"}

    try:
        result = subprocess.run(
            cmd,
            input=code,
            capture_output=True,
            text=True,
            timeout=30,
        )
        expected = extract_expected_output(code)
        stdout = result.stdout.rstrip("\n")

        if result.returncode != 0:
            return {
                "status": "failed",
                "error": result.stderr.strip()[:500],
                "stdout": stdout,
                "stderr": result.stderr.strip()[:500],
            }

        output = {"status": "passed", "stdout": stdout}

        if expected is not None:
            output["expected_output"] = expected
            output["match"] = stdout.strip() == expected.strip()
            if not output["match"]:
                output["status"] = "failed"
                output["error"] = f"Output mismatch: expected '{expected}', got '{stdout.strip()}'"

        return output

    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": "TimeoutExpired: execution exceeded 30s",
                "stdout": "", "stderr": ""}


def run_execute_mode(path: str):
    """Execute :runnable blocks in a file or directory."""
    if os.path.isdir(path):
        files = sorted([os.path.join(path, f) for f in os.listdir(path)
                        if f.startswith("ch") and f.endswith(".md")])
    else:
        files = [path]

    all_results = []
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = extract_code_blocks(content)
        runnable = [b for b in blocks if b.get("tag") == "runnable"]

        file_results = []
        passed = 0
        failed = 0

        for block in runnable:
            result = execute_block(block["code"], block["language"])
            result["block_index"] = block["block_index"]
            result["language"] = block["language"]
            result["line_in_file"] = block["line_in_file"]
            file_results.append(result)
            if result["status"] == "passed":
                passed += 1
            elif result["status"] == "failed":
                failed += 1

        all_results.append({
            "file": os.path.basename(file_path),
            "total_runnable": len(runnable),
            "passed": passed,
            "failed": failed,
            "results": file_results,
        })

    print(json.dumps(all_results if len(all_results) > 1 else all_results[0],
                     ensure_ascii=False, indent=2))


def run_syntax_mode(file_path: str):
    """Original syntax validation mode."""
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


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: validate_code.py [--execute] <file_or_directory>"}))
        sys.exit(1)

    if sys.argv[1] == "--execute":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: validate_code.py --execute <file_or_directory>"}))
            sys.exit(1)
        path = sys.argv[2]
        if not os.path.exists(path):
            print(json.dumps({"error": f"Path not found: {path}"}))
            sys.exit(1)
        run_execute_mode(path)
    else:
        file_path = sys.argv[1]
        if not os.path.exists(file_path):
            print(json.dumps({"error": f"File not found: {file_path}"}))
            sys.exit(1)
        run_syntax_mode(file_path)


if __name__ == "__main__":
    main()
