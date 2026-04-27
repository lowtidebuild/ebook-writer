#!/usr/bin/env python3
"""Utilities for v4 ebook pipeline state files."""

from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 4
STEP_ORDER = (
    "research",
    "outline",
    "chapter_writing",
    "editing",
    "image_generation",
    "translation",
    "pdf_typesetting",
    "web_viewer",
)
STEP_OUTPUTS = {
    "research": {
        "research_report": "output/research/research_report.md",
        "verification_report": "output/research/verification_report.json",
        "citations": "output/research/citations.json",
    },
    "outline": {
        "outline_json": "output/outline/outline.json",
        "table_of_contents": "output/outline/table_of_contents.md",
    },
    "chapter_writing": {"directory": "output/chapters/{primary_language}/"},
    "editing": {"edit_report": "output/edit/edit_report.md"},
    "image_generation": {"directory": "output/images/"},
    "translation": {"directory": "output/chapters/{secondary_language}/"},
    "pdf_typesetting": {"directory": "output/final/"},
    "web_viewer": {"directory": "output/web-viewer/"},
}
LEGACY_STEP_MAP = {
    "step_1": "research",
    "step_2": "outline",
    "step_3": "chapter_writing",
    "step_4": "editing",
    "step_5": "image_generation",
    "step_6": "translation",
    "step_7": "pdf_typesetting",
    "step_8": "web_viewer",
}
VALID_STATUSES = {"pending", "running", "completed", "skipped", "failed", "blocked"}
VALID_GATE_STATUSES = {"pending", "approved", "rejected"}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _step_template(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "pending",
        "outputs": deepcopy(STEP_OUTPUTS[name]),
        "retry_count": 0,
        "completed_at": None,
        "error": None,
    }


def create_initial_state(
    topic: str,
    author: str,
    plugin: str | None = None,
    primary_language: str = "ko",
    secondary_language: str = "en",
    bilingual: bool = False,
    now: str | None = None,
) -> dict[str, Any]:
    """Create a fresh v4 pipeline state object."""
    timestamp = now or iso_now()
    steps = {step: _step_template(step) for step in STEP_ORDER}
    if not bilingual:
        steps["translation"]["status"] = "skipped"

    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline": "generate",
        "topic": topic,
        "author": author,
        "plugin": plugin,
        "primary_language": primary_language,
        "secondary_language": secondary_language,
        "bilingual": bilingual,
        "started_at": timestamp,
        "updated_at": timestamp,
        "current_step": "research",
        "last_completed_step": None,
        "chapters": [],
        "steps": steps,
        "gates": {
            "outline": {"status": "pending", "feedback": None},
            "final": {"status": "pending", "feedback": None},
        },
    }


def infer_bilingual(state: dict[str, Any]) -> bool:
    """Infer bilingual mode from v4 or legacy state."""
    if "bilingual" in state:
        return bool(state["bilingual"])

    legacy_translation = state.get("step_artifacts", {}).get("step_6", {})
    return legacy_translation.get("status") == "completed"


def _legacy_current_step(value: Any) -> str:
    if isinstance(value, str):
        if value in STEP_ORDER:
            return value
        if value in LEGACY_STEP_MAP:
            return LEGACY_STEP_MAP[value]
    if isinstance(value, int) and 1 <= value <= len(STEP_ORDER):
        return STEP_ORDER[value - 1]
    return STEP_ORDER[0]


def _legacy_last_completed_step(value: Any) -> str | None:
    if isinstance(value, str):
        if value in STEP_ORDER:
            return value
        if value in LEGACY_STEP_MAP:
            return LEGACY_STEP_MAP[value]
    if isinstance(value, int) and 1 <= value <= len(STEP_ORDER):
        return STEP_ORDER[value - 1]
    return None


def _legacy_step_to_v4(name: str, legacy: dict[str, Any]) -> dict[str, Any]:
    step = _step_template(name)
    status = legacy.get("status", "pending")
    step["status"] = status if status in VALID_STATUSES else "pending"
    step["retry_count"] = legacy.get("retry_count", 0)
    step["completed_at"] = legacy.get("completed_at")

    outputs = deepcopy(STEP_OUTPUTS[name])
    output = legacy.get("output")
    if isinstance(output, str):
        outputs["primary"] = output
    for legacy_key, output_key in (
        ("verification_output", "verification_report"),
        ("citations_output", "citations"),
    ):
        value = legacy.get(legacy_key)
        if isinstance(value, str):
            outputs[output_key] = value
    step["outputs"] = outputs

    if "verification_rate" in legacy:
        step["verification_rate"] = legacy.get("verification_rate")
    if "quality_review_status" in legacy:
        step["quality_review_status"] = legacy.get("quality_review_status")
    if "avg_quality_score" in legacy:
        step["avg_quality_score"] = legacy.get("avg_quality_score")
    return step


