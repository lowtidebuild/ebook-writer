#!/usr/bin/env python3
"""
insert_images.py - Replace [IMAGE: ...] markers in chapter files with
generated image links or failure placeholders.

Usage:
    python3 insert_images.py <manifest_json_path> <chapters_dir>

Example:
    python3 insert_images.py output/images/image_manifest.json output/chapters/ko/
"""

import json
import re
import sys
from pathlib import Path


def load_manifest(manifest_path: str) -> list[dict]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_replacement(entry: dict, chapters_dir: str) -> str:
    """Return the markdown string that should replace the [IMAGE: ...] marker."""
    marker_id = entry["marker_id"]
    description = entry["description"]
    status = entry["status"]

    if status == "completed":
        # Build a relative path from the chapter file to the image.
        # Chapters live in chapters_dir; images live in a sibling "images" dir.
        image_filename = f"{marker_id}.png"
        relative_path = f"../images/{image_filename}"
        return f"![{description}]({relative_path})"
    else:
        # Placeholder for failed or still-pending entries
        return f"> [이미지 생성 실패] {description}"


def insert_images(manifest_path: str, chapters_dir: str) -> None:
    manifest = load_manifest(manifest_path)

    if not manifest:
        print("Manifest is empty. Nothing to insert.")
        return

    # Group entries by chapter file for efficient processing
    chapters_map: dict[str, list[dict]] = {}
    for entry in manifest:
        chapter_file = entry["chapter_file"]
        chapters_map.setdefault(chapter_file, []).append(entry)

    inserted_count = 0
    placeholder_count = 0
    skipped_files = 0

    for chapter_file, entries in chapters_map.items():
        chapter_path = Path(chapter_file)
        if not chapter_path.is_file():
            print(f"Warning: chapter file not found, skipping: {chapter_file}", file=sys.stderr)
            skipped_files += 1
            continue

        with open(chapter_path, "r", encoding="utf-8") as f:
            content = f.read()

        modified = False

        for entry in entries:
            description = entry["description"]
            # Escape special regex characters in the description
            escaped_desc = re.escape(description)
            # Match the exact [IMAGE: description] marker
            pattern = re.compile(r"\[IMAGE:\s*" + escaped_desc + r"\s*\]")

            replacement = build_replacement(entry, chapters_dir)

            new_content, count = pattern.subn(replacement, content, count=1)
            if count > 0:
                content = new_content
                modified = True
                if entry["status"] == "completed":
                    inserted_count += 1
                else:
                    placeholder_count += 1
            else:
                print(
                    f"Warning: marker not found in {chapter_file}: "
                    f"[IMAGE: {description[:60]}{'...' if len(description) > 60 else ''}]",
                    file=sys.stderr,
                )

        if modified:
            with open(chapter_path, "w", encoding="utf-8") as f:
                f.write(content)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"Insertion complete:")
    print(f"  Images inserted : {inserted_count}")
    print(f"  Placeholders    : {placeholder_count}")
    if skipped_files:
        print(f"  Skipped files   : {skipped_files}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python3 insert_images.py <manifest_json_path> <chapters_dir>", file=sys.stderr)
        sys.exit(1)

    manifest_path = sys.argv[1]
    chapters_dir = sys.argv[2]

    if not Path(manifest_path).is_file():
        print(f"Error: manifest file not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    if not Path(chapters_dir).is_dir():
        print(f"Error: chapters directory not found: {chapters_dir}", file=sys.stderr)
        sys.exit(1)

    insert_images(manifest_path, chapters_dir)


if __name__ == "__main__":
    main()
