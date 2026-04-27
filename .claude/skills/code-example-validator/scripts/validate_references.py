#!/usr/bin/env python3
"""Validate cross-references between chapters in markdown files.

Usage:
    .venv/bin/python3 .claude/skills/code-example-validator/scripts/validate_references.py <chapters_directory>
    .venv/bin/python3 .claude/skills/code-example-validator/scripts/validate_references.py <chapters_directory> --citations <citations.json>

Scans chapter files for references to other chapters and inline citations,
then validates that referenced chapters and citation IDs actually exist.
Output: JSON to stdout
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from markdown_utils import extract_code_block_line_numbers


CHAPTER_FILENAME_PATTERN = re.compile(r"^ch(\d+)_")
KO_CHAPTER_PATTERN = re.compile(r"(\d+)장")
EN_CHAPTER_PATTERN = re.compile(r"Chapter\s+(\d+)", re.IGNORECASE)
FOOTNOTE_DEFINITION_PATTERN = re.compile(r"^\[\^\d+\]:")
CITATION_MARKER_PATTERN = re.compile(r"\[\^(\d+)\]")


def extract_existing_chapters(directory: str) -> set[int]:
    """Extract chapter numbers from filenames in the directory."""
    chapters = set()
    for filename in os.listdir(directory):
        match = CHAPTER_FILENAME_PATTERN.match(filename)
        if match:
            chapters.add(int(match.group(1)))
    return chapters


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Validate chapter cross-references and citation IDs.",
    )
    parser.add_argument("chapters_directory", help="Directory containing chapter markdown files.")
    parser.add_argument(
        "--citations",
        default=None,
        help="Path to citations.json (optional; auto-detected when possible).",
    )
    return parser.parse_args(argv)


def discover_citations_path(chapters_dir: str, citations_arg: str | None = None) -> Path | None:
    """Return the citations path from CLI input or common output layouts."""
    if citations_arg:
        citations_path = Path(citations_arg)
        if not citations_path.is_file():
            raise FileNotFoundError(f"Citations file not found: {citations_arg}")
        return citations_path

    chapters_path = Path(chapters_dir).resolve()
    candidates = [
        chapters_path / "citations.json",
        chapters_path.parent / "citations.json",
        chapters_path.parent / "research" / "citations.json",
        chapters_path.parent.parent / "research" / "citations.json",
    ]

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate

    return None


def load_citation_ids(citations_path: Path | None) -> set[int] | None:
    """Load citation IDs from citations.json."""
    if citations_path is None:
        return None

    with citations_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    citations = data if isinstance(data, list) else data.get("citations", [])
    citation_ids: set[int] = set()
    for citation in citations:
        citation_id = citation.get("id")
        if isinstance(citation_id, str) and citation_id.isdigit():
            citation_ids.add(int(citation_id))
        elif isinstance(citation_id, int):
            citation_ids.add(citation_id)

    return citation_ids


def extract_references(
    filepath: str,
    existing_chapters: set[int],
    citation_ids: set[int] | None,
) -> tuple[list[dict], dict[str, int]]:
    """Extract and validate cross-references in a chapter file."""
    errors = []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    code_block_lines = extract_code_block_line_numbers(content)
    max_chapter = max(existing_chapters) if existing_chapters else 0

    stats = {
        "chapter_total": 0,
        "chapter_valid": 0,
        "citation_total": 0,
        "citation_valid": 0,
    }

    for line_num, line in enumerate(lines, 1):
        stripped_line = line.strip()

        # Skip H1 title lines
        if stripped_line.startswith("# 제") or stripped_line.startswith("# Chapter"):
            continue

        # Skip lines inside code blocks
        if line_num in code_block_lines:
            continue

        # Skip image markers
        if "[IMAGE:" in line:
            continue

        # Skip footnote definitions
        if FOOTNOTE_DEFINITION_PATTERN.match(stripped_line):
            continue

        # Find Korean references
        for match in KO_CHAPTER_PATTERN.finditer(line):
            chapter_num = int(match.group(1))
            if chapter_num == 0:
                continue
            stats["chapter_total"] += 1
            if chapter_num in existing_chapters:
                stats["chapter_valid"] += 1
            else:
                errors.append(
                    {
                        "file": os.path.basename(filepath),
                        "line": line_num,
                        "reference_type": "chapter",
                        "reference": match.group(0),
                        "referenced_chapter": chapter_num,
                        "issue": f"Chapter {chapter_num} does not exist (max chapter: {max_chapter})",
                    }
                )

        # Find English references
        for match in EN_CHAPTER_PATTERN.finditer(line):
            # Skip if this is part of H1 (already checked above, but double-check)
            if stripped_line.startswith("#"):
                continue
            chapter_num = int(match.group(1))
            if chapter_num == 0:
                continue
            stats["chapter_total"] += 1
            if chapter_num in existing_chapters:
                stats["chapter_valid"] += 1
            else:
                errors.append(
                    {
                        "file": os.path.basename(filepath),
                        "line": line_num,
                        "reference_type": "chapter",
                        "reference": match.group(0),
                        "referenced_chapter": chapter_num,
                        "issue": f"Chapter {chapter_num} does not exist (max chapter: {max_chapter})",
                    }
                )

        if citation_ids is None:
            continue

        for match in CITATION_MARKER_PATTERN.finditer(line):
            citation_id = int(match.group(1))
            stats["citation_total"] += 1
            if citation_id in citation_ids:
                stats["citation_valid"] += 1
                continue

            errors.append(
                {
                    "file": os.path.basename(filepath),
                    "line": line_num,
                    "reference_type": "citation",
                    "reference": match.group(0),
                    "citation_id": citation_id,
                    "issue": f"Citation ID {citation_id} not found in citations.json",
                }
            )

    return errors, stats


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    chapters_dir = args.chapters_directory

    if not os.path.isdir(chapters_dir):
        print(json.dumps({"error": f"Directory not found: {chapters_dir}"}))
        sys.exit(1)

    try:
        citations_path = discover_citations_path(chapters_dir, args.citations)
    except FileNotFoundError as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)

    citation_ids = load_citation_ids(citations_path)
    existing_chapters = extract_existing_chapters(chapters_dir)

    if not existing_chapters:
        print(
            json.dumps(
                {
                    "total_references": 0,
                    "valid": 0,
                    "invalid": 0,
                    "chapter_references": {"total": 0, "valid": 0, "invalid": 0},
                    "citation_references": {
                        "total": 0,
                        "valid": 0,
                        "invalid": 0,
                        "citations_path": str(citations_path) if citations_path else None,
                    },
                    "errors": [],
                },
                ensure_ascii=False,
            )
        )
        return

    all_errors = []
    totals = {
        "chapter_total": 0,
        "chapter_valid": 0,
        "citation_total": 0,
        "citation_valid": 0,
    }

    chapter_files = sorted(
        [f for f in os.listdir(chapters_dir) if f.startswith("ch") and f.endswith(".md")]
    )

    for filename in chapter_files:
        filepath = os.path.join(chapters_dir, filename)
        errors, stats = extract_references(filepath, existing_chapters, citation_ids)
        all_errors.extend(errors)
        for key in totals:
            totals[key] += stats[key]

    chapter_invalid = sum(1 for error in all_errors if error["reference_type"] == "chapter")
    citation_invalid = sum(1 for error in all_errors if error["reference_type"] == "citation")

    result = {
        "total_references": totals["chapter_total"] + totals["citation_total"],
        "valid": totals["chapter_valid"] + totals["citation_valid"],
        "invalid": len(all_errors),
        "chapter_references": {
            "total": totals["chapter_total"],
            "valid": totals["chapter_valid"],
            "invalid": chapter_invalid,
        },
        "citation_references": {
            "total": totals["citation_total"],
            "valid": totals["citation_valid"],
            "invalid": citation_invalid,
            "citations_path": str(citations_path) if citations_path else None,
        },
        "errors": all_errors,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
