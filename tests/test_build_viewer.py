from __future__ import annotations

import sys

from helpers import REPO_ROOT, load_module


build_viewer = load_module(
    "test_build_viewer_module",
    ".claude/skills/web-viewer-builder/scripts/build_viewer.py",
)


def test_build_language_toggle_is_empty_for_single_language():
    assert build_viewer.build_language_toggle("한국어", "English", False) == ""


def test_apply_template_replacements_fails_on_remaining_placeholder():
    try:
        build_viewer.apply_template_replacements("{{KNOWN}} {{MISSING}}", {"{{KNOWN}}": "ok"})
    except ValueError as exc:
        assert "{{MISSING}}" in str(exc)
    else:
        raise AssertionError("Expected unreplaced placeholder to fail")


def test_main_hides_secondary_toggle_when_secondary_pdf_missing(tmp_path, monkeypatch):
    primary_pdf = tmp_path / "book_ko.pdf"
    primary_pdf.write_bytes(b"%PDF-1.4\n% fake\n")
    out_dir = tmp_path / "viewer"
    template_path = (
        REPO_ROOT
        / ".claude"
        / "skills"
        / "web-viewer-builder"
        / "references"
        / "viewer_template.html"
    )

    monkeypatch.setattr(build_viewer, "extract_toc", lambda pdf_path: [])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_viewer.py",
            "--pdf-primary",
            str(primary_pdf),
            "--output",
            str(out_dir),
            "--template",
            str(template_path),
            "--title",
            "테스트 책",
            "--primary-lang",
            "ko",
            "--secondary-lang",
            "en",
        ],
    )

    build_viewer.main()
    html = (out_dir / "index.html").read_text(encoding="utf-8")

    assert 'id="be"' not in html
    assert 'id="bk"' not in html
    assert "{{" not in html
    assert (out_dir / "book_ko.pdf").is_file()
    assert not (out_dir / "book_en.pdf").exists()
