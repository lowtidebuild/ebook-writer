#!/usr/bin/env python3
"""Maintain a normalized source cache for research citations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def normalize_url(url: str) -> str:
    """Return a canonical URL suitable for deduplication."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            urlencode(sorted(query)),
            "",
        )
    )


def citation_sources(payload: Any) -> list[dict[str, Any]]:
    """Extract citation objects from either list or {citations: [...]} payloads."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [item for item in payload.get("citations", []) if isinstance(item, dict)]
    return []


def source_cache_key(source: dict[str, Any]) -> str:
    normalized = normalize_url(str(source.get("url", "")))
    if normalized:
        return normalized
    title = str(source.get("title", "")).strip().casefold()
    return f"title:{title}" if title else f"id:{source.get('id', '')}"


def build_source_cache(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a deduplicated cache payload from citation sources."""
    records: dict[str, dict[str, Any]] = {}
    for source in sources:
        key = source_cache_key(source)
        record = records.setdefault(
            key,
            {
                "key": key,
                "normalized_url": normalize_url(str(source.get("url", ""))),
                "url": source.get("url", ""),
                "title": source.get("title", ""),
                "grade": source.get("grade", ""),
                "ids": [],
                "seen_count": 0,
            },
        )
        source_id = source.get("id")
        if source_id is not None and str(source_id) not in record["ids"]:
            record["ids"].append(str(source_id))
        record["seen_count"] += 1
        if source.get("grade") and not record.get("grade"):
            record["grade"] = source["grade"]

    return {
        "schema_version": 1,
        "source_count": len(records),
        "sources": [records[key] for key in sorted(records)],
    }


def write_source_cache(citations_path: str | Path, cache_path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(citations_path).read_text(encoding="utf-8"))
    cache = build_source_cache(citation_sources(payload))
    output_path = Path(cache_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "created", "cache_path": str(output_path), "source_count": cache["source_count"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a normalized source cache from citations.json.")
    parser.add_argument("citations_json")
    parser.add_argument("cache_json")
    args = parser.parse_args(argv)

    try:
        payload = write_source_cache(args.citations_json, args.cache_json)
    except Exception as exc:  # noqa: BLE001 - CLI reports structured failures.
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
