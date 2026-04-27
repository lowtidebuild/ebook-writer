#!/usr/bin/env python3
"""Claim ledger and chapter pack helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ALLOWED_USAGE = {
    "safe_to_state",
    "state_with_hedge",
    "background_only",
    "do_not_use",
}
CLAIM_CONFIDENCE = {"verified", "partially_verified", "unverified"}
BODY_USABLE = {"safe_to_state", "state_with_hedge"}
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def source_id(value: Any) -> str:
    return str(value)


def load_citations(path: str | Path) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    citations = data if isinstance(data, list) else data.get("citations", [])
    result: dict[str, dict[str, Any]] = {}
    for citation in citations:
        if not isinstance(citation, dict) or "id" not in citation:
            continue
        result[source_id(citation["id"])] = citation
    return result


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def tokens(value: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(value) if len(token) >= 2}


def chapter_search_text(chapter: dict[str, Any]) -> str:
    parts = [
        str(chapter.get("slug", "")),
        str(chapter.get("title", "")),
        str(chapter.get("summary", "")),
        " ".join(str(item) for item in chapter.get("key_content", [])),
    ]
    return " ".join(parts)


def claim_matches_chapter(claim: dict[str, Any], chapter: dict[str, Any]) -> bool:
    chapter_id = chapter.get("chapter_id")
    chapter_slug = chapter.get("slug")
    if chapter_id in claim.get("chapter_ids", []):
        return True
    if chapter_slug in claim.get("chapter_slugs", []):
        return True

    chapter_tokens = tokens(chapter_search_text(chapter))
    tag_tokens = set()
    for tag in claim.get("topic_tags", []):
        tag_tokens.update(tokens(str(tag).replace("-", " ")))
    if tag_tokens and chapter_tokens.intersection(tag_tokens):
        return True

    claim_tokens = tokens(str(claim.get("text", "")))
    return bool(chapter_tokens.intersection(claim_tokens))


def normalize_claim(claim: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(claim)
    normalized["source_ids"] = [source_id(value) for value in claim.get("source_ids", [])]
    normalized.setdefault("notes", "")
    return normalized
