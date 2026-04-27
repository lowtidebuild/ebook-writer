#!/usr/bin/env python3
"""Validate image manifest consistency before final review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from preflight_utils import issue, load_json, result_payload, write_json


VALID_STATUSES = {"pending", "completed", "failed", "skipped"}
VALID_PROVIDERS = {"diagram", "gemini", "openai", "codex", None}
RASTER_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def manifest_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        for key in ("images", "entries", "manifest"):
            value = payload.get(key)
            if isinstance(value, list):
                return [entry for entry in value if isinstance(entry, dict)]
    return []


def validate_image_format(path: Path) -> str | None:
    suffix = path.suffix.lower()
    data = path.read_bytes()
    if suffix == ".svg":
        text = data.decode("utf-8", errors="ignore").lstrip()
        return None if "<svg" in text[:300].lower() else "SVG file does not contain an <svg> root"
    if suffix == ".png":
        return None if data.startswith(b"\x89PNG\r\n\x1a\n") else "PNG signature is invalid"
    if suffix in {".jpg", ".jpeg"}:
        return None if data.startswith(b"\xff\xd8") else "JPEG signature is invalid"
    if suffix == ".webp":
        return None if data.startswith(b"RIFF") and b"WEBP" in data[:16] else "WEBP signature is invalid"
    return f"Unsupported image extension: {suffix}"


def validate_entry(
    entry: dict[str, Any],
    index: int,
    manifest_dir: Path,
    allow_failed: bool,
    allow_pending: bool,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    label = entry.get("marker_id") or f"entry[{index}]"

    for field in ("marker_id", "chapter_file", "description", "status"):
        if not entry.get(field):
            issues.append(issue("missing_image_manifest_field", f"{field} is required", file=label))

    status = entry.get("status")
    if status not in VALID_STATUSES:
        issues.append(issue("invalid_image_status", f"Invalid image status: {status!r}", file=label))

    provider = entry.get("provider")
    if provider not in VALID_PROVIDERS:
        issues.append(issue("invalid_image_provider", f"Invalid image provider: {provider!r}", file=label))

    output_path_value = entry.get("output_path")
    output_path = None
    if output_path_value:
        output_path = Path(output_path_value)
        if not output_path.is_absolute():
            output_path = (manifest_dir.parent / output_path).resolve()
            if not output_path.exists():
                output_path = Path(output_path_value)
    elif status == "completed":
        issues.append(issue("missing_image_output_path", "Completed image entry has no output_path", file=label))

    if output_path is not None and provider == "diagram" and output_path.suffix.lower() != ".svg":
        issues.append(
            issue(
                "diagram_extension_mismatch",
                "Diagram provider output should be an SVG file",
                file=label,
                output_path=str(output_path_value),
            )
        )
    elif output_path is not None and provider in {"gemini", "openai", "codex"}:
        if output_path.suffix.lower() not in RASTER_SUFFIXES:
            issues.append(
                issue(
                    "model_image_extension_mismatch",
                    "Model image provider output should be a raster image",
                    file=label,
                    output_path=str(output_path_value),
                )
            )

    chapter_file = entry.get("chapter_file")
    if isinstance(chapter_file, str) and not Path(chapter_file).is_file():
        issues.append(issue("missing_image_chapter_file", "Manifest chapter_file does not exist", file=label, chapter_file=chapter_file))

    if status == "completed" and output_path is not None:
        if not output_path.is_file():
            issues.append(issue("missing_completed_image", "Completed image file does not exist", file=label, output_path=str(output_path_value)))
        elif output_path.stat().st_size == 0:
            issues.append(issue("empty_completed_image", "Completed image file is empty", file=label, output_path=str(output_path_value)))
        else:
            format_error = validate_image_format(output_path)
            if format_error:
                issues.append(issue("invalid_image_format", format_error, file=label, output_path=str(output_path_value)))

    if status == "failed" and not allow_failed:
        issues.append(issue("failed_image_entry", "Failed image entry blocks final review", file=label))
    if status == "pending" and not allow_pending:
        issues.append(issue("pending_image_entry", "Pending image entry blocks final review", file=label))

    return issues


def validate_images(
    manifest_path: str | Path,
    allow_failed: bool = False,
    allow_pending: bool = False,
) -> dict[str, Any]:
    path = Path(manifest_path)
    issues: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []

    if not path.is_file():
        issues.append(issue("missing_image_manifest", f"Image manifest not found: {path}"))
    else:
        entries = manifest_entries(load_json(path))
        if not entries:
            issues.append(issue("empty_image_manifest", "Image manifest contains no entries", severity="warning"))

    seen_keys: set[tuple[Any, Any, Any]] = set()
    seen_marker_ids: set[str] = set()
    for index, entry in enumerate(entries):
        marker_id = entry.get("marker_id")
        if isinstance(marker_id, str):
            if marker_id in seen_marker_ids:
                issues.append(issue("duplicate_marker_id", f"Duplicate marker_id: {marker_id}", file=marker_id))
            seen_marker_ids.add(marker_id)

        unique_key = (entry.get("chapter_file"), entry.get("line_number"), marker_id)
        if unique_key in seen_keys:
            issues.append(issue("duplicate_manifest_location", "Duplicate chapter/line/marker entry", file=str(marker_id)))
        seen_keys.add(unique_key)
        issues.extend(validate_entry(entry, index, path.parent, allow_failed, allow_pending))

    return result_payload(
        "validate_images",
        issues,
        manifest_path=str(path),
        entries_checked=len(entries),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate image manifest entries.")
    parser.add_argument("manifest_path")
    parser.add_argument("--allow-failed", action="store_true")
    parser.add_argument("--allow-pending", action="store_true")
    parser.add_argument("--output", help="Optional JSON log output path.")
    args = parser.parse_args(argv)

    payload = validate_images(args.manifest_path, args.allow_failed, args.allow_pending)
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
