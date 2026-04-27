#!/usr/bin/env python3
"""Build a compact outline-facing summary from a research report."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.MULTILINE)


def compact_words(text: str, max_words: int) -> str:
    words = re.sub(r"\s+", " ", text).strip().split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + " ..."


def split_sections(markdown: str) -> list[tuple[str, str]]:
    matches = list(HEADING_RE.finditer(markdown))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        title = match.group(2).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        if body:
            sections.append((title, body))
    return sections


def summarize_research(markdown: str, max_sections: int = 14, max_words_per_section: int = 90) -> str:
    """Return a concise markdown summary for the Architect agent."""
    sections = split_sections(markdown)
    output = [
        "# Research Summary for Outline",
        "",
        "Use this compact summary before opening the full research report.",
        "",
    ]

    for title, body in sections[:max_sections]:
        source_lines = [
            line.strip()
            for line in body.splitlines()
            if line.strip().startswith("- ") and ("http" in line or "—" in line)
        ][:3]
        body_without_sources = "\n".join(
            line for line in body.splitlines() if not line.strip().startswith("- ")
        )
        output.extend([f"## {title}", "", compact_words(body_without_sources, max_words_per_section)])
        if source_lines:
            output.extend(["", "**Representative Sources**:", *source_lines])
        output.append("")

    if len(sections) > max_sections:
        output.append(f"_Omitted {len(sections) - max_sections} lower-priority sections; use the full report only as fallback._")
        output.append("")

    return "\n".join(output).rstrip() + "\n"


def write_research_summary(
    research_report: str | Path,
    output_path: str | Path,
    max_sections: int = 14,
    max_words_per_section: int = 90,
) -> dict[str, str | int]:
    markdown = Path(research_report).read_text(encoding="utf-8")
    summary = summarize_research(
        markdown,
        max_sections=max_sections,
        max_words_per_section=max_words_per_section,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(summary, encoding="utf-8")
    return {
        "status": "created",
        "summary_path": str(destination),
        "word_count": len(summary.split()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize research report for outline design.")
    parser.add_argument("research_report")
    parser.add_argument("output_path")
    parser.add_argument("--max-sections", type=int, default=14)
    parser.add_argument("--max-words-per-section", type=int, default=90)
    args = parser.parse_args(argv)

    payload = write_research_summary(
        args.research_report,
        args.output_path,
        max_sections=args.max_sections,
        max_words_per_section=args.max_words_per_section,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
