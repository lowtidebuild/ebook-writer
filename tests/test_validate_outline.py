from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from helpers import REPO_ROOT, load_module


outline_utils = load_module("outline_utils", "scripts/outline_utils.py")


def valid_outline() -> dict:
    return {
        "book_title": "실전 AI 업무 자동화",
        "target_audience": "AI 도구를 업무에 적용하려는 실무자",
        "language": "ko",
        "chapters": [
            {
                "chapter_id": 1,
                "slug": "foundations",
                "title": "기초 다지기",
                "summary": "업무 자동화에 필요한 기본 개념을 설명한다.",
                "key_content": ["자동화 범위 정의", "도구 선택 기준"],
                "estimated_words": 2500,
                "dependencies": [],
            },
            {
                "chapter_id": 2,
                "slug": "workflow-design",
                "title": "워크플로 설계",
                "summary": "반복 업무를 안정적인 워크플로로 바꾸는 방법을 다룬다.",
                "key_content": ["입출력 정의", "검증 단계 설계"],
                "estimated_words": 3000,
                "dependencies": [1],
            },
            {
                "chapter_id": 3,
                "slug": "operations",
                "title": "운영과 개선",
                "summary": "운영 중 품질을 추적하고 개선하는 방법을 설명한다.",
                "key_content": ["품질 지표", "회귀 테스트"],
                "estimated_words": 3200,
                "dependencies": [1, 2],
            },
        ],
    }


def test_valid_outline_renders_markdown_and_waves() -> None:
    outline = valid_outline()

    assert outline_utils.validate_outline(outline) == []
    assert outline_utils.dependency_waves(outline) == [[1], [2], [3]]

    markdown = outline_utils.render_outline_markdown(outline)
    assert "# 실전 AI 업무 자동화" in markdown
    assert "- **Slug**: `workflow-design`" in markdown
    assert "- **Dependencies**: [1, 2]" in markdown


def test_chapter_state_entries_are_execution_ready() -> None:
    entries = outline_utils.chapter_state_entries(valid_outline())

    assert entries == [
        {
            "chapter_id": 1,
            "slug": "foundations",
            "title": "기초 다지기",
            "dependencies": [],
            "write_status": "pending",
        },
        {
            "chapter_id": 2,
            "slug": "workflow-design",
            "title": "워크플로 설계",
            "dependencies": [1],
            "write_status": "pending",
        },
        {
            "chapter_id": 3,
            "slug": "operations",
            "title": "운영과 개선",
            "dependencies": [1, 2],
            "write_status": "pending",
        },
    ]


def test_duplicate_slug_is_invalid() -> None:
    outline = valid_outline()
    outline["chapters"][1]["slug"] = "foundations"

    assert "chapter slugs must be unique" in outline_utils.validate_outline(outline)


def test_missing_dependency_is_invalid() -> None:
    outline = valid_outline()
    outline["chapters"][1]["dependencies"] = [99]

    assert "Chapter 2 depends on missing Chapter 99" in outline_utils.validate_outline(outline)


def test_cycle_error_includes_concrete_path() -> None:
    outline = valid_outline()
    outline["chapters"][0]["dependencies"] = [2]

    errors = outline_utils.validate_outline(outline)

    assert "Dependency cycle detected: Chapter 1 -> Chapter 2 -> Chapter 1" in errors


def test_validate_outline_cli_detects_markdown_mismatch(tmp_path: Path) -> None:
    outline_path = tmp_path / "outline.json"
    markdown_path = tmp_path / "table_of_contents.md"
    outline_path.write_text(json.dumps(valid_outline(), ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text("# stale\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/validate_outline.py"),
            str(outline_path),
            "--markdown",
            str(markdown_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Markdown outline is out of sync" in result.stdout
