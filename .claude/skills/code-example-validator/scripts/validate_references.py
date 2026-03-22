#!/usr/bin/env python3
"""Validate cross-references between chapters in markdown files.

Usage:
    python3 validate_references.py <chapters_directory>

Scans chapter files for references to other chapters and validates
that referenced chapters actually exist.
Output: JSON to stdout
"""

import json
import os
import re
import sys


def extract_existing_chapters(directory: str) -> set[int]:
    """Extract chapter numbers from filenames in the directory."""
    chapters = set()
    pattern = re.compile(r"^ch(\d+)_")
    for filename in os.listdir(directory):
        match = pattern.match(filename)
        if match:
            chapters.add(int(match.group(1)))
    return chapters


def is_inside_code_block(lines: list[str], line_index: int) -> bool:
    """Check if a line is inside a fenced code block."""
    fence_count = 0
    for i in range(line_index):
        if lines[i].strip().startswith("```"):
            fence_count += 1
    return fence_count % 2 == 1


def extract_references(filepath: str, existing_chapters: set[int]) -> list[dict]:
    """Extract and validate cross-references in a chapter file."""
    errors = []
    valid_count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    max_chapter = max(existing_chapters) if existing_chapters else 0

    # Korean pattern: N장 (but not in H1 titles like "# 제N장:")
    ko_pattern = re.compile(r"(\d+)장")
    # English pattern: Chapter N (but not in H1 titles like "# Chapter N:")
    en_pattern = re.compile(r"Chapter\s+(\d+)", re.IGNORECASE)

    for line_num, line in enumerate(lines, 1):
        # Skip H1 title lines
        if line.startswith("# 제") or line.startswith("# Chapter"):
            continue

        # Skip lines inside code blocks
        if is_inside_code_block(lines, line_num - 1):
            continue

        # Skip image markers
        if "[IMAGE:" in line:
            continue

        # Skip footnote definitions
        if re.match(r"^\[\^\d+\]:", line):
            continue

        # Find Korean references
        for match in ko_pattern.finditer(line):
            chapter_num = int(match.group(1))
            if chapter_num == 0:
                continue
            if chapter_num in existing_chapters:
                valid_count += 1
            else:
                errors.append({
                    "file": os.path.basename(filepath),
                    "line": line_num,
                    "reference": match.group(0),
                    "referenced_chapter": chapter_num,
                    "issue": f"Chapter {chapter_num} does not exist (max chapter: {max_chapter})",
                })

        # Find English references
        for match in en_pattern.finditer(line):
            # Skip if this is part of H1 (already checked above, but double-check)
            if line.strip().startswith("#"):
                continue
            chapter_num = int(match.group(1))
            if chapter_num == 0:
                continue
            if chapter_num in existing_chapters:
                valid_count += 1
            else:
                errors.append({
                    "file": os.path.basename(filepath),
                    "line": line_num,
                    "reference": match.group(0),
                    "referenced_chapter": chapter_num,
                    "issue": f"Chapter {chapter_num} does not exist (max chapter: {max_chapter})",
                })

    return errors, valid_count


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_references.py <chapters_directory>", file=sys.stderr)
        sys.exit(1)

    chapters_dir = sys.argv[1]

    if not os.path.isdir(chapters_dir):
        print(json.dumps({"error": f"Directory not found: {chapters_dir}"}))
        sys.exit(1)

    existing_chapters = extract_existing_chapters(chapters_dir)

    if not existing_chapters:
        print(json.dumps({
            "total_references": 0,
            "valid": 0,
            "invalid": 0,
            "errors": [],
        }))
        return

    all_errors = []
    total_valid = 0

    chapter_files = sorted(
        [f for f in os.listdir(chapters_dir) if f.startswith("ch") and f.endswith(".md")]
    )

    for filename in chapter_files:
        filepath = os.path.join(chapters_dir, filename)
        errors, valid_count = extract_references(filepath, existing_chapters)
        all_errors.extend(errors)
        total_valid += valid_count

    result = {
        "total_references": total_valid + len(all_errors),
        "valid": total_valid,
        "invalid": len(all_errors),
        "errors": all_errors,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
