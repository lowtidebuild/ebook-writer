from __future__ import annotations

import json

from helpers import load_module


validate_claims = load_module("validate_claims_module", "scripts/validate_claims.py")


def write_citations(path) -> None:
    path.write_text(
        json.dumps(
            {
                "citations": [
                    {"id": 1, "title": "Official Guide", "url": "https://example.com/guide"},
                    {"id": 2, "title": "API Docs", "url": "https://example.com/api"},
                ]
            }
        ),
        encoding="utf-8",
    )


def test_validate_ledger_accepts_body_usable_claims_with_sources(tmp_path) -> None:
    citations = tmp_path / "citations.json"
    write_citations(citations)
    ledger = tmp_path / "claim_ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "id": "claim_001",
                        "text": "The API supports local file edits after approval.",
                        "topic_tags": ["api", "approval"],
                        "source_ids": [1],
                        "supporting_excerpt": "Official guide describes approval before local edits.",
                        "confidence": "verified",
                        "allowed_usage": "safe_to_state",
                        "notes": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = validate_claims.validate_ledger(ledger, citations)

    assert result["status"] == "passed"


def test_validate_ledger_blocks_duplicate_ids_and_unknown_sources(tmp_path) -> None:
    citations = tmp_path / "citations.json"
    write_citations(citations)
    ledger = tmp_path / "claim_ledger.json"
    claim = {
        "id": "claim_001",
        "text": "Unsupported API fact.",
        "topic_tags": ["api"],
        "source_ids": [99],
        "supporting_excerpt": "",
        "confidence": "verified",
        "allowed_usage": "safe_to_state",
    }
    ledger.write_text(json.dumps({"claims": [claim, claim]}), encoding="utf-8")

    result = validate_claims.validate_ledger(ledger, citations)
    codes = {issue["code"] for issue in result["issues"]}

    assert result["status"] == "failed"
    assert "duplicate_claim_id" in codes
    assert "unknown_claim_source_id" in codes


def test_validate_chapter_usage_blocks_pack_outside_source_and_do_not_use_claim(tmp_path) -> None:
    chapter = tmp_path / "ch01_intro.md"
    chapter.write_text(
        "# Chapter 1: Intro\n\n"
        "The forbidden claim is true.[^2]\n\n"
        "[^2]: Bad source\n",
        encoding="utf-8",
    )
    pack = tmp_path / "ch01_intro.json"
    pack.write_text(
        json.dumps(
            {
                "allowed_claims": [
                    {"id": "claim_001", "text": "Allowed claim.", "source_ids": [1]}
                ],
                "blocked_claims": [
                    {
                        "id": "claim_999",
                        "text": "The forbidden claim is true.",
                        "source_ids": [2],
                        "allowed_usage": "do_not_use",
                    }
                ],
                "allowed_source_ids": ["1"],
            }
        ),
        encoding="utf-8",
    )

    result = validate_claims.validate_chapter_usage(
        chapter,
        pack,
        strict_unsupported_claims=False,
    )
    codes = {issue["code"] for issue in result["issues"]}

    assert result["status"] == "failed"
    assert "source_not_in_chapter_pack" in codes
    assert "blocked_claim_used" in codes


def test_validate_chapter_usage_blocks_uncited_risky_claim(tmp_path) -> None:
    chapter = tmp_path / "ch01_intro.md"
    chapter.write_text(
        "# Chapter 1: Intro\n\n"
        "The API changed in 2025 and now supports a new SDK mode.\n",
        encoding="utf-8",
    )
    pack = tmp_path / "ch01_intro.json"
    pack.write_text(json.dumps({"allowed_claims": [], "allowed_source_ids": []}), encoding="utf-8")

    result = validate_claims.validate_chapter_usage(chapter, pack)

    assert result["status"] == "failed"
    assert any(issue["code"] == "unsupported_risky_claim" for issue in result["issues"])
