#!/usr/bin/env python3
"""Chunk user reference materials into bounded JSON files."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any


SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf", ".docx"}
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "are",
    "was",
    "were",
    "have",
    "has",
    "you",
    "your",
    "to",
    "of",
    "in",
    "on",
    "a",
    "an",
}
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")


class ReferenceParseError(RuntimeError):
    """Raised when a reference file cannot be parsed."""


def safe_name(path: str | Path) -> str:
    """Return a stable directory-safe name for a source file."""
    source = Path(path)
    raw = f"{source.stem}_{source.suffix.lstrip('.')}" if source.suffix else source.stem
    name = re.sub(r"[^0-9A-Za-z가-힣]+", "_", raw).strip("_").lower()
    return name or "reference"


def parse_text(file_path: str | Path) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def parse_pdf(file_path: str | Path) -> str:
    """Extract text from PDF using common local tools."""
    commands = [
        ["textutil", "-convert", "txt", "-stdout", str(file_path)],
        ["pdftotext", str(file_path), "-"],
    ]
    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    raise ReferenceParseError(f"No PDF parser available for {file_path}")


def parse_docx(file_path: str | Path) -> str:
    """Extract paragraph text from a DOCX document."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        with zipfile.ZipFile(file_path, "r") as archive:
            xml_content = archive.read("word/document.xml")
        root = ET.fromstring(xml_content)
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise ReferenceParseError(f"DOCX parsing failed: {exc}") from exc

    paragraphs: list[str] = []
    for para in root.iter(f"{{{ns['w']}}}p"):
        texts = [run.text for run in para.iter(f"{{{ns['w']}}}t") if run.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n\n".join(paragraphs)


def parse_reference(file_path: str | Path) -> tuple[str, str]:
    """Return extracted text and content type for a supported reference file."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".md":
        return parse_text(path), "markdown"
    if suffix == ".txt":
        return parse_text(path), "text"
    if suffix == ".pdf":
        return parse_pdf(path), "pdf"
    if suffix == ".docx":
        return parse_docx(path), "docx"
    raise ReferenceParseError(f"Unsupported file type: {suffix}")


def keywords_for_text(text: str, limit: int = 12) -> list[str]:
    tokens = [
        token.casefold()
        for token in TOKEN_RE.findall(text)
        if token.casefold() not in STOPWORDS
    ]
    return [token for token, _count in Counter(tokens).most_common(limit)]


def chunk_text(text: str, chunk_words: int = 900, overlap_words: int = 90) -> list[dict[str, Any]]:
    """Split text into overlapping word chunks."""
    if chunk_words <= 0:
        raise ValueError("chunk_words must be positive")
    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative")
    if overlap_words >= chunk_words:
        raise ValueError("overlap_words must be smaller than chunk_words")

    words = text.split()
    if not words:
        return []

    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_words, len(words))
        chunk_body = " ".join(words[start:end])
        chunks.append(
            {
                "index": len(chunks) + 1,
                "word_start": start,
                "word_end": end,
                "word_count": end - start,
                "text": chunk_body,
                "keywords": keywords_for_text(chunk_body),
            }
        )
        if end == len(words):
            break
        start = end - overlap_words
    return chunks


def write_chunks_for_text(
    source_file: str | Path,
    content_type: str,
    text: str,
    output_root: str | Path,
    chunk_words: int = 900,
    overlap_words: int = 90,
) -> dict[str, Any]:
    """Write chunk JSON files and a per-source manifest."""
    source_path = Path(source_file)
    source_dir = Path(output_root) / safe_name(source_path)
    source_dir.mkdir(parents=True, exist_ok=True)

    chunks = chunk_text(text, chunk_words=chunk_words, overlap_words=overlap_words)
    chunk_entries: list[dict[str, Any]] = []
    for chunk in chunks:
        chunk_id = f"{safe_name(source_path)}_{chunk['index']:03d}"
        chunk_path = source_dir / f"chunk_{chunk['index']:03d}.json"
        payload = {
            "source_file": str(source_path),
            "content_type": content_type,
            "chunk_id": chunk_id,
            "chunk_index": chunk["index"],
            "word_start": chunk["word_start"],
            "word_end": chunk["word_end"],
            "word_count": chunk["word_count"],
            "keywords": chunk["keywords"],
            "text": chunk["text"],
        }
        chunk_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        chunk_entries.append(
            {
                "chunk_id": chunk_id,
                "path": str(chunk_path),
                "word_start": chunk["word_start"],
                "word_end": chunk["word_end"],
                "word_count": chunk["word_count"],
                "keywords": chunk["keywords"],
            }
        )

    manifest = {
        "status": "created",
        "source_file": str(source_path),
        "content_type": content_type,
        "word_count": len(text.split()),
        "chunk_count": len(chunk_entries),
        "chunks": chunk_entries,
    }
    manifest_path = source_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def iter_reference_files(path: str | Path) -> list[Path]:
    """Return supported reference files from a file or directory."""
    root = Path(path)
    if root.is_file():
        return [root] if root.suffix.lower() in SUPPORTED_SUFFIXES else []
    if not root.is_dir():
        raise FileNotFoundError(f"Reference path not found: {path}")
    return sorted(
        file_path
        for file_path in root.rglob("*")
        if file_path.is_file()
        and not file_path.name.startswith(".")
        and file_path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def chunk_reference_path(
    reference_path: str | Path,
    output_dir: str | Path,
    chunk_words: int = 900,
    overlap_words: int = 90,
) -> dict[str, Any]:
    """Chunk a reference file or directory and write a global manifest."""
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    manifests: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for file_path in iter_reference_files(reference_path):
        try:
            text, content_type = parse_reference(file_path)
            manifests.append(
                write_chunks_for_text(
                    file_path,
                    content_type,
                    text,
                    output_root,
                    chunk_words=chunk_words,
                    overlap_words=overlap_words,
                )
            )
        except Exception as exc:  # noqa: BLE001 - reference ingestion should continue per file.
            errors.append({"source_file": str(file_path), "error": str(exc)})

    payload = {
        "status": "created" if not errors else "partial",
        "output_dir": str(output_root),
        "file_count": len(manifests),
        "files": manifests,
        "errors": errors,
    }
    manifest_path = output_root / "reference_chunks_manifest.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload["manifest_path"] = str(manifest_path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chunk reference materials into bounded JSON files.")
    parser.add_argument("reference_path", help="Reference file or directory.")
    parser.add_argument("--output-dir", default="output/research/reference_chunks")
    parser.add_argument("--chunk-words", type=int, default=900)
    parser.add_argument("--overlap-words", type=int, default=90)
    args = parser.parse_args(argv)

    try:
        payload = chunk_reference_path(
            args.reference_path,
            args.output_dir,
            chunk_words=args.chunk_words,
            overlap_words=args.overlap_words,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should return structured failures.
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] in {"created", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
