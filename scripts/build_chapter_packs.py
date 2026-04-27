#!/usr/bin/env python3
"""Build per-chapter evidence packs from outline, claim ledger, and citations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from claim_utils import (
    BODY_USABLE,
    claim_matches_chapter,
    load_citations,
    load_json,
    normalize_claim,
    source_id,
    write_json,
)
from outline_utils import validate_outline
from validate_claims import ledger_claims, validate_ledger


def citation_subset(citations: dict[str, dict[str, Any]], source_ids: set[str]) -> list[dict[str, Any]]:
    return [citations[sid] for sid in sorted(source_ids, key=lambda value: (not value.isdigit(), value)) if sid in citations]


def pack_path(output_dir: str | Path, chapter: dict[str, Any]) -> Path:
    return Path(output_dir) / f"ch{chapter['chapter_id']:02d}_{chapter['slug']}.json"


def build_pack_for_chapter(
    chapter: dict[str, Any],
    claims: list[dict[str, Any]],
    citations: dict[str, dict[str, Any]],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    matched = [normalize_claim(claim) for claim in claims if claim_matches_chapter(claim, chapter)]
    allowed_claims = [claim for claim in matched if claim.get("allowed_usage") in BODY_USABLE]
    background_claims = [claim for claim in matched if claim.get("allowed_usage") == "background_only"]
    blocked_claims = [claim for claim in matched if claim.get("allowed_usage") == "do_not_use"]

    allowed_source_ids: set[str] = set()
    cited_source_ids: set[str] = set()
    for claim in allowed_claims:
        ids = {source_id(value) for value in claim.get("source_ids", [])}
        allowed_source_ids.update(ids)
        cited_source_ids.update(ids)
    for claim in background_claims + blocked_claims:
        cited_source_ids.update(source_id(value) for value in claim.get("source_ids", []))

    return {
        "chapter_id": chapter["chapter_id"],
        "slug": chapter["slug"],
        "title": chapter["title"],
        "summary": chapter["summary"],
        "key_content": chapter["key_content"],
        "dependencies": chapter["dependencies"],
        "allowed_claims": allowed_claims,
        "background_claims": background_claims,
        "blocked_claims": blocked_claims,
        "allowed_source_ids": sorted(allowed_source_ids, key=lambda value: (not value.isdigit(), value)),
        "citations": citation_subset(citations, cited_source_ids),
        "usage_policy": {
            "safe_to_state": "May be stated directly with inline source footnotes.",
            "state_with_hedge": "Must be hedged in prose and cited.",
            "background_only": "May inform framing but must not be stated as a factual claim.",
            "do_not_use": "Must not appear in chapter text.",
        },
        "generated_from": source_paths,
    }


def build_chapter_packs(
    outline_path: str | Path,
    claim_ledger_path: str | Path,
    citations_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    outline = load_json(outline_path)
    outline_errors = validate_outline(outline)
    if outline_errors:
        raise ValueError("Invalid outline: " + "; ".join(outline_errors))

    ledger_result = validate_ledger(claim_ledger_path, citations_path)
    if ledger_result["status"] == "failed":
        raise ValueError(
            "Invalid claim ledger: "
            + "; ".join(issue["message"] for issue in ledger_result["issues"])
        )

    claim_ledger = load_json(claim_ledger_path)
    claims = ledger_claims(claim_ledger)
    citations = load_citations(citations_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    source_paths = {
        "outline": str(outline_path),
        "claim_ledger": str(claim_ledger_path),
        "citations": str(citations_path),
    }
    written: list[str] = []
    for chapter in outline["chapters"]:
        pack = build_pack_for_chapter(chapter, claims, citations, source_paths)
        path = pack_path(output_root, chapter)
        write_json(path, pack)
        written.append(str(path))

    manifest = {
        "status": "created",
        "chapter_count": len(outline["chapters"]),
        "output_dir": str(output_root),
        "packs": written,
    }
    write_json(output_root / "chapter_packs_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build per-chapter evidence packs.")
    parser.add_argument("outline_json")
    parser.add_argument("claim_ledger_json")
    parser.add_argument("citations_json")
    parser.add_argument("output_dir")
    args = parser.parse_args(argv)

    try:
        payload = build_chapter_packs(
            args.outline_json,
            args.claim_ledger_json,
            args.citations_json,
            args.output_dir,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should report validation failures.
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
