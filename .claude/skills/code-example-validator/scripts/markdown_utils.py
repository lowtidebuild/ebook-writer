#!/usr/bin/env python3
"""Shared markdown parsing helpers for validator scripts."""

from __future__ import annotations

import re


FENCED_CODE_BLOCK_PATTERN = re.compile(
    r"^```([^\s:`]+)?(?::([^\s`]+))?\s*\n(.*?)^```",
    re.MULTILINE | re.DOTALL,
)


def extract_code_blocks(markdown_text: str) -> list[dict]:
    """Extract fenced code blocks with language tags and line numbers."""
    blocks = []

    for index, match in enumerate(FENCED_CODE_BLOCK_PATTERN.finditer(markdown_text)):
        block_text = match.group(0)
        start_line = markdown_text.count("\n", 0, match.start()) + 1
        end_line = start_line + block_text.count("\n")

        blocks.append(
            {
                "block_index": index,
                "language": (match.group(1) or "unknown").lower(),
                "tag": match.group(2),
                "code": match.group(3),
                "line_in_file": start_line,
                "start_line": start_line,
                "end_line": end_line,
            }
        )

    return blocks


def extract_code_block_line_numbers(markdown_text: str) -> set[int]:
    """Return the set of markdown line numbers occupied by fenced code blocks."""
    line_numbers: set[int] = set()

    for block in extract_code_blocks(markdown_text):
        line_numbers.update(range(block["start_line"], block["end_line"] + 1))

    return line_numbers
