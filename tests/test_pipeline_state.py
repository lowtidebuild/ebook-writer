from __future__ import annotations

from pathlib import Path

from helpers import load_module


pipeline_state = load_module("pipeline_state", "scripts/pipeline_state.py")


def test_create_initial_state_uses_v4_named_steps() -> None:
    state = pipeline_state.create_initial_state(
        topic="AI 활용 가이드",
        author="홍길동",
        primary_language="ko",
        secondary_language="en",
        bilingual=False,
        now="2026-04-27T00:00:00+00:00",
    )

    assert state["schema_version"] == 4
    assert state["author"] == "홍길동"
    assert state["current_step"] == "research"
    assert state["last_completed_step"] is None
    assert state["steps"]["outline"]["outputs"]["outline_json"] == "output/outline/outline.json"
    assert state["steps"]["translation"]["status"] == "skipped"
    assert state["gates"]["outline"]["status"] == "pending"
    assert pipeline_state.validate_state(state) == []


def test_migrate_legacy_state_backfills_author_steps_and_gates() -> None:
    legacy = {
        "pipeline": "generate",
        "topic": "Legacy Book",
        "plugin": "legal",
        "primary_language": "ko",
        "secondary_language": "en",
        "started_at": "2026-04-20T00:00:00+00:00",
        "updated_at": "2026-04-21T00:00:00+00:00",
        "current_step": 3,
        "last_completed_step": 2,
        "gate1_status": "rejected",
        "gate1_feedback": "챕터를 줄여주세요.",
        "step_artifacts": {
            "step_2": {
                "name": "outline",
                "status": "completed",
                "output": "output/outline/table_of_contents.md",
                "retry_count": 1,
                "completed_at": "2026-04-21T00:00:00+00:00",
            },
            "step_6": {
                "name": "translation",
                "status": "skipped",
                "output": "output/chapters/en/",
                "retry_count": 0,
                "completed_at": None,
            },
        },
    }

    migrated = pipeline_state.migrate_state(
        legacy,
        default_author="Unknown Author",
        now="2026-04-27T00:00:00+00:00",
    )

    assert migrated["schema_version"] == 4
    assert migrated["author"] == "Unknown Author"
    assert migrated["current_step"] == "chapter_writing"
    assert migrated["last_completed_step"] == "outline"
    assert migrated["steps"]["outline"]["status"] == "completed"
    assert migrated["steps"]["outline"]["outputs"]["primary"] == "output/outline/table_of_contents.md"
    assert migrated["steps"]["translation"]["status"] == "skipped"
    assert migrated["gates"]["outline"]["status"] == "rejected"
    assert migrated["gates"]["outline"]["feedback"] == "챕터를 줄여주세요."
    assert pipeline_state.validate_state(migrated) == []


def test_validate_state_reports_missing_author_and_bad_status() -> None:
    state = pipeline_state.create_initial_state(
        topic="Topic",
        author="Author",
        now="2026-04-27T00:00:00+00:00",
    )
    state["author"] = ""
    state["steps"]["research"]["status"] = "done"

    errors = pipeline_state.validate_state(state)

    assert "author is required" in errors
    assert "steps.research.status is invalid" in errors


def test_migrate_partial_v4_state_fills_missing_defaults() -> None:
    partial = {
        "schema_version": 4,
        "pipeline": "generate",
        "topic": "Partial",
        "author": "Author",
        "primary_language": "ko",
        "secondary_language": "en",
        "bilingual": False,
        "started_at": "2026-04-27T00:00:00+00:00",
        "updated_at": "2026-04-27T00:00:00+00:00",
        "current_step": "research",
        "chapters": [],
        "steps": {"research": pipeline_state._step_template("research")},
        "gates": {},
    }

    migrated = pipeline_state.migrate_state(partial)

    assert "outline" in migrated["steps"]
    assert migrated["steps"]["translation"]["status"] == "skipped"
    assert migrated["gates"]["outline"]["status"] == "pending"
    assert pipeline_state.validate_state(migrated) == []


def test_backup_and_migrate_state_file_writes_backup(tmp_path: Path) -> None:
    state_path = tmp_path / "pipeline_state.json"
    state_path.write_text(
        '{"pipeline":"generate","topic":"Book","current_step":1}',
        encoding="utf-8",
    )

    migrated = pipeline_state.backup_and_migrate_state_file(
        state_path,
        default_author="Migrated Author",
    )

    assert migrated["schema_version"] == 4
    assert migrated["author"] == "Migrated Author"
    assert (tmp_path / "pipeline_state.vlegacy.backup.json").exists()
