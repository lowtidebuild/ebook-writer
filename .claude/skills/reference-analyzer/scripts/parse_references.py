#!/usr/bin/env python3
"""Parse reference files and extract text content.

Usage:
    .venv/bin/python3 .claude/skills/reference-analyzer/scripts/parse_references.py <file_path>
    .venv/bin/python3 .claude/skills/reference-analyzer/scripts/parse_references.py <file_path> --output-dir output/research/reference_chunks/source_pdf/

Supports: .md, .txt, .pdf, .docx
Output: JSON to stdout. With --output-dir, stdout contains only status and
manifest paths; extracted text is written to bounded chunk files.
"""

import argparse
import json
import os
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_markdown(file_path: str) -> str:
    """Read markdown or text file content."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_pdf(file_path: str) -> str:
    """Extract text from PDF using available system tools."""
    # Try textutil (macOS native)
    try:
        result = subprocess.run(
            ["textutil", "-convert", "txt", "-stdout", file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try pdftotext (poppler)
    try:
        result = subprocess.run(
            ["pdftotext", file_path, "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    raise RuntimeError(f"No PDF parser available for {file_path}")


def parse_docx(file_path: str) -> str:
    """Extract text from DOCX by reading the XML content."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            xml_content = z.read("word/document.xml")
        root = ET.fromstring(xml_content)
        paragraphs = []
        for para in root.iter(f"{{{ns['w']}}}p"):
            texts = []
            for run in para.iter(f"{{{ns['w']}}}t"):
                if run.text:
                    texts.append(run.text)
            if texts:
                paragraphs.append("".join(texts))
        return "\n\n".join(paragraphs)
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as e:
        raise RuntimeError(f"DOCX parsing failed: {e}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse and optionally chunk a reference file.")
    parser.add_argument("file_path")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--chunk-words", type=int, default=900)
    parser.add_argument("--overlap-words", type=int, default=90)
    return parser.parse_args(argv)


def write_chunk_output(
    file_path: str,
    content_type: str,
    extracted_text: str,
    output_dir: str,
    chunk_words: int,
    overlap_words: int,
) -> dict:
    """Write bounded chunk files via the repository chunking utility."""
    repo_root = Path(__file__).resolve().parents[4]
    scripts_dir = str(repo_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    from chunk_references import write_chunks_for_text  # noqa: PLC0415

    manifest = write_chunks_for_text(
        file_path,
        content_type,
        extracted_text,
        output_dir,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
    )
    return {
        "filename": os.path.basename(file_path),
        "content_type": content_type,
        "word_count": manifest["word_count"],
        "chunk_count": manifest["chunk_count"],
        "manifest_path": manifest["manifest_path"],
        "status": "success",
    }


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    file_path = args.file_path

    if not os.path.exists(file_path):
        print(json.dumps({"status": "error", "error": f"File not found: {file_path}"}))
        sys.exit(1)

    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    parsers = {
        ".md": ("markdown", parse_markdown),
        ".txt": ("text", parse_markdown),
        ".pdf": ("pdf", parse_pdf),
        ".docx": ("docx", parse_docx),
    }

    if ext not in parsers:
        print(json.dumps({
            "filename": filename,
            "content_type": ext.lstrip("."),
            "status": "unsupported",
            "error": f"Unsupported file type: {ext}",
        }))
        sys.exit(1)

    content_type, parser_fn = parsers[ext]

    try:
        extracted_text = parser_fn(file_path)
        word_count = len(extracted_text.split())
        if args.output_dir:
            payload = write_chunk_output(
                file_path,
                content_type,
                extracted_text,
                args.output_dir,
                args.chunk_words,
                args.overlap_words,
            )
            print(json.dumps(payload, ensure_ascii=False))
            return

        print(json.dumps({
            "filename": filename,
            "content_type": content_type,
            "extracted_text": extracted_text,
            "word_count": word_count,
            "status": "success",
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            "filename": filename,
            "content_type": content_type,
            "status": "failed",
            "error": str(e),
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
