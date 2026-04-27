#!/usr/bin/env python3
"""Render table_of_contents.md from outline.json."""

from __future__ import annotations

import argparse
from pathlib import Path

from outline_utils import load_outline, render_outline_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a readable outline Markdown file.")
    parser.add_argument("outline_json", help="Path to output/outline/outline.json")
    parser.add_argument("output_markdown", help="Path to output/outline/table_of_contents.md")
    args = parser.parse_args()

    outline = load_outline(args.outline_json)
    markdown = render_outline_markdown(outline)
    output_path = Path(args.output_markdown)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Rendered {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
