from __future__ import annotations

import json

from helpers import load_module


validate_code = load_module(
    "test_validate_code_module",
    ".claude/skills/code-example-validator/scripts/validate_code.py",
)


def test_extract_code_blocks_reports_tags_and_line_numbers():
    markdown = (
        "# Title\n\n"
        "```python:runnable\n"
        "print('hi')\n"
        "```\n\n"
        "```bash\n"
        "echo hi\n"
        "```\n"
    )

    blocks = validate_code.extract_code_blocks(markdown)

    assert len(blocks) == 2
    assert blocks[0]["language"] == "python"
    assert blocks[0]["tag"] == "runnable"
    assert blocks[0]["line_in_file"] == 3
    assert blocks[1]["language"] == "bash"
    assert blocks[1]["line_in_file"] == 7


def test_run_syntax_mode_counts_valid_invalid_and_unchecked(tmp_path, capsys):
    markdown_file = tmp_path / "chapter.md"
    markdown_file.write_text(
        "# Title\n\n"
        "```python\n"
        "print('ok')\n"
        "```\n\n"
        "```python\n"
        "def broken(\n"
        "```\n\n"
        "```mermaid\n"
        "graph TD\n"
        "```\n",
        encoding="utf-8",
    )

    validate_code.run_syntax_mode(str(markdown_file))
    result = json.loads(capsys.readouterr().out)

    assert result["file"] == "chapter.md"
    assert result["total_blocks"] == 3
    assert result["valid"] == 1
    assert result["invalid"] == 1
    assert result["unchecked"] == 1
    assert result["errors"][0]["language"] == "python"
    assert "SyntaxError" in result["errors"][0]["error"]


def test_run_execute_mode_reports_pass_and_output_mismatch(tmp_path, capsys):
    markdown_file = tmp_path / "chapter.md"
    markdown_file.write_text(
        "```python:runnable\n"
        "print('alpha')\n"
        "# Expected output: alpha\n"
        "```\n\n"
        "```python:runnable\n"
        "print('beta')\n"
        "# Expected output: gamma\n"
        "```\n",
        encoding="utf-8",
    )

    validate_code.run_execute_mode(
        str(markdown_file),
        sandbox_mode="process",
        allow_unsafe_process=True,
    )
    result = json.loads(capsys.readouterr().out)

    assert result["total_runnable"] == 2
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["results"][1]["status"] == "failed"
    assert "Output mismatch" in result["results"][1]["error"]


def test_run_execute_mode_directory_returns_results_for_each_file(tmp_path, capsys):
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "ch02_second.md").write_text(
        "```python:runnable\nprint('two')\n# Expected output: two\n```\n",
        encoding="utf-8",
    )
    (chapters_dir / "ch01_first.md").write_text(
        "```python:runnable\nprint('one')\n# Expected output: one\n```\n",
        encoding="utf-8",
    )

    validate_code.run_execute_mode(
        str(chapters_dir),
        sandbox_mode="process",
        allow_unsafe_process=True,
    )
    result = json.loads(capsys.readouterr().out)

    assert isinstance(result, list)
    assert [entry["file"] for entry in result] == ["ch01_first.md", "ch02_second.md"]
    assert all(entry["passed"] == 1 for entry in result)


def test_execute_block_skips_unknown_languages():
    result = validate_code.execute_block("SELECT 1;", "sql")

    assert result == {"status": "skipped", "reason": "No executor for sql"}


def test_execute_block_reports_static_network_lint_failure():
    result = validate_code.execute_block(
        "import urllib.request\nprint('x')",
        "python",
        sandbox_mode="process",
        allow_unsafe_process=True,
    )

    assert result["status"] == "failed"
    assert result["sandbox"]["network_access"] == "blocked_by_static_lint"
    assert "Network usage is not allowed" in result["error"]
