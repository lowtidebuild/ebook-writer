#!/usr/bin/env python3
"""Validate code examples in markdown chapter files.

Usage:
    .venv/bin/python3 .claude/skills/code-example-validator/scripts/validate_code.py <markdown_file>
    .venv/bin/python3 .claude/skills/code-example-validator/scripts/validate_code.py --execute <file_or_directory>
    .venv/bin/python3 .claude/skills/code-example-validator/scripts/validate_code.py --execute --sandbox docker <file_or_directory>

Extracts fenced code blocks and validates syntax per language.
With --execute, runs :runnable tagged blocks and checks expected output.
Docker sandboxing is used when available. Process execution requires
--allow-unsafe-process and is intended only for trusted local examples.
Output: JSON to stdout
"""

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile

from execution_sandbox import (
    SandboxConfig,
    SandboxUnavailableError,
    UnsafeCodeError,
    resolve_executor,
    run_code_in_sandbox,
)
from markdown_utils import extract_code_blocks


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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Validate markdown code blocks and execute runnable examples.",
    )
    parser.add_argument("target", help="Markdown file, or chapter directory with --execute.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute :runnable blocks instead of syntax-only validation.",
    )
    parser.add_argument(
        "--sandbox",
        choices=["auto", "docker", "process"],
        default="auto",
        help="Sandbox backend for --execute (default: auto).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Execution timeout in seconds for --execute (default: 30).",
    )
    parser.add_argument(
        "--allow-unsafe-process",
        action="store_true",
        help="Allow --sandbox process fallback for trusted local examples only.",
    )
    return parser.parse_args(argv)


def execute_block(
    code: str,
    language: str,
    sandbox_mode: str = "auto",
    timeout: int = 30,
    allow_unsafe_process: bool = False,
) -> dict:
    """Execute a :runnable code block and return results."""
    if resolve_executor(language) is None:
        return {"status": "skipped", "reason": f"No executor for {language}"}

    config = SandboxConfig(
        mode=sandbox_mode,
        timeout_seconds=timeout,
        allow_unsafe_process=allow_unsafe_process,
    )

    try:
        sandbox_result = run_code_in_sandbox(code, language, config)
    except UnsafeCodeError as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "stdout": "",
            "stderr": "",
            "sandbox": {
                "backend": sandbox_mode,
                "network_access": "blocked_by_static_lint",
            },
        }
    except SandboxUnavailableError as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "stdout": "",
            "stderr": "",
            "sandbox": {"backend": sandbox_mode},
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "error": f"TimeoutExpired: execution exceeded {timeout}s",
            "stdout": "",
            "stderr": "",
            "sandbox": {"backend": sandbox_mode},
        }
    expected = extract_expected_output(code)
    stdout = sandbox_result["stdout"]

    if sandbox_result["returncode"] != 0:
        return {
            "status": "failed",
            "error": sandbox_result["stderr"],
            "stdout": stdout,
            "stderr": sandbox_result["stderr"],
            "sandbox": sandbox_result["sandbox"],
        }

    output = {
        "status": "passed",
        "stdout": stdout,
        "sandbox": sandbox_result["sandbox"],
    }

    if expected is not None:
        output["expected_output"] = expected
        output["match"] = stdout.strip() == expected.strip()
        if not output["match"]:
            output["status"] = "failed"
            output["error"] = f"Output mismatch: expected '{expected}', got '{stdout.strip()}'"

    return output


def run_execute_mode(
    path: str,
    sandbox_mode: str = "auto",
    timeout: int = 30,
    allow_unsafe_process: bool = False,
):
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
            result = execute_block(
                block["code"],
                block["language"],
                sandbox_mode=sandbox_mode,
                timeout=timeout,
                allow_unsafe_process=allow_unsafe_process,
            )
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


def main(argv: list[str] | None = None):
    args = parse_args(argv)

    if args.execute:
        if not os.path.exists(args.target):
            print(json.dumps({"error": f"Path not found: {args.target}"}))
            sys.exit(1)
        run_execute_mode(
            args.target,
            sandbox_mode=args.sandbox,
            timeout=args.timeout,
            allow_unsafe_process=args.allow_unsafe_process,
        )
    else:
        if not os.path.exists(args.target):
            print(json.dumps({"error": f"File not found: {args.target}"}))
            sys.exit(1)
        run_syntax_mode(args.target)


if __name__ == "__main__":
    main()