def migrate_state(
    raw_state: dict[str, Any],
    default_author: str = "Unknown Author",
    now: str | None = None,
) -> dict[str, Any]:
    """Return a v4-compatible copy of a legacy or partial state object."""
    timestamp = now or iso_now()
    if raw_state.get("schema_version") == SCHEMA_VERSION:
        state = deepcopy(raw_state)
        state.setdefault("author", default_author)
        state.setdefault("bilingual", infer_bilingual(state))
        steps = state.setdefault("steps", {})
        if isinstance(steps, dict):
            for step_name in STEP_ORDER:
                steps.setdefault(step_name, _step_template(step_name))
        gates = state.setdefault("gates", {})
        if isinstance(gates, dict):
            gates.setdefault("outline", {"status": "pending", "feedback": None})
            gates.setdefault("final", {"status": "pending", "feedback": None})
        state.setdefault("current_step", "research")
        state.setdefault("last_completed_step", None)
        state["updated_at"] = state.get("updated_at") or timestamp
        if (
            not state["bilingual"]
            and isinstance(state.get("steps"), dict)
            and isinstance(state["steps"].get("translation"), dict)
            and state["steps"]["translation"].get("status") == "pending"
        ):
            state["steps"]["translation"]["status"] = "skipped"
        return state

    migrated = create_initial_state(
        topic=str(raw_state.get("topic", "")),
        author=str(raw_state.get("author") or default_author),
        plugin=raw_state.get("plugin"),
        primary_language=raw_state.get("primary_language", "ko"),
        secondary_language=raw_state.get("secondary_language", "en"),
        bilingual=infer_bilingual(raw_state),
        now=raw_state.get("started_at") or timestamp,
    )
    migrated["updated_at"] = raw_state.get("updated_at") or timestamp
    migrated["current_step"] = _legacy_current_step(raw_state.get("current_step"))
    migrated["last_completed_step"] = _legacy_last_completed_step(
        raw_state.get("last_completed_step")
    )
    migrated["chapters"] = deepcopy(raw_state.get("chapters", []))
    migrated["gates"] = {
        "outline": {
            "status": raw_state.get("gate1_status", "pending"),
            "feedback": raw_state.get("gate1_feedback"),
        },
        "final": {
            "status": raw_state.get("gate2_status", "pending"),
            "feedback": raw_state.get("gate2_feedback"),
        },
    }

    legacy_steps = raw_state.get("step_artifacts", {})
    for legacy_key, step_name in LEGACY_STEP_MAP.items():
        if isinstance(legacy_steps.get(legacy_key), dict):
            migrated["steps"][step_name] = _legacy_step_to_v4(
                step_name, legacy_steps[legacy_key]
            )

    if not migrated["bilingual"] and migrated["steps"]["translation"]["status"] == "pending":
        migrated["steps"]["translation"]["status"] = "skipped"
    return migrated


def validate_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if state.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 4")
    if state.get("pipeline") != "generate":
        errors.append('pipeline must be "generate"')
    if not state.get("topic"):
        errors.append("topic is required")
    if not state.get("author"):
        errors.append("author is required")

    current_step = state.get("current_step")
    if current_step not in STEP_ORDER:
        errors.append(f"current_step must be one of {', '.join(STEP_ORDER)}")

    steps = state.get("steps")
    if not isinstance(steps, dict):
        errors.append("steps must be an object")
    else:
        for name in STEP_ORDER:
            step = steps.get(name)
            if not isinstance(step, dict):
                errors.append(f"steps.{name} is required")
                continue
            if step.get("status") not in VALID_STATUSES:
                errors.append(f"steps.{name}.status is invalid")

    gates = state.get("gates")
    if not isinstance(gates, dict):
        errors.append("gates must be an object")
    else:
        for gate_name in ("outline", "final"):
            gate = gates.get(gate_name)
            if not isinstance(gate, dict):
                errors.append(f"gates.{gate_name} is required")
                continue
            if gate.get("status") not in VALID_GATE_STATUSES:
                errors.append(f"gates.{gate_name}.status is invalid")

    return errors


def backup_and_migrate_state_file(
    path: str | Path,
    default_author: str = "Unknown Author",
) -> dict[str, Any]:
    """Back up a state file and replace it with v4 JSON."""
    state_path = Path(path)
    raw_state = json.loads(state_path.read_text(encoding="utf-8"))
    migrated = migrate_state(raw_state, default_author=default_author)
    errors = validate_state(migrated)
    if errors:
        raise ValueError("Invalid migrated state: " + "; ".join(errors))

    old_version = raw_state.get("schema_version", "legacy")
    backup_path = state_path.with_name(f"{state_path.stem}.v{old_version}.backup.json")
    backup_path.write_text(
        json.dumps(raw_state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    temp_path = state_path.with_suffix(state_path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(migrated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, state_path)
    return migrated


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage ebook pipeline state files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a new v4 state file.")
    init_parser.add_argument("--topic", required=True)
    init_parser.add_argument("--author", required=True)
    init_parser.add_argument("--plugin")
    init_parser.add_argument("--primary-language", default="ko")
    init_parser.add_argument("--secondary-language", default="en")
    init_parser.add_argument("--bilingual", action="store_true")
    init_parser.add_argument("--output", default="output/pipeline_state.json")

    migrate_parser = subparsers.add_parser("migrate", help="Migrate an existing state file.")
    migrate_parser.add_argument("path", nargs="?", default="output/pipeline_state.json")
    migrate_parser.add_argument("--default-author", default="Unknown Author")

    validate_parser = subparsers.add_parser("validate", help="Validate a v4 state file.")
    validate_parser.add_argument("path", nargs="?", default="output/pipeline_state.json")

    args = parser.parse_args()
    if args.command == "init":
        state = create_initial_state(
            topic=args.topic,
            author=args.author,
            plugin=args.plugin,
            primary_language=args.primary_language,
            secondary_language=args.secondary_language,
            bilingual=args.bilingual,
        )
        _write_json(Path(args.output), state)
        print(json.dumps({"status": "created", "path": args.output}, ensure_ascii=False))
        return 0

    if args.command == "migrate":
        migrated = backup_and_migrate_state_file(args.path, default_author=args.default_author)
        print(
            json.dumps(
                {
                    "status": "migrated",
                    "path": args.path,
                    "schema_version": migrated["schema_version"],
                },
                ensure_ascii=False,
            )
        )
        return 0

    state = json.loads(Path(args.path).read_text(encoding="utf-8"))
    errors = validate_state(state)
    print(
        json.dumps(
            {"status": "failed" if errors else "passed", "errors": errors},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
