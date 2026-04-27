#!/usr/bin/env python3
"""Validate structural correspondence between primary and translated chapters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from preflight_utils import (
    chapter_files,
    chapter_number,
    code_fence_languages,
    dangerous_text_issues,
    footnote_info,
    headings,
    image_reference_count,
    issue,
    result_payload,
    urls,
    write_json,
)


def chapter_map(directory: str | Path) -> dict[int, Path]:
    mapping: dict[int, Path] = {}
    for path in chapter_files(directory):
        number = chapter_number(path)
        if number is not None:
            mapping[number] = path
    return mapping


def heading_levels(text: str) -> list[int]:
    return [heading["level"] for heading in headings(text)]


def compare_chapter_pair(primary_path: Path, secondary_path: Path) -> list[dict[str, Any]]:
    primary_text = primary_path.read_text(encoding="utf-8")
    secondary_text = secondary_path.read_text(encoding="utf-8")
    issues: list[dict[str, Any]] = []
    pair = f"{primary_path.name} -> {secondary_path.name}"

    primary_heading_levels = heading_levels(primary_text)
    secondary_heading_levels = heading_levels(secondary_text)
    if primary_heading_levels != secondary_heading_levels:
        issues.append(
            issue(
                "heading_structure_mismatch",
                "Primary and secondary heading levels differ",
                file=pair,
                primary=primary_heading_levels,
                secondary=secondary_heading_levels,
            )
        )

    primary_code_langs = code_fence_languages(primary_text)
    secondary_code_langs = code_fence_languages(secondary_text)
    if primary_code_langs != secondary_code_langs:
        issues.append(
            issue(
                "code_block_structure_mismatch",
                "Primary and secondary code fence languages/counts differ",
                file=pair,
                primary=primary_code_langs,
                secondary=secondary_code_langs,
            )
        )

    primary_image_count = image_reference_count(primary_text)
    secondary_image_count = image_reference_count(secondary_text)
    if primary_image_count != secondary_image_count:
        issues.append(
            issue(
                "image_reference_count_mismatch",
                "Primary and secondary image reference counts differ",
                file=pair,
                primary=primary_image_count,
                secondary=secondary_image_count,
            )
        )

    primary_footnotes = footnote_info(primary_text)["marker_counts"]
    secondary_footnotes = footnote_info(secondary_text)["marker_counts"]
    if primary_footnotes != secondary_footnotes:
        issues.append(
            issue(
                "footnote_marker_mismatch",
                "Primary and secondary footnote marker IDs/counts differ",
                file=pair,
                primary=dict(primary_footnotes),
                secondary=dict(secondary_footnotes),
            )
        )

    missing_urls = sorted(set(urls(primary_text)) - set(urls(secondary_text)))
    if missing_urls:
        issues.append(
            issue(
                "url_not_preserved",
                "Secondary chapter does not preserve all source URLs",
                file=pair,
                urls=missing_urls,
            )
        )

    issues.extend(dangerous_text_issues(secondary_text, str(secondary_path)))
    return issues


def validate_translations(
    primary_dir: str | Path,
    secondary_dir: str | Path,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    primary_root = Path(primary_dir)
    secondary_root = Path(secondary_dir)

    if not primary_root.is_dir():
        issues.append(issue("missing_primary_dir", f"Primary chapter directory not found: {primary_root}"))
        primary = {}
    else:
        primary = chapter_map(primary_root)

    if not secondary_root.is_dir():
        issues.append(issue("missing_secondary_dir", f"Secondary chapter directory not found: {secondary_root}"))
        secondary = {}
    else:
        secondary = chapter_map(secondary_root)

    primary_numbers = set(primary)
    secondary_numbers = set(secondary)
    for missing in sorted(primary_numbers - secondary_numbers):
        issues.append(
            issue(
                "missing_secondary_chapter",
                f"Secondary chapter for Chapter {missing} is missing",
                chapter_id=missing,
            )
        )
    for extra in sorted(secondary_numbers - primary_numbers):
        issues.append(
            issue(
                "extra_secondary_chapter",
                f"Secondary chapter {extra} has no primary counterpart",
                chapter_id=extra,
            )
        )

    for number in sorted(primary_numbers & secondary_numbers):
        issues.extend(compare_chapter_pair(primary[number], secondary[number]))

    return result_payload(
        "validate_translations",
        issues,
        primary_dir=str(primary_root),
        secondary_dir=str(secondary_root),
        primary_chapters=len(primary),
        secondary_chapters=len(secondary),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate translated chapter structure.")
    parser.add_argument("primary_dir")
    parser.add_argument("secondary_dir")
    parser.add_argument("--output", help="Optional JSON log output path.")
    args = parser.parse_args(argv)

    payload = validate_translations(args.primary_dir, args.secondary_dir)
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
