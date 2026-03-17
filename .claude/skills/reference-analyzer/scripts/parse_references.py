#!/usr/bin/env python3
"""Parse reference files and extract text content.

Usage:
    python3 parse_references.py <file_path>

Supports: .md, .txt, .pdf, .docx
Output: JSON to stdout
"""

import json
import os
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET


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


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"status": "error", "error": "Usage: parse_references.py <file_path>"}))
        sys.exit(1)

    file_path = sys.argv[1]

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
