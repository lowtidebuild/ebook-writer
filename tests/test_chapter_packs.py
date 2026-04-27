from __future__ import annotations

import json

from helpers import load_module


build_chapter_packs = load_module("build_chapter_packs_module", "scripts/build_chapter_packs.py")


def write_outline(path) -> None:
    path.write_text(
        json.dumps(
            {
                "book_title": "AI Workflow",
                "target_audience": "Operators",
                "chapters": [
                    {
                        "chapter_id": 1,
                        "slug": "api-foundations",
                        "title": "API Foundations",
                        "summary": "Core API approval workflow.",
                        "key_content": ["approval", "file edits"],
                        "estimated_words": 2000,
                        "dependencies": [],
                    },
                    {
                        "chapter_id": 2,
                        "slug": "operations",
                        "title": "Operations",
                        "summary": "Operational monitoring.",
                        "key_content": ["monitoring"],
                        "estimated_words": 2000,
                        "dependencies": [1],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def write_citations(path) -> None:
    path.write_text(
        json.dumps(
            {
                "citations": [
                    {"id": 1, "title": "Official Guide", "url": "https://example.com/guide"},
                    {"id": 2, "title": "Monitoring Guide", "url": "https://example.com/ops"},
                    {"id": 3, "title": "Unsafe Blog", "url": "https://example.com/blog"},
                ]
            }
        ),
        encoding="utf-8",
    )


def write_ledger(path) -> None:
    path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "id": "claim_001",
                        "text": "The API requires approval before file edits.",
                        "topic_tags": ["api", "approval"],
                        "source_ids": [1],
                        "supporting_excerpt": "Approval is required before file edits.",
                        "confidence": "verified",
                        "allowed_usage": "safe_to_state",
                    },
                    {
                        "id": "claim_002",
                        "text": "Monitoring should be reviewed weekly.",
                        "topic_tags": ["monitoring"],
                        "source_ids": [2],
                        "supporting_excerpt": "Monitoring guidance discusses regular review.",
                        "confidence": "partially_verified",
                        "allowed_usage": "state_with_hedge",
                    },
                    {
                        "id": "claim_003",
                        "text": "The API never requires approval.",
                        "topic_tags": ["api"],
                        "source_ids": [3],
                        "supporting_excerpt": "Unsupported blog claim.",
                        "confidence": "unverified",
                        "allowed_usage": "do_not_use",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def test_build_chapter_packs_selects_claims_and_sources(tmp_path) -> None:
    outline = tmp_path / "outline.json"
    citations = tmp_path / "citations.json"
    ledger = tmp_path / "claim_ledger.json"
    out_dir = tmp_path / "chapter_packs"
    write_outline(outline)
    write_citations(citations)
    write_ledger(ledger)

    manifest = build_chapter_packs.build_chapter_packs(outline, ledger, citations, out_dir)
    ch1 = json.loads((out_dir / "ch01_api-foundations.json").read_text(encoding="utf-8"))
    ch2 = json.loads((out_dir / "ch02_operations.json").read_text(encoding="utf-8"))

    assert manifest["chapter_count"] == 2
    assert ch1["allowed_source_ids"] == ["1"]
    assert [claim["id"] for claim in ch1["allowed_claims"]] == ["claim_001"]
    assert [claim["id"] for claim in ch1["blocked_claims"]] == ["claim_003"]
    assert [claim["id"] for claim in ch2["allowed_claims"]] == ["claim_002"]
    assert (out_dir / "chapter_packs_manifest.json").is_file()


def test_build_chapter_packs_fails_for_invalid_ledger(tmp_path) -> None:
    outline = tmp_path / "outline.json"
    citations = tmp_path / "citations.json"
    ledger = tmp_path / "claim_ledger.json"
    write_outline(outline)
    write_citations(citations)
    ledger.write_text(json.dumps({"claims": []}), encoding="utf-8")

    try:
        build_chapter_packs.build_chapter_packs(outline, ledger, citations, tmp_path / "packs")
    except ValueError as exc:
        assert "Invalid claim ledger" in str(exc)
    else:
        raise AssertionError("Expected invalid claim ledger to fail")
