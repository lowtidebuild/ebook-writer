#!/usr/bin/env python3
"""Run final preflight validators before Gate 2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from preflight_utils import result_payload, write_json
from validate_chapters import validate_chapters
from validate_claims import validate_chapter_usage
from validate_final_pdf import validate_final_pdf
from validate_images import validate_images
from validate_translations import validate_translations
from validate_web_viewer import validate_web_viewer


def collect_issues(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for result in results:
        validator = result.get("validator")
        for item in result.get("issues", []):
            enriched = dict(item)
            enriched.setdefault("validator", validator)
            issues.append(enriched)
    return issues


def run_preflight(args: argparse.Namespace) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    results.append(validate_chapters(args.primary_chapters, args.primary_language, args.citations))

    chapter_packs_dir = getattr(args, "chapter_packs_dir", None)
    if chapter_packs_dir:
        for chapter_path in sorted(Path(args.primary_chapters).glob("ch*.md")):
            pack_path = Path(chapter_packs_dir) / f"{chapter_path.stem}.json"
            results.append(
                validate_chapter_usage(
                    chapter_path,
                    pack_path,
                    ledger_path=getattr(args, "claim_ledger", None),
                )
            )

    if args.secondary_chapters:
        results.append(validate_chapters(args.secondary_chapters, args.secondary_language, args.citations))
    if args.bilingual:
        results.append(validate_translations(args.primary_chapters, args.secondary_chapters))

    if args.image_manifest and Path(args.image_manifest).exists():
        results.append(validate_images(args.image_manifest))

    if args.primary_pdf:
        results.append(validate_final_pdf(args.primary_pdf, args.primary_language, args.min_pdf_size))
    if args.secondary_pdf:
        results.append(validate_final_pdf(args.secondary_pdf, args.secondary_language, args.min_pdf_size))

    if args.viewer_dir and args.primary_pdf:
        results.append(
            validate_web_viewer(
                args.viewer_dir,
                args.primary_pdf,
                secondary_pdf=args.secondary_pdf,
                bilingual=args.bilingual,
            )
        )

    issues = collect_issues(results)
    payload = result_payload(
        "final_preflight",
        issues,
        validators_run=[result.get("validator") for result in results],
        results=results,
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run final ebook artifact preflight checks.")
    parser.add_argument("--primary-chapters", required=True)
    parser.add_argument("--primary-language", required=True, choices=["ko", "en"])
    parser.add_argument("--secondary-chapters")
    parser.add_argument("--secondary-language", default="en", choices=["ko", "en"])
    parser.add_argument("--bilingual", action="store_true")
    parser.add_argument("--citations")
    parser.add_argument("--claim-ledger")
    parser.add_argument("--chapter-packs-dir")
    parser.add_argument("--image-manifest")
    parser.add_argument("--primary-pdf")
    parser.add_argument("--secondary-pdf")
    parser.add_argument("--viewer-dir")
    parser.add_argument("--min-pdf-size", type=int, default=10 * 1024)
    parser.add_argument(
        "--output",
        default="output/logs/validation/final_preflight.json",
        help="JSON log output path.",
    )
    args = parser.parse_args(argv)

    if args.bilingual and not args.secondary_chapters:
        parser.error("--bilingual requires --secondary-chapters")

    payload = run_preflight(args)
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
