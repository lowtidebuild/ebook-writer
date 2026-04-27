#!/usr/bin/env python3
"""
generate_images.py - Generate images for pending manifest entries.

Dispatches each entry to its configured provider:
  - "diagram": Local deterministic SVG renderer for architecture, process flow,
    and comparison diagrams.
  - "codex": god-tibo-imagen (gti) via the user's local Codex CLI auth.
    Optional override. Relies on ChatGPT's private backend — unsupported and may break.
  - "gemini": Google Gemini multimodal image output. Default for illustrative
    content (concept_diagram, metaphor).
  - "openai": Paid OpenAI Images API (gpt-image-*). Explicit override only.

The provider for each entry is set by generate_prompts.py based on image_type
(or by the IMAGE_PROVIDER env var override). It can also be edited directly
in the manifest before running this script.

Usage:
    .venv/bin/python3 .claude/skills/image-generator/scripts/generate_images.py <manifest_json_path>

Example:
    .venv/bin/python3 .claude/skills/image-generator/scripts/generate_images.py output/images/image_manifest.json

Environment variables:
    GEMINI_API_KEY        - Required when any entry uses provider="gemini"
    OPENAI_API_KEY        - Required when any entry uses provider="openai"
    IMAGE_MODEL           - Gemini model name (default: gemini-3.1-flash-image-preview)
    OPENAI_IMAGE_MODEL    - OpenAI image model name (default: gpt-image-1)
    OPENAI_IMAGE_SIZE     - OpenAI output size (default: 1536x1024)
    OPENAI_IMAGE_QUALITY  - OpenAI quality: low|medium|high (default: high)
    CODEX_IMAGE_MODEL     - Codex (gti) model name (default: gpt-5.4)

Codex provider requires that Codex CLI is logged in locally
(~/.codex/auth.json). No API key env var is read for codex.

Reads from .env in the project root if env vars are not set.
"""

import base64
import json
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_env():
    """Load environment variables from .env file if it exists."""
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = value


def load_manifest(manifest_path: str):
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest, manifest_path: str) -> None:
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def manifest_entries(manifest) -> list[dict]:
    if isinstance(manifest, list):
        return [entry for entry in manifest if isinstance(entry, dict)]
    if isinstance(manifest, dict):
        for key in ("entries", "images", "manifest"):
            value = manifest.get(key)
            if isinstance(value, list):
                return [entry for entry in value if isinstance(entry, dict)]
    return []


# ---- Gemini -----------------------------------------------------------------

