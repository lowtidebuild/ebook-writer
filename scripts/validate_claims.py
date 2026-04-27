#!/usr/bin/env python3
"""Validate claim ledgers and chapter usage against chapter packs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from claim_utils import (
    ALLOWED_USAGE,
    BODY_USABLE,
    CLAIM_CONFIDENCE,
    load_citations,
    load_json,
    normalize_claim,
    normalize_text,
    source_id,
    write_json,
)
from preflight_utils import FOOTNOTE_MARKER_RE, footnote_info, issue, non_code_lines, result_payload


RISKY_UNCITED_RE = re.compile(
    r"(\b\d{4}\b|\b\d+(?:\.\d+)?%|\bAPI\b|\bSDK\b|법|규정|조항|시행|regulation|statute)",
    re.IGNORECASE,
)


def ledger_claims(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("claims"), list):
        return [claim for claim in payload["claims"] if isinstance(claim, dict)]
    return []


def validate_ledger(
    ledger_path: str | Path,
    citations_path: str | Path | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    path = Path(ledger_path)
    citations = load_citations(citations_path) if citations_path else {}

    if not path.is_file():
        return result_payload(
            "validate_claim_ledger",
            [issue("missing_claim_ledger", f"Claim ledger not found: {path}")],
            claim_ledger=str(path),
        )

    claims = ledger_claims(load_json(path))
    if not claims:
        issues.append(issue("empty_claim_ledger", "claim_ledger.json must contain a non-empty claims array"))

    seen_ids: set[str] = set()
    for index, raw_claim in enumerate(claims):
        claim = normalize_claim(raw_claim)
        label = str(claim.get("id") or f"claims[{index}]")

        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id:
            issues.append(issue("missing_claim_id", "Claim id is required", file=label))
        elif claim_id in seen_ids:
            issues.append(issue("duplicate_claim_id", f"Duplicate claim id: {claim_id}", file=label))
        else:
            seen_ids.add(claim_id)

        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            issues.append(issue("missing_claim_text", "Claim text is required", file=label))
        if not isinstance(claim.get("topic_tags"), list) or not claim["topic_tags"]:
            issues.append(issue("missing_topic_tags", "Claim must have at least one topic tag", file=label))
        if claim.get("confidence") not in CLAIM_CONFIDENCE:
            issues.append(issue("invalid_claim_confidence", "Invalid claim confidence", file=label, confidence=claim.get("confidence")))
        if claim.get("allowed_usage") not in ALLOWED_USAGE:
            issues.append(issue("invalid_allowed_usage", "Invalid allowed_usage", file=label, allowed_usage=claim.get("allowed_usage")))

        source_ids = claim.get("source_ids", [])
        if claim.get("allowed_usage") in BODY_USABLE and not source_ids:
            issues.append(issue("missing_claim_sources", "Body-usable claim must have at least one source_id", file=label))
        if citations:
            for sid in source_ids:
                if source_id(sid) not in citations:
                    issues.append(issue("unknown_claim_source_id", f"Claim references missing citation id: {sid}", file=label, source_id=source_id(sid)))

    return result_payload(
        "validate_claim_ledger",
        issues,
        claim_ledger=str(path),
        claims_checked=len(claims),
        citations_path=str(citations_path) if citations_path else None,
    )


def source_ids_from_pack(pack: dict[str, Any]) -> set[str]:
    explicit = pack.get("allowed_source_ids")
    if isinstance(explicit, list):
        return {source_id(value) for value in explicit}
    ids: set[str] = set()
    for claim in pack.get("allowed_claims", []):
        if isinstance(claim, dict):
            ids.update(source_id(value) for value in claim.get("source_ids", []))
    return ids


def blocked_claims(pack: dict[str, Any], ledger: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for key in ("blocked_claims", "do_not_use_claims"):
        values = pack.get(key, [])
        if isinstance(values, list):
            claims.extend(claim for claim in values if isinstance(claim, dict))
    if ledger:
        claims.extend(
            claim
            for claim in ledger_claims(ledger)
            if claim.get("allowed_usage") == "do_not_use"
        )
    return claims


def validate_chapter_usage(
    chapter_path: str | Path,
    pack_path: str | Path,
    ledger_path: str | Path | None = None,
    strict_unsupported_claims: bool = True,
) -> dict[str, Any]:
    chapter = Path(chapter_path)
    issues: list[dict[str, Any]] = []
    pack_file = Path(pack_path)

    if not chapter.is_file():
        return result_payload(
            "validate_chapter_claim_usage",
            [issue("missing_chapter_file", f"Chapter file not found: {chapter}")],
            chapter=str(chapter),
            pack=str(pack_path),
        )
    if not pack_file.is_file():
        return result_payload(
            "validate_chapter_claim_usage",
            [issue("missing_chapter_pack", f"Chapter pack not found: {pack_file}")],
            chapter=str(chapter),
            pack=str(pack_file),
        )

    pack = load_json(pack_file)
    ledger = load_json(ledger_path) if ledger_path else None

    text = chapter.read_text(encoding="utf-8")
    allowed_sources = source_ids_from_pack(pack)
    info = footnote_info(text)
    for marker_id, line_number in info["marker_lines"]:
        if marker_id not in allowed_sources:
            issues.append(
                issue(
                    "source_not_in_chapter_pack",
                    f"Footnote source [^{marker_id}] is not allowed by this chapter pack",
                    file=str(chapter),
                    line=line_number,
                    source_id=marker_id,
                )
            )

    normalized_chapter = normalize_text(text)
    seen_blocked_ids: set[str] = set()
    for claim in blocked_claims(pack, ledger):
        claim_id = str(claim.get("id", "unknown"))
        if claim_id in seen_blocked_ids:
            continue
        seen_blocked_ids.add(claim_id)
        claim_text = str(claim.get("text", "")).strip()
        if claim_text and normalize_text(claim_text) in normalized_chapter:
            issues.append(
                issue(
                    "blocked_claim_used",
                    "Chapter text contains a do_not_use claim",
                    file=str(chapter),
                    claim_id=claim_id,
                )
            )

    if strict_unsupported_claims:
        for line_number, line in non_code_lines(text):
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("#")
                or stripped.startswith("[^")
                or "[IMAGE:" in stripped
                or FOOTNOTE_MARKER_RE.search(stripped)
            ):
                continue
            if RISKY_UNCITED_RE.search(stripped):
                issues.append(
                    issue(
                        "unsupported_risky_claim",
                        "Risky factual claim appears without an inline footnote",
                        file=str(chapter),
                        line=line_number,
                    )
                )

    return result_payload(
        "validate_chapter_claim_usage",
        issues,
        chapter=str(chapter),
        pack=str(pack_path),
        allowed_source_count=len(allowed_sources),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate claim ledger or chapter claim usage.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ledger_parser = subparsers.add_parser("ledger", help="Validate claim_ledger.json.")
    ledger_parser.add_argument("claim_ledger")
    ledger_parser.add_argument("--citations")
    ledger_parser.add_argument("--output")

    chapter_parser = subparsers.add_parser("chapter", help="Validate a chapter against its chapter pack.")
    chapter_parser.add_argument("chapter")
    chapter_parser.add_argument("--pack", required=True)
    chapter_parser.add_argument("--ledger")
    chapter_parser.add_argument("--allow-uncited-risky-claims", action="store_true")
    chapter_parser.add_argument("--output")

    args = parser.parse_args(argv)
    if args.command == "ledger":
        payload = validate_ledger(args.claim_ledger, args.citations)
        output = args.output
    else:
        payload = validate_chapter_usage(
            args.chapter,
            args.pack,
            ledger_path=args.ledger,
            strict_unsupported_claims=not args.allow_uncited_risky_claims,
        )
        output = args.output

    if output:
        write_json(output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
