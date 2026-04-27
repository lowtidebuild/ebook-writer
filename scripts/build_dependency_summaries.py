#!/usr/bin/env python3
"""Build compact summaries of completed chapter files for downstream agents."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CHAPTER_RE = re.compile(r"^ch(\d+)_")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


def chapter_number(path: str | Path) -> int | None:
    match = CHAPTER_RE.match(Path(path).name)
    return int(match.group(1)) if match else None


def first_body_paragraph(markdown: str) -> str:
    for paragraph in re.split(r"\n\s*\n", markdown):
        stripped = paragraph.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("[^"):
            return re.sub(r"\s+", " ", stripped)
    return ""


def summarize_chapter(path: str | Path, max_words: int = 120) -> dict[str, Any]:
    source_path = Path(path)
    markdown = source_path.read_text(encoding="utf-8")
    headings = [
        {"level": len(match.group(1)), "title": match.group(2).strip()}
        for match in HEADING_RE.finditer(markdown)
    ]
    title = headings[0]["title"] if headings else source_path.stem
    words = markdown.split()
    paragraph_words = first_body_paragraph(markdown).split()
    summary = " ".join(paragraph_words[:max_words])
    if len(paragraph_words) > max_words:
        summary += " ..."

    return {
        "chapter_number": chapter_number(source_path),
        "source_file": str(source_path),
        "title": title,
        "word_count": len(words),
        "summary": summary,
        "headings": headings[:20],
    }


def build_dependency_summaries(
    chapters_dir: str | Path,
    output_dir: str | Path,
    max_words: int = 120,
) -> dict[str, Any]:
    source_root = Path(chapters_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    chapter_files = sorted(source_root.glob("ch*.md"))

    entries: list[dict[str, Any]] = []
    for chapter_path in chapter_files:
        summary = summarize_chapter(chapter_path, max_words=max_words)
        number = summary["chapter_number"] or 0
        summary_path = output_root / f"ch{number:02d}_summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        entries.append(
            {
                "chapter_number": summary["chapter_number"],
                "source_file": summary["source_file"],
                "summary_path": str(summary_path),
                "title": summary["title"],
                "word_count": summary["word_count"],
            }
        )

    manifest = {
        "status": "created",
        "chapter_count": len(entries),
        "chapters_dir": str(source_root),
        "output_dir": str(output_root),
        "summaries": entries,
    }
    manifest_path = output_root / "dependency_summaries_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build compact dependency summaries from chapter markdown files.")
    parser.add_argument("chapters_dir")
    parser.add_argument("output_dir")
    parser.add_argument("--max-words", type=int, default=120)
    args = parser.parse_args(argv)

    try:
        payload = build_dependency_summaries(args.chapters_dir, args.output_dir, max_words=args.max_words)
    except Exception as exc:  # noqa: BLE001 - CLI should report structured failures.
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
