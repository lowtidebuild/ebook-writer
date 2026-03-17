#!/usr/bin/env python3
"""
extract_markers.py - Scan chapter markdown files for [IMAGE: ...] markers
and produce an image_manifest.json.

Usage:
    python3 extract_markers.py <chapters_dir> <output_manifest_path>

Example:
    python3 extract_markers.py output/chapters/ko/ output/images/image_manifest.json
"""

import json
import os
import re
import sys
from pathlib import Path

IMAGE_MARKER_RE = re.compile(r"\[IMAGE:\s*(.+?)\]")


def extract_markers(chapters_dir: str, output_manifest_path: str) -> None:
    chapters_path = Path(chapters_dir)
    if not chapters_path.is_dir():
        print(f"Error: chapters directory does not exist: {chapters_dir}", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(chapters_path.glob("*.md"))
    if not md_files:
        print(f"Warning: no .md files found in {chapters_dir}", file=sys.stderr)

    manifest: list[dict] = []
    chapter_counters: dict[str, int] = {}

    for md_file in md_files:
        chapter_stem = md_file.stem  # e.g. "ch01_introduction"
        # Derive a short chapter tag like "ch01" from the filename.
        # Accepts patterns such as ch01, chapter01, ch1, etc.
        tag_match = re.match(r"(ch(?:apter)?_?\d+)", chapter_stem, re.IGNORECASE)
        chapter_tag = tag_match.group(1) if tag_match else chapter_stem

        with open(md_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_number_0, line in enumerate(lines):
            line_number = line_number_0 + 1  # 1-based
            for match in IMAGE_MARKER_RE.finditer(line):
                description = match.group(1).strip()

                # Build a unique marker_id
                counter = chapter_counters.get(chapter_tag, 0) + 1
                chapter_counters[chapter_tag] = counter
                marker_id = f"{chapter_tag}_img{counter:02d}"

                # Determine the output image path relative to project root,
                # placed alongside the manifest.
                output_dir = Path(output_manifest_path).parent
                output_image_path = str(output_dir / f"{marker_id}.png")

                manifest.append(
                    {
                        "marker_id": marker_id,
                        "chapter_file": str(md_file),
                        "description": description,
                        "line_number": line_number,
                        "output_path": output_image_path,
                        "prompt": None,
                        "status": "pending",
                    }
                )

    # Ensure output directory exists
    output_path = Path(output_manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Extracted {len(manifest)} image marker(s) from {len(md_files)} chapter file(s).")
    print(f"Manifest written to: {output_manifest_path}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python3 extract_markers.py <chapters_dir> <output_manifest_path>", file=sys.stderr)
        sys.exit(1)

    chapters_dir = sys.argv[1]
    output_manifest_path = sys.argv[2]
    extract_markers(chapters_dir, output_manifest_path)


if __name__ == "__main__":
    main()
