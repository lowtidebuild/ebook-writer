#!/usr/bin/env python3
"""Validate generated PDF web viewer artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from preflight_utils import FOOTNOTE_MARKER_RE, TODO_RE, issue, result_payload, write_json


PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")


def validate_web_viewer(
    viewer_dir: str | Path,
    primary_pdf: str | Path,
    secondary_pdf: str | Path | None = None,
    bilingual: bool = False,
) -> dict[str, Any]:
    root = Path(viewer_dir)
    primary_name = Path(primary_pdf).name
    secondary_name = Path(secondary_pdf).name if secondary_pdf else None
    issues: list[dict[str, Any]] = []

    index_path = root / "index.html"
    if not root.is_dir():
        issues.append(issue("missing_viewer_dir", f"Viewer directory not found: {root}"))
        html = ""
    elif not index_path.is_file():
        issues.append(issue("missing_viewer_index", f"Viewer index.html not found: {index_path}"))
        html = ""
    else:
        html = index_path.read_text(encoding="utf-8")

    if root.is_dir() and not (root / primary_name).is_file():
        issues.append(issue("missing_viewer_primary_pdf", "Primary PDF was not copied into viewer directory", file=str(root / primary_name)))

    if bilingual:
        if not secondary_name:
            issues.append(issue("missing_secondary_pdf_argument", "Bilingual viewer validation requires --secondary-pdf"))
        elif not (root / secondary_name).is_file():
            issues.append(issue("missing_viewer_secondary_pdf", "Secondary PDF was not copied into viewer directory", file=str(root / secondary_name)))

    if html:
        placeholder = PLACEHOLDER_RE.search(html)
        if placeholder:
            issues.append(
                issue(
                    "unreplaced_viewer_placeholder",
                    f"Unreplaced template placeholder remains: {placeholder.group(0)}",
                    file=str(index_path),
                )
            )
        if primary_name not in html:
            issues.append(issue("viewer_missing_primary_pdf_reference", "index.html does not reference the primary PDF", file=str(index_path), pdf=primary_name))
        if bilingual and secondary_name and secondary_name not in html:
            issues.append(issue("viewer_missing_secondary_pdf_reference", "index.html does not reference the secondary PDF", file=str(index_path), pdf=secondary_name))
        if not bilingual and ('id="bk"' in html or 'id="be"' in html):
            issues.append(issue("single_language_toggle_visible", "Single-language viewer still contains language toggle buttons", file=str(index_path)))

        for token in ("[IMAGE:", "[이미지 생성 실패]", "[Image generation failed]"):
            if token in html:
                issues.append(issue("forbidden_viewer_text", f"Forbidden text remains in viewer HTML: {token}", file=str(index_path), token=token))
        if TODO_RE.search(html):
            issues.append(issue("viewer_todo_placeholder", "TODO/TBD remains in viewer HTML", file=str(index_path)))
        if FOOTNOTE_MARKER_RE.search(html):
            issues.append(issue("raw_viewer_footnote_marker", "Raw footnote marker remains in viewer HTML", file=str(index_path)))

    return result_payload(
        "validate_web_viewer",
        issues,
        viewer_dir=str(root),
        primary_pdf=primary_name,
        secondary_pdf=secondary_name,
        bilingual=bilingual,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate generated web viewer output.")
    parser.add_argument("viewer_dir")
    parser.add_argument("--primary-pdf", required=True)
    parser.add_argument("--secondary-pdf")
    parser.add_argument("--bilingual", action="store_true")
    parser.add_argument("--output", help="Optional JSON log output path.")
    args = parser.parse_args(argv)

    payload = validate_web_viewer(
        args.viewer_dir,
        args.primary_pdf,
        secondary_pdf=args.secondary_pdf,
        bilingual=args.bilingual,
    )
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