class GeminiBackend:
    name = "gemini"

    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set (check environment or .env file)."
            )
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "google-genai package is not installed. "
                "Install it with: pip install google-genai"
            ) from exc

        self._types = types
        self._client = genai.Client(api_key=api_key)
        self._model = os.environ.get("IMAGE_MODEL", "gemini-3.1-flash-image-preview")

    def generate(self, prompt: str, output_path: str) -> None:
        response = self._client.models.generate_content(
            model=self._model,
            contents=f"Generate an image: {prompt}",
            config=self._types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"]
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                with open(output_path, "wb") as f:
                    f.write(part.inline_data.data)
                return

        raise RuntimeError("Gemini API returned no image data in response.")


# ---- Codex (god-tibo-imagen) ------------------------------------------------

class CodexBackend:
    """Generate images by reusing the local Codex CLI auth.

    This routes through ChatGPT's private codex backend via the gti package.
    No API key is required, but the user must have run `codex login` and have
    image generation entitlement on their ChatGPT account. The backend is
    unsupported by OpenAI and may break without notice.
    """

    name = "codex"

    def __init__(self) -> None:
        try:
            from gti import Client
        except ImportError as exc:
            raise RuntimeError(
                "god-tibo-imagen package is not installed. "
                "Install it with: pip install god-tibo-imagen"
            ) from exc

        self._client = Client(provider="private-codex")
        self._model = os.environ.get("CODEX_IMAGE_MODEL", "gpt-5.4")

    def generate(self, prompt: str, output_path: str) -> None:
        result = self._client.generate_image(
            prompt=prompt,
            model=self._model,
            output_path=output_path,
        )

        # gti writes the file itself when output_path is provided. Confirm.
        saved = getattr(result, "saved_path", None) or output_path
        if not Path(saved).is_file() or os.path.getsize(saved) == 0:
            raise RuntimeError(
                f"Codex (gti) did not produce a file at {saved}. "
                "Check that `codex login` is current and the account has "
                "image generation entitlement."
            )


# ---- OpenAI -----------------------------------------------------------------

class OpenAIBackend:
    name = "openai"

    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set (check environment or .env file)."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai package is not installed. Install it with: pip install openai"
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
        self._size = os.environ.get("OPENAI_IMAGE_SIZE", "1536x1024")
        self._quality = os.environ.get("OPENAI_IMAGE_QUALITY", "high")

    def generate(self, prompt: str, output_path: str) -> None:
        response = self._client.images.generate(
            model=self._model,
            prompt=prompt,
            size=self._size,
            quality=self._quality,
            n=1,
        )

        datum = response.data[0]
        b64 = getattr(datum, "b64_json", None)
        if not b64:
            raise RuntimeError("OpenAI API response did not include b64_json image data.")

        with open(output_path, "wb") as f:
            f.write(base64.b64decode(b64))


# ---- Dispatcher -------------------------------------------------------------

class DiagramBackend:
    name = "diagram"

    def generate(self, prompt: str, output_path: str, image_type: str = "process_flow") -> None:
        from render_diagrams import render_diagram

        Path(output_path).write_text(
            render_diagram(prompt, image_type),
            encoding="utf-8",
        )


def get_backend(provider: str, cache: dict[str, object]) -> object:
    """Lazily instantiate (and memoize) a backend for the given provider."""
    if provider not in cache:
        if provider == "diagram":
            cache[provider] = DiagramBackend()
        elif provider == "codex":
            cache[provider] = CodexBackend()
        elif provider == "gemini":
            cache[provider] = GeminiBackend()
        elif provider == "openai":
            cache[provider] = OpenAIBackend()
        else:
            raise RuntimeError(f"Unknown image provider: {provider!r}")
    return cache[provider]


def generate_images(manifest_path: str) -> None:
    load_env()

    manifest = load_manifest(manifest_path)

    entries = manifest_entries(manifest)
    pending = [entry for entry in entries if entry.get("status") == "pending" and entry.get("prompt")]
    if not pending:
        print("No pending entries with prompts found. Nothing to generate.")
        return

    # Apply IMAGE_PROVIDER override globally if set, so user can force one
    # provider for the whole run without editing the manifest.
    override = os.environ.get("IMAGE_PROVIDER", "").strip().lower()
    if override in {"diagram", "codex", "openai", "gemini"}:
        for entry in pending:
            entry["provider"] = override

    by_provider: dict[str, int] = {}
    for entry in pending:
        prov = entry.get("provider") or "gemini"
        by_provider[prov] = by_provider.get(prov, 0) + 1
    summary = ", ".join(f"{n} {p}" for p, n in sorted(by_provider.items()))
    print(f"Found {len(pending)} pending image(s) to generate ({summary}).")

    backends: dict[str, object] = {}
    completed_count = 0
    failed_count = 0

    for idx, entry in enumerate(pending):
        marker_id = entry["marker_id"]
        prompt = entry["prompt"]
        output_path = entry["output_path"]
        provider = entry.get("provider") or "gemini"

        print(f"\n[{idx + 1}/{len(pending)}] Generating: {marker_id} (provider={provider})")
        print(f"  Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")

        try:
            if provider == "diagram" and not str(output_path).endswith(".svg"):
                output_path = str(Path(output_path).with_suffix(".svg"))
                entry["output_path"] = output_path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            backend = get_backend(provider, backends)
            if provider == "diagram":
                backend.generate(entry.get("description") or prompt, output_path, entry.get("image_type", "process_flow"))
            else:
                backend.generate(prompt, output_path)

            entry["status"] = "completed"
            completed_count += 1
            file_size = os.path.getsize(output_path)
            print(f"  Saved: {output_path} ({file_size:,} bytes)")

        except Exception as exc:
            error_msg = str(exc)
            entry["status"] = "failed"
            entry["error"] = error_msg
            failed_count += 1
            print(f"  FAILED: {error_msg}", file=sys.stderr)

        save_manifest(manifest, manifest_path)

        if idx < len(pending) - 1:
            time.sleep(2)

    print(f"\nGeneration complete: {completed_count} succeeded, {failed_count} failed.")
    print(f"Manifest updated: {manifest_path}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: .venv/bin/python3 .claude/skills/image-generator/scripts/generate_images.py <manifest_json_path>", file=sys.stderr)
        sys.exit(1)

    manifest_path = sys.argv[1]
    if not Path(manifest_path).is_file():
        print(f"Error: manifest file not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    generate_images(manifest_path)


if __name__ == "__main__":
    main()
