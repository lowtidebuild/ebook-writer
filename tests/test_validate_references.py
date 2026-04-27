from __future__ import annotations

import json

from helpers import load_module


validate_references = load_module(
    "test_validate_references_module",
    ".claude/skills/code-example-validator/scripts/validate_references.py",
)


def test_main_detects_missing_chapters_and_ignores_code_blocks(tmp_path, capsys):
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "ch01_intro.md").write_text(
        "# 제1장: 소개\n"
        "2장과 3장을 비교합니다.\n"
        "[IMAGE: 9장 비교 도식]\n"
        "[^5]: 참고자료 8장 언급\n"
        "```python\n"
        "print('4장')\n"
        "```\n",
        encoding="utf-8",
    )
    (chapters_dir / "ch02_next.md").write_text("# 제2장: 다음 장\n", encoding="utf-8")

    validate_references.main([str(chapters_dir)])
    result = json.loads(capsys.readouterr().out)

    assert result["chapter_references"]["total"] == 2
    assert result["chapter_references"]["valid"] == 1
    assert result["chapter_references"]["invalid"] == 1
    assert result["citation_references"]["total"] == 0
    assert result["errors"][0]["reference"] == "3장"


def test_main_validates_citation_ids_against_explicit_citations_file(tmp_path, capsys):
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    citations_path = tmp_path / "citations.json"
    citations_path.write_text(
        json.dumps({"citations": [{"id": 1}, {"id": "3"}]}),
        encoding="utf-8",
    )
    (chapters_dir / "ch01_intro.md").write_text(
        "# 제1장: 소개\n"
        "검증된 사실입니다[^1].\n"
        "누락된 인용입니다[^2].\n"
        "[^2]: 정의 줄은 중복 집계하지 않습니다.\n"
        "```python\n"
        "print('ignore [^99] in code')\n"
        "```\n",
        encoding="utf-8",
    )

    validate_references.main([str(chapters_dir), "--citations", str(citations_path)])
    result = json.loads(capsys.readouterr().out)

    assert result["citation_references"]["total"] == 2
    assert result["citation_references"]["valid"] == 1
    assert result["citation_references"]["invalid"] == 1
    assert result["errors"][0]["reference_type"] == "citation"
    assert result["errors"][0]["citation_id"] == 2


def test_main_auto_detects_citations_json_in_output_layout(tmp_path, capsys):
    output_dir = tmp_path / "output"
    chapters_dir = output_dir / "chapters" / "ko"
    research_dir = output_dir / "research"
    chapters_dir.mkdir(parents=True)
    research_dir.mkdir(parents=True)
    (research_dir / "citations.json").write_text(
        json.dumps({"citations": [{"id": 1}]}),
        encoding="utf-8",
    )
    (chapters_dir / "ch01_intro.md").write_text(
        "# 제1장: 소개\n"
        "자동 탐지 테스트[^1].\n",
        encoding="utf-8",
    )

    validate_references.main([str(chapters_dir)])
    result = json.loads(capsys.readouterr().out)

    assert result["citation_references"]["total"] == 1
    assert result["citation_references"]["invalid"] == 0
    assert result["citation_references"]["citations_path"] == str(research_dir / "citations.json")


def test_main_returns_zero_counts_when_no_chapters_exist(tmp_path, capsys):
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()

    validate_references.main([str(chapters_dir)])
    result = json.loads(capsys.readouterr().out)

    assert result["total_references"] == 0
    assert result["invalid"] == 0
    assert result["errors"] == []
