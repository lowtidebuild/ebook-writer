#!/usr/bin/env python3
"""Review generated image files and write validation metadata back to the manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_images import validate_image_format


def manifest_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        for key in ("images", "entries", "manifest"):
            value = payload.get(key)
            if isinstance(value, list):
                return [entry for entry in value if isinstance(entry, dict)]
    return []


def review_manifest(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    entries = manifest_entries(manifest)
    reviewed = 0
    failed = 0

    for entry in entries:
        blocking: list[str] = []
        output_path_value = entry.get("output_path")
        if not output_path_value:
            blocking.append("missing output_path")
        else:
            output_path = Path(output_path_value)
            if not output_path.is_file():
                blocking.append("output file does not exist")
            elif output_path.stat().st_size == 0:
                blocking.append("output file is empty")
            else:
                format_error = validate_image_format(output_path)
                if format_error:
                    blocking.append(format_error)

        entry["blocking_issues"] = blocking
        if blocking:
            entry["status"] = "failed"
            failed += 1
        elif entry.get("status") == "completed":
            reviewed += 1
            entry.setdefault("quality_score", 8 if entry.get("provider") == "diagram" else None)

    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "failed" if failed else "passed", "reviewed": reviewed, "failed": failed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Review image manifest output files.")
    parser.add_argument("manifest")
    args = parser.parse_args()
    print(json.dumps(review_manifest(args.manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
