from __future__ import annotations

import json
from argparse import Namespace

from helpers import load_module


validate_final_pdf = load_module("validate_final_pdf_module", "scripts/validate_final_pdf.py")
validate_images = load_module("validate_images_module", "scripts/validate_images.py")
validate_web_viewer = load_module("validate_web_viewer_module", "scripts/validate_web_viewer.py")
final_preflight = load_module("final_preflight_module", "scripts/final_preflight.py")


def make_pdf(path, text: str) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_validate_images_blocks_failed_entries_and_accepts_svg(tmp_path) -> None:
    chapter = tmp_path / "ch01_intro.md"
    chapter.write_text("# 제1장: 소개\n", encoding="utf-8")
    image = tmp_path / "diagram.svg"
    image.write_text("<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>", encoding="utf-8")
    manifest = tmp_path / "image_manifest.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "marker_id": "ch01_img01",
                    "chapter_file": str(chapter),
                    "description": "diagram",
                    "line_number": 2,
                    "provider": "diagram",
                    "output_path": str(image),
                    "status": "completed",
                },
                {
                    "marker_id": "ch01_img02",
                    "chapter_file": str(chapter),
                    "description": "failed",
                    "line_number": 3,
                    "provider": "gemini",
                    "output_path": str(tmp_path / "missing.png"),
                    "status": "failed",
                },
            ]
        ),
        encoding="utf-8",
    )

    result = validate_images.validate_images(manifest)

    assert result["status"] == "failed"
    assert any(issue["code"] == "failed_image_entry" for issue in result["issues"])


def test_validate_final_pdf_blocks_raw_markers_and_wrong_language_label(tmp_path) -> None:
    pdf_path = tmp_path / "book_ko.pdf"
    make_pdf(pdf_path, "Chapter 1\nTODO\n[IMAGE: diagram]\n[^1]")

    result = validate_final_pdf.validate_final_pdf(pdf_path, "ko", min_size=0)
    codes = {issue["code"] for issue in result["issues"]}

    assert result["status"] == "failed"
    assert "unexpected_english_chapter_label" in codes
    assert "pdf_todo_placeholder" in codes
    assert "forbidden_pdf_text" in codes
    assert "raw_pdf_footnote_marker" in codes


def test_validate_web_viewer_blocks_single_language_toggle_and_placeholders(tmp_path) -> None:
    viewer = tmp_path / "viewer"
    viewer.mkdir()
    (viewer / "book_ko.pdf").write_bytes(b"%PDF-1.4\n")
    (viewer / "index.html").write_text(
        "<html>{{TITLE}}<button id=\"bk\">KO</button><script>const pdf='book_ko.pdf'</script></html>",
        encoding="utf-8",
    )

    result = validate_web_viewer.validate_web_viewer(viewer, "book_ko.pdf", bilingual=False)
    codes = {issue["code"] for issue in result["issues"]}

    assert result["status"] == "failed"
    assert "unreplaced_viewer_placeholder" in codes
    assert "single_language_toggle_visible" in codes


def test_final_preflight_runs_selected_validators(tmp_path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    (chapters / "ch01_intro.md").write_text(
        "# Chapter 1: Intro\n\nBody.[^1]\n\n[^1]: Source\n",
        encoding="utf-8",
    )
    citations = tmp_path / "citations.json"
    citations.write_text(json.dumps({"citations": [{"id": 1, "title": "Source"}]}), encoding="utf-8")

    args = Namespace(
        primary_chapters=str(chapters),
        primary_language="en",
        secondary_chapters=None,
        secondary_language="ko",
        bilingual=False,
        citations=str(citations),
        image_manifest=None,
        primary_pdf=None,
        secondary_pdf=None,
        viewer_dir=None,
        min_pdf_size=0,
    )

    result = final_preflight.run_preflight(args)

    assert result["status"] == "passed"
    assert result["summary"]["validators_run"] == ["validate_chapters"]
