from __future__ import annotations

import json

from helpers import load_module


validate_chapters = load_module("validate_chapters_module", "scripts/validate_chapters.py")


def test_validate_chapters_passes_valid_korean_chapter(tmp_path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    (chapters / "ch01_intro.md").write_text(
        "# 제1장: 시작하기\n\n"
        "본문입니다.[^1]\n\n"
        "## 배경\n\n"
        "설명입니다.\n\n"
        "[^1]: 참고문헌 항목\n",
        encoding="utf-8",
    )
    citations = tmp_path / "citations.json"
    citations.write_text(json.dumps({"citations": [{"id": 1, "title": "Source"}]}), encoding="utf-8")

    result = validate_chapters.validate_chapters(chapters, "ko", citations)

    assert result["status"] == "passed"
    assert result["error_count"] == 0


def test_validate_chapters_blocks_heading_skip_and_image_failure_placeholder(tmp_path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    (chapters / "ch01_intro.md").write_text(
        "# 제1장: 시작하기\n\n"
        "본문입니다.[^99]\n\n"
        "### 너무 깊은 제목\n\n"
        "> [이미지 생성 실패] 그림\n\n",
        encoding="utf-8",
    )
    citations = tmp_path / "citations.json"
    citations.write_text(json.dumps({"citations": [{"id": 1, "title": "Source"}]}), encoding="utf-8")

    result = validate_chapters.validate_chapters(chapters, "ko", citations)
    codes = {issue["code"] for issue in result["issues"]}

    assert result["status"] == "failed"
    assert "heading_level_skip" in codes
    assert "forbidden_text" in codes
    assert "missing_footnote_definition" in codes
    assert "unknown_citation_id" in codes


def test_validate_chapters_warns_on_orphan_footnote_definition(tmp_path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    (chapters / "ch01_intro.md").write_text(
        "# Chapter 1: Intro\n\n"
        "Body.\n\n"
        "[^1]: Orphan source\n",
        encoding="utf-8",
    )

    result = validate_chapters.validate_chapters(chapters, "en")

    assert result["status"] == "passed"
    assert result["warning_count"] == 1
    assert result["issues"][0]["code"] == "orphan_footnote_definition"
