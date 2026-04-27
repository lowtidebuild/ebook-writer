from __future__ import annotations

from helpers import load_module


validate_translations = load_module("validate_translations_module", "scripts/validate_translations.py")


def write_pair(primary_dir, secondary_dir, secondary_body: str) -> None:
    primary_dir.mkdir()
    secondary_dir.mkdir()
    (primary_dir / "ch01_intro.md").write_text(
        "# 제1장: 소개\n\n"
        "본문입니다.[^1]\n\n"
        "## 코드\n\n"
        "```python\nprint('hi')\n```\n\n"
        "![다이어그램](../../images/a.svg)\n\n"
        "https://example.com\n\n"
        "[^1]: 출처\n",
        encoding="utf-8",
    )
    (secondary_dir / "ch01_intro.md").write_text(secondary_body, encoding="utf-8")


def test_validate_translations_passes_matching_structure(tmp_path) -> None:
    primary = tmp_path / "ko"
    secondary = tmp_path / "en"
    write_pair(
        primary,
        secondary,
        "# Chapter 1: Introduction\n\n"
        "Body.[^1]\n\n"
        "## Code\n\n"
        "```python\nprint('hi')\n```\n\n"
        "![Diagram](../../images/a.svg)\n\n"
        "https://example.com\n\n"
        "[^1]: Source\n",
    )

    result = validate_translations.validate_translations(primary, secondary)

    assert result["status"] == "passed"


def test_validate_translations_blocks_structural_mismatch(tmp_path) -> None:
    primary = tmp_path / "ko"
    secondary = tmp_path / "en"
    write_pair(
        primary,
        secondary,
        "# Chapter 1: Introduction\n\n"
        "Body.\n\n"
        "### Skipped heading\n\n"
        "```javascript\nconsole.log('hi')\n```\n\n",
    )

    result = validate_translations.validate_translations(primary, secondary)
    codes = {issue["code"] for issue in result["issues"]}

    assert result["status"] == "failed"
    assert "heading_structure_mismatch" in codes
    assert "code_block_structure_mismatch" in codes
    assert "image_reference_count_mismatch" in codes
    assert "footnote_marker_mismatch" in codes
    assert "url_not_preserved" in codes
