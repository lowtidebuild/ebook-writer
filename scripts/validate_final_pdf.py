#!/usr/bin/env python3
"""Validate reader-facing PDF artifacts before final review."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from preflight_utils import FINAL_BLOCKING_TEXT, FOOTNOTE_MARKER_RE, TODO_RE, issue, result_payload, write_json


def extract_pdf_text(path: Path) -> tuple[int, str]:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - dependency is declared.
        raise RuntimeError("pymupdf is required for PDF preflight validation") from exc

    document = fitz.open(path)
    try:
        text_parts = [page.get_text() for page in document]
        return document.page_count, "\n".join(text_parts)
    finally:
        document.close()


def validate_final_pdf(
    pdf_path: str | Path,
    language: str,
    min_size: int = 10 * 1024,
) -> dict[str, Any]:
    path = Path(pdf_path)
    issues: list[dict[str, Any]] = []
    page_count = 0
    extracted_chars = 0

    if not path.is_file():
        issues.append(issue("missing_pdf", f"PDF file not found: {path}"))
        return result_payload("validate_final_pdf", issues, pdf_path=str(path), language=language)

    size = path.stat().st_size
    if size < min_size:
        issues.append(
            issue(
                "pdf_too_small",
                f"PDF file is smaller than expected threshold ({size} < {min_size})",
                file=str(path),
                size=size,
                min_size=min_size,
            )
        )

    try:
        page_count, text = extract_pdf_text(path)
    except Exception as exc:  # noqa: BLE001 - report malformed PDFs as validation failures.
        issues.append(issue("pdf_text_extraction_failed", str(exc), file=str(path)))
        text = ""

    extracted_chars = len(text)
    if page_count <= 0:
        issues.append(issue("pdf_has_no_pages", "PDF has no pages", file=str(path)))

    for token in FINAL_BLOCKING_TEXT:
        if token in text:
            issues.append(
                issue(
                    "forbidden_pdf_text",
                    f"Forbidden text remains in PDF: {token}",
                    file=str(path),
                    token=token,
                )
            )
    if TODO_RE.search(text):
        issues.append(issue("pdf_todo_placeholder", "TODO/TBD remains in PDF text", file=str(path)))
    if FOOTNOTE_MARKER_RE.search(text):
        issues.append(issue("raw_pdf_footnote_marker", "Raw footnote marker remains in PDF text", file=str(path)))

    if language == "ko" and re.search(r"\bChapter\s+\d+\b", text):
        issues.append(
            issue(
                "unexpected_english_chapter_label",
                "Korean PDF contains an English chapter label",
                file=str(path),
            )
        )
    if language == "en" and re.search(r"제\s*\d+\s*장|제\d+장", text):
        issues.append(
            issue(
                "unexpected_korean_chapter_label",
                "English PDF contains a Korean chapter label",
                file=str(path),
            )
        )

    return result_payload(
        "validate_final_pdf",
        issues,
        pdf_path=str(path),
        language=language,
        size=size,
        min_size=min_size,
        page_count=page_count,
        extracted_chars=extracted_chars,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate final PDF output.")
    parser.add_argument("pdf_path")
    parser.add_argument("--language", required=True, choices=["ko", "en"])
    parser.add_argument("--min-size", type=int, default=10 * 1024)
    parser.add_argument("--output", help="Optional JSON log output path.")
    args = parser.parse_args(argv)

    payload = validate_final_pdf(args.pdf_path, args.language, args.min_size)
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
