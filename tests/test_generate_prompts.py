from __future__ import annotations

import json
import sys

from helpers import load_module


generate_prompts = load_module(
    "test_generate_prompts_module",
    ".claude/skills/image-generator/scripts/generate_prompts.py",
)


def test_load_template_prefers_specific_template(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "architecture.txt").write_text("Architecture: {description}", encoding="utf-8")
    (templates_dir / "generic.txt").write_text("Generic: {description}", encoding="utf-8")

    template = generate_prompts.load_template(str(templates_dir), "architecture")

    assert template == "Architecture: {description}"


def test_load_template_falls_back_to_generic_template(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "generic.txt").write_text("Generic: {description}", encoding="utf-8")

    template = generate_prompts.load_template(str(templates_dir), "metaphor")

    assert template == "Generic: {description}"


def test_load_template_uses_hardcoded_fallback_when_no_templates_exist(tmp_path):
    template = generate_prompts.load_template(str(tmp_path / "missing"), "architecture")

    assert "professional infographic" in template
    assert "{description}" in template


def test_main_generates_prompts_in_place_for_list_manifest(tmp_path, monkeypatch, capsys):
    manifest_path = tmp_path / "image_manifest.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "architecture.txt").write_text("Prompt: {description}", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            [
                {"image_type": "architecture", "description": "System overview", "prompt": None},
                {"image_type": "architecture", "description": "Keep me", "prompt": "existing"},
                {"image_type": "architecture", "description": "", "prompt": None},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_prompts.py",
            "--manifest",
            str(manifest_path),
            "--templates",
            str(templates_dir),
        ],
    )
    generate_prompts.main()
    output = capsys.readouterr()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest[0]["prompt"] == "Prompt: System overview"
    assert manifest[1]["prompt"] == "existing"
    assert manifest[2]["prompt"] is None
    assert "Generated 1 prompts" in output.out


def test_main_supports_entries_manifest_shape(tmp_path, monkeypatch):
    manifest_path = tmp_path / "image_manifest.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "generic.txt").write_text("Generic: {description}", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "entries": [
                    {"image_type": "unknown", "description": "Fallback example", "prompt": None}
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_prompts.py",
            "--manifest",
            str(manifest_path),
            "--templates",
            str(templates_dir),
        ],
    )
    generate_prompts.main()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["entries"][0]["prompt"] == "Generic: Fallback example"
