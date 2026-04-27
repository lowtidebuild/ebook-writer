#!/usr/bin/env python3
"""Validate chapter Markdown before final artifact generation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from preflight_utils import (
    chapter_files,
    chapter_number,
    dangerous_text_issues,
    footnote_info,
    headings,
    issue,
    load_citation_ids,
    result_payload,
    write_json,
)


KO_H1_RE = re.compile(r"^#\s+제(\d+)장[:：]\s+\S")
EN_H1_RE = re.compile(r"^#\s+Chapter\s+(\d+)[:：]\s+\S", re.IGNORECASE)


def validate_heading_structure(path: Path, text: str, language: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    file_label = str(path)
    found = headings(text)
    h1_headings = [heading for heading in found if heading["level"] == 1]
    expected_number = chapter_number(path)

    if len(h1_headings) != 1:
        issues.append(
            issue(
                "h1_count",
                f"Expected exactly one H1, found {len(h1_headings)}",
                file=file_label,
            )
        )
    elif expected_number is not None:
        h1_line = text.splitlines()[h1_headings[0]["line"] - 1].strip()
        pattern = KO_H1_RE if language == "ko" else EN_H1_RE
        match = pattern.match(h1_line)
        if not match:
            expected = "# 제N장: 제목" if language == "ko" else "# Chapter N: Title"
            issues.append(
                issue(
                    "h1_format",
                    f"H1 must match language format: {expected}",
                    file=file_label,
                    line=h1_headings[0]["line"],
                )
            )
        elif int(match.group(1)) != expected_number:
            issues.append(
                issue(
                    "h1_number_mismatch",
                    "H1 chapter number does not match chapter filename",
                    file=file_label,
                    line=h1_headings[0]["line"],
                    expected=expected_number,
                    actual=int(match.group(1)),
                )
            )

    previous_level = 0
    for heading in found:
        level = heading["level"]
        if previous_level and level > previous_level + 1:
            issues.append(
                issue(
                    "heading_level_skip",
                    f"Heading level jumps from H{previous_level} to H{level}",
                    file=file_label,
                    line=heading["line"],
                )
            )
        previous_level = level

    return issues


def validate_footnotes(
    path: Path,
    text: str,
    citation_ids: set[str] | None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    info = footnote_info(text)
    marker_ids = set(info["marker_ids"])
    definitions = info["definitions"]
    file_label = str(path)

    for marker_id, line_number in info["marker_lines"]:
        if marker_id not in definitions:
            issues.append(
                issue(
                    "missing_footnote_definition",
                    f"Footnote marker [^{marker_id}] has no matching definition",
                    file=file_label,
                    line=line_number,
                    footnote_id=marker_id,
                )
            )
        if citation_ids is not None and marker_id not in citation_ids:
            issues.append(
                issue(
                    "unknown_citation_id",
                    f"Footnote marker [^{marker_id}] does not exist in citations.json",
                    file=file_label,
                    line=line_number,
                    footnote_id=marker_id,
                )
            )

    for definition_id, lines in definitions.items():
        if len(lines) > 1:
            issues.append(
                issue(
                    "duplicate_footnote_definition",
                    f"Footnote definition [^{definition_id}] appears more than once",
                    file=file_label,
                    line=lines[1],
                    footnote_id=definition_id,
                )
            )
        if definition_id not in marker_ids:
            issues.append(
                issue(
                    "orphan_footnote_definition",
                    f"Footnote definition [^{definition_id}] has no marker in the chapter body",
                    severity="warning",
                    file=file_label,
                    line=lines[0],
                    footnote_id=definition_id,
                )
            )

    return issues


def validate_chapter_file(
    path: Path,
    language: str,
    citation_ids: set[str] | None,
) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    issues = validate_heading_structure(path, text, language)
    issues.extend(dangerous_text_issues(text, str(path)))
    issues.extend(validate_footnotes(path, text, citation_ids))
    return issues


def validate_chapters(
    chapters_dir: str | Path,
    language: str,
    citations_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(chapters_dir)
    issues: list[dict[str, Any]] = []
    files = chapter_files(root) if root.is_dir() else []

    if not root.is_dir():
        issues.append(issue("missing_chapters_dir", f"Chapter directory not found: {root}"))
    elif not files:
        issues.append(issue("no_chapters", f"No chapter markdown files found in {root}"))

    citation_ids = load_citation_ids(citations_path)
    for path in files:
        issues.extend(validate_chapter_file(path, language, citation_ids))

    return result_payload(
        "validate_chapters",
        issues,
        chapters_dir=str(root),
        language=language,
        files_checked=len(files),
        citations_path=str(citations_path) if citations_path else None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate generated chapter Markdown.")
    parser.add_argument("chapters_dir")
    parser.add_argument("--language", required=True, choices=["ko", "en"])
    parser.add_argument("--citations")
    parser.add_argument("--output", help="Optional JSON log output path.")
    args = parser.parse_args(argv)

    payload = validate_chapters(args.chapters_dir, args.language, args.citations)
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
