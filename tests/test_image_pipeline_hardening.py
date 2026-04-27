from __future__ import annotations

import json

from helpers import load_module


extract_markers = load_module(
    "extract_markers_module",
    ".claude/skills/image-generator/scripts/extract_markers.py",
)
generate_prompts = load_module(
    "generate_prompts_module",
    ".claude/skills/image-generator/scripts/generate_prompts.py",
)
insert_images = load_module(
    "insert_images_hardening_module",
    ".claude/skills/image-generator/scripts/insert_images.py",
)
render_diagrams = load_module("render_diagrams_module", "scripts/render_diagrams.py")
review_images = load_module("review_images_module", "scripts/review_images.py")


def test_extract_markers_defers_output_extension_until_provider_routing(tmp_path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    (chapters / "ch01_intro.md").write_text("[IMAGE: 프로세스 흐름]\n", encoding="utf-8")
    manifest = tmp_path / "images" / "image_manifest.json"

    extract_markers.extract_markers(str(chapters), str(manifest))
    entries = json.loads(manifest.read_text(encoding="utf-8"))

    assert entries[0]["output_path"] is None
    assert entries[0]["output_stem"].endswith("ch01_img01")


def test_generate_prompts_routes_text_heavy_diagrams_to_local_svg(tmp_path, monkeypatch) -> None:
    manifest = tmp_path / "images" / "image_manifest.json"
    templates = tmp_path / "templates"
    manifest.parent.mkdir()
    templates.mkdir()
    (templates / "process_flow.txt").write_text("Flow: {description}", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            [
                {
                    "marker_id": "ch01_img01",
                    "chapter_file": "ch01.md",
                    "description": "A -> B",
                    "line_number": 1,
                    "image_type": "process_flow",
                    "output_stem": str(tmp_path / "images" / "ch01_img01"),
                    "output_path": None,
                    "status": "pending",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        generate_prompts.sys,
        "argv",
        [
            "generate_prompts.py",
            "--manifest",
            str(manifest),
            "--templates",
            str(templates),
        ],
    )

    generate_prompts.main()
    entry = json.loads(manifest.read_text(encoding="utf-8"))[0]

    assert entry["provider"] == "diagram"
    assert entry["output_path"].endswith(".svg")
    assert entry["prompt"] == "Flow: A -> B"


def test_render_diagrams_updates_manifest_and_writes_svg(tmp_path) -> None:
    manifest = tmp_path / "image_manifest.json"
    output_path = tmp_path / "diagram.svg"
    manifest.write_text(
        json.dumps(
            [
                {
                    "marker_id": "ch01_img01",
                    "description": "draft -> review -> publish",
                    "image_type": "process_flow",
                    "provider": "diagram",
                    "output_path": str(output_path),
                    "status": "pending",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = render_diagrams.render_manifest(manifest)
    entry = json.loads(manifest.read_text(encoding="utf-8"))[0]

    assert result["rendered"] == 1
    assert entry["status"] == "completed"
    assert "<svg" in output_path.read_text(encoding="utf-8")


def test_failed_image_insertion_uses_neutral_caption_not_failure_placeholder(tmp_path) -> None:
    replacement = insert_images.build_replacement(
        {
            "marker_id": "ch01_img01",
            "description": "missing diagram",
            "status": "failed",
        },
        tmp_path / "ch01_intro.md",
    )

    assert "[이미지 생성 실패]" not in replacement
    assert "[IMAGE:" not in replacement
    assert "Image omitted" in replacement


def test_review_images_marks_invalid_completed_file_failed(tmp_path) -> None:
    chapter = tmp_path / "ch01_intro.md"
    image = tmp_path / "bad.svg"
    manifest = tmp_path / "image_manifest.json"
    chapter.write_text("# Chapter 1: Intro\n", encoding="utf-8")
    image.write_text("not svg", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            [
                {
                    "marker_id": "ch01_img01",
                    "chapter_file": str(chapter),
                    "description": "bad",
                    "line_number": 1,
                    "provider": "diagram",
                    "output_path": str(image),
                    "status": "completed",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = review_images.review_manifest(manifest)
    entry = json.loads(manifest.read_text(encoding="utf-8"))[0]

    assert result["status"] == "failed"
    assert entry["status"] == "failed"
    assert entry["blocking_issues"]
