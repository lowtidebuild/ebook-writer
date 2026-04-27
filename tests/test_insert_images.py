from __future__ import annotations

import json

from helpers import load_module


insert_images = load_module(
    "test_insert_images_module",
    ".claude/skills/image-generator/scripts/insert_images.py",
)


def test_build_replacement_uses_manifest_output_path_and_preserves_extension(tmp_path):
    chapter_path = tmp_path / "output" / "chapters" / "ko" / "ch01_intro.md"
    image_path = tmp_path / "output" / "images" / "ch01_img01.svg"
    chapter_path.parent.mkdir(parents=True)
    image_path.parent.mkdir(parents=True)
    image_path.write_text("<svg></svg>", encoding="utf-8")

    replacement = insert_images.build_replacement(
        {
            "marker_id": "ch01_img01",
            "description": "구조도",
            "status": "completed",
            "output_path": str(image_path),
        },
        chapter_path,
    )

    assert replacement == "![구조도](../../images/ch01_img01.svg)"


def test_insert_images_replaces_marker_with_relative_svg_path(tmp_path):
    chapter_path = tmp_path / "output" / "chapters" / "ko" / "ch01_intro.md"
    image_path = tmp_path / "output" / "images" / "ch01_img01.svg"
    manifest_path = tmp_path / "output" / "images" / "image_manifest.json"
    chapter_path.parent.mkdir(parents=True)
    image_path.parent.mkdir(parents=True)
    chapter_path.write_text(
        "# 제1장: 소개\n\n[IMAGE: 구조도]\n",
        encoding="utf-8",
    )
    image_path.write_text("<svg></svg>", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "marker_id": "ch01_img01",
                    "chapter_file": str(chapter_path),
                    "description": "구조도",
                    "status": "completed",
                    "output_path": str(image_path),
                }
            ]
        ),
        encoding="utf-8",
    )

    insert_images.insert_images(str(manifest_path), str(chapter_path.parent))

    assert "![구조도](../../images/ch01_img01.svg)" in chapter_path.read_text(
        encoding="utf-8"
    )
