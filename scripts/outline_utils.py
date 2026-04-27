#!/usr/bin/env python3
"""Structured outline validation and rendering helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class OutlineError(ValueError):
    """Raised when an outline cannot be used for pipeline execution."""


def load_outline(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_outline(outline: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not isinstance(outline, dict):
        return ["outline must be a JSON object"]

    for field in ("book_title", "target_audience", "chapters"):
        if field not in outline:
            errors.append(f"{field} is required")

    chapters = outline.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        errors.append("chapters must be a non-empty array")
        return errors

    ids: list[int] = []
    slugs: list[str] = []
    for index, chapter in enumerate(chapters, start=1):
        path = f"chapters[{index}]"
        if not isinstance(chapter, dict):
            errors.append(f"{path} must be an object")
            continue

        chapter_id = chapter.get("chapter_id")
        if not isinstance(chapter_id, int) or chapter_id < 1:
            errors.append(f"{path}.chapter_id must be a positive integer")
        else:
            ids.append(chapter_id)

        slug = chapter.get("slug")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            errors.append(f"{path}.slug must be lowercase kebab-case")
        else:
            slugs.append(slug)

        for field in ("title", "summary"):
            if not isinstance(chapter.get(field), str) or not chapter[field].strip():
                errors.append(f"{path}.{field} is required")

        key_content = chapter.get("key_content")
        if not isinstance(key_content, list) or not key_content:
            errors.append(f"{path}.key_content must be a non-empty array")
        elif any(not isinstance(item, str) or not item.strip() for item in key_content):
            errors.append(f"{path}.key_content items must be non-empty strings")

        estimated_words = chapter.get("estimated_words")
        if not isinstance(estimated_words, int) or estimated_words <= 0:
            errors.append(f"{path}.estimated_words must be a positive integer")

        dependencies = chapter.get("dependencies")
        if not isinstance(dependencies, list):
            errors.append(f"{path}.dependencies must be an array")
        elif any(not isinstance(dep, int) or dep < 1 for dep in dependencies):
            errors.append(f"{path}.dependencies must contain positive integers")

    if len(ids) != len(set(ids)):
        errors.append("chapter_id values must be unique")
    if len(slugs) != len(set(slugs)):
        errors.append("chapter slugs must be unique")

    if ids:
        expected_ids = list(range(1, len(chapters) + 1))
        if sorted(ids) != expected_ids:
            errors.append(
                "chapter_id values must be contiguous and start at 1 "
                f"(expected {expected_ids})"
            )

    id_set = set(ids)
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        chapter_id = chapter.get("chapter_id")
        dependencies = chapter.get("dependencies")
        if not isinstance(chapter_id, int) or not isinstance(dependencies, list):
            continue
        for dep in dependencies:
            if not isinstance(dep, int):
                continue
            if dep == chapter_id:
                errors.append(f"Chapter {chapter_id} cannot depend on itself")
            elif dep not in id_set:
                errors.append(f"Chapter {chapter_id} depends on missing Chapter {dep}")

    cycle = find_dependency_cycle(outline)
    if cycle:
        cycle_text = " -> ".join(f"Chapter {chapter_id}" for chapter_id in cycle)
        errors.append(f"Dependency cycle detected: {cycle_text}")

    return errors


def find_dependency_cycle(outline: dict[str, Any]) -> list[int] | None:
    chapters = outline.get("chapters")
    if not isinstance(chapters, list):
        return None

    graph: dict[int, list[int]] = {}
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        chapter_id = chapter.get("chapter_id")
        dependencies = chapter.get("dependencies", [])
        if isinstance(chapter_id, int) and isinstance(dependencies, list):
            graph[chapter_id] = [dep for dep in dependencies if isinstance(dep, int)]

    visiting: set[int] = set()
    visited: set[int] = set()
    stack: list[int] = []

    def dfs(chapter_id: int) -> list[int] | None:
        if chapter_id in visiting:
            start = stack.index(chapter_id)
            return stack[start:] + [chapter_id]
        if chapter_id in visited:
            return None

        visiting.add(chapter_id)
        stack.append(chapter_id)
        for dependency_id in graph.get(chapter_id, []):
            if dependency_id not in graph:
                continue
            cycle = dfs(dependency_id)
            if cycle:
                return cycle
        stack.pop()
        visiting.remove(chapter_id)
        visited.add(chapter_id)
        return None

    for chapter_id in sorted(graph):
        cycle = dfs(chapter_id)
        if cycle:
            return cycle
    return None


def dependency_waves(outline: dict[str, Any]) -> list[list[int]]:
    errors = validate_outline(outline)
    if errors:
        raise OutlineError("; ".join(errors))

    chapters = outline["chapters"]
    remaining = {chapter["chapter_id"]: set(chapter["dependencies"]) for chapter in chapters}
    completed: set[int] = set()
    waves: list[list[int]] = []

    while remaining:
        ready = sorted(
            chapter_id
            for chapter_id, dependencies in remaining.items()
            if dependencies.issubset(completed)
        )
        if not ready:
            raise OutlineError("Unable to build dependency waves from outline")
        waves.append(ready)
        completed.update(ready)
        for chapter_id in ready:
            remaining.pop(chapter_id)

    return waves


def chapter_state_entries(outline: dict[str, Any]) -> list[dict[str, Any]]:
    errors = validate_outline(outline)
    if errors:
        raise OutlineError("; ".join(errors))

    return [
        {
            "chapter_id": chapter["chapter_id"],
            "slug": chapter["slug"],
            "title": chapter["title"],
            "dependencies": list(chapter["dependencies"]),
            "write_status": "pending",
        }
        for chapter in outline["chapters"]
    ]


def render_outline_markdown(outline: dict[str, Any]) -> str:
    errors = validate_outline(outline)
    if errors:
        raise OutlineError("; ".join(errors))

    total_words = sum(chapter["estimated_words"] for chapter in outline["chapters"])
    lines = [
        f"# {outline['book_title']}",
        "",
        f"**Target Audience**: {outline['target_audience']}",
        f"**Estimated Total Length**: ~{total_words} words",
        f"**Total Chapters**: {len(outline['chapters'])}",
        "",
        "---",
        "",
    ]

    current_part = None
    for chapter in outline["chapters"]:
        part = chapter.get("part")
        if part and part != current_part:
            lines.extend([f"## {part}", ""])
            current_part = part

        dependencies = (
            "none"
            if not chapter["dependencies"]
            else "[" + ", ".join(str(dep) for dep in chapter["dependencies"]) + "]"
        )
        lines.extend(
            [
                f"### Chapter {chapter['chapter_id']}: {chapter['title']}",
                f"- **Slug**: `{chapter['slug']}`",
                f"- **Summary**: {chapter['summary']}",
                "- **Key Content**:",
            ]
        )
        lines.extend(f"  - {item}" for item in chapter["key_content"])
        lines.extend(
            [
                f"- **Estimated Length**: ~{chapter['estimated_words']} words",
                f"- **Dependencies**: {dependencies}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def normalized_markdown(markdown: str) -> str:
    lines = [line.rstrip() for line in markdown.strip().splitlines()]
    return "\n".join(lines) + "\n"
