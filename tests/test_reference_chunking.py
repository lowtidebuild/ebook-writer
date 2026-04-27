from __future__ import annotations

import json

from helpers import load_module


chunk_references = load_module("chunk_references_module", "scripts/chunk_references.py")
source_cache = load_module("source_cache_module", "scripts/source_cache.py")
research_summary = load_module(
    "research_summary_module",
    "scripts/summarize_research_for_outline.py",
)
dependency_summaries = load_module(
    "dependency_summaries_module",
    "scripts/build_dependency_summaries.py",
)
parse_references = load_module(
    "parse_references_for_chunking_module",
    ".claude/skills/reference-analyzer/scripts/parse_references.py",
)


def test_chunk_reference_path_writes_manifest_and_bounded_chunks(tmp_path) -> None:
    references = tmp_path / "references"
    references.mkdir()
    (references / "source.txt").write_text(" ".join(f"word{i}" for i in range(130)), encoding="utf-8")

    manifest = chunk_references.chunk_reference_path(
        references,
        tmp_path / "chunks",
        chunk_words=50,
        overlap_words=10,
    )

    assert manifest["status"] == "created"
    assert manifest["file_count"] == 1
    assert manifest["files"][0]["chunk_count"] == 3
    chunk_path = tmp_path / "chunks" / "source_txt" / "chunk_001.json"
    chunk = json.loads(chunk_path.read_text(encoding="utf-8"))
    assert chunk["word_count"] == 50
    assert "text" in chunk


def test_parse_references_output_dir_omits_extracted_text_from_stdout(tmp_path, capsys) -> None:
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\n" + "alpha beta gamma " * 40, encoding="utf-8")

    parse_references.main(
        [
            str(source),
            "--output-dir",
            str(tmp_path / "chunks"),
            "--chunk-words",
            "30",
            "--overlap-words",
            "5",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "success"
    assert payload["chunk_count"] > 1
    assert "manifest_path" in payload
    assert "extracted_text" not in payload


def test_source_cache_normalizes_duplicate_tracking_urls() -> None:
    cache = source_cache.build_source_cache(
        [
            {"id": 1, "url": "HTTPS://Example.com/Page/?utm_source=x&b=2", "title": "A"},
            {"id": 2, "url": "https://example.com/Page?b=2#section", "title": "A"},
        ]
    )

    assert cache["source_count"] == 1
    assert cache["sources"][0]["normalized_url"] == "https://example.com/Page?b=2"
    assert cache["sources"][0]["ids"] == ["1", "2"]


def test_research_summary_limits_sections_and_words(tmp_path) -> None:
    report = tmp_path / "research.md"
    output = tmp_path / "summary.md"
    report.write_text(
        "# Research\n\n"
        "## Topic A\n\n"
        + " ".join(f"a{i}" for i in range(40))
        + "\n\n## Topic B\n\n"
        + " ".join(f"b{i}" for i in range(40)),
        encoding="utf-8",
    )

    payload = research_summary.write_research_summary(
        report,
        output,
        max_sections=1,
        max_words_per_section=10,
    )
    summary = output.read_text(encoding="utf-8")

    assert payload["status"] == "created"
    assert "## Topic A" in summary
    assert "## Topic B" not in summary
    assert "Omitted 1 lower-priority sections" in summary


def test_dependency_summaries_extract_title_headings_and_manifest(tmp_path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    (chapters / "ch01_intro.md").write_text(
        "# Chapter 1: Intro\n\n"
        "This chapter introduces the main concept in a compact way.\n\n"
        "## Core Idea\n\n"
        "Details.",
        encoding="utf-8",
    )

    manifest = dependency_summaries.build_dependency_summaries(chapters, tmp_path / "summaries")
    summary_path = tmp_path / "summaries" / "ch01_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert manifest["chapter_count"] == 1
    assert summary["chapter_number"] == 1
    assert summary["title"] == "Chapter 1: Intro"
    assert summary["headings"][1]["title"] == "Core Idea"
