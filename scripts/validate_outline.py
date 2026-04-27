#!/usr/bin/env python3
"""Validate outline.json and its rendered Markdown companion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from outline_utils import (
    load_outline,
    normalized_markdown,
    render_outline_markdown,
    validate_outline,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a structured ebook outline.")
    parser.add_argument("outline_json", help="Path to output/outline/outline.json")
    parser.add_argument(
        "--markdown",
        help="Optional path to output/outline/table_of_contents.md for consistency checks",
    )
    args = parser.parse_args()

    outline_path = Path(args.outline_json)
    errors: list[str] = []
    outline = None
    try:
        outline = load_outline(outline_path)
        errors.extend(validate_outline(outline))
    except Exception as exc:  # noqa: BLE001 - report malformed user-facing artifacts.
        errors.append(f"Unable to read outline JSON: {exc}")

    if outline is not None and args.markdown:
        markdown_path = Path(args.markdown)
        if not markdown_path.exists():
            errors.append(f"Markdown outline does not exist: {markdown_path}")
        elif not errors:
            expected = normalized_markdown(render_outline_markdown(outline))
            actual = normalized_markdown(markdown_path.read_text(encoding="utf-8"))
            if actual != expected:
                errors.append(
                    "Markdown outline is out of sync with outline.json. "
                    "Regenerate it with scripts/render_outline_markdown.py."
                )

    chapter_count = 0
    if isinstance(outline, dict) and isinstance(outline.get("chapters"), list):
        chapter_count = len(outline["chapters"])

    print(
        json.dumps(
            {
                "status": "failed" if errors else "passed",
                "errors": errors,
                "chapter_count": chapter_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
