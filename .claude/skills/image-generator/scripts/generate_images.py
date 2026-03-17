#!/usr/bin/env python3
"""
generate_images.py - Generate images for pending manifest entries via Google Gemini API.

Uses the new google-genai SDK with GenerativeModel multimodal output.

Usage:
    python3 generate_images.py <manifest_json_path>

Example:
    python3 generate_images.py output/images/image_manifest.json

Environment variables:
    GEMINI_API_KEY  (required) - Google Gemini API key
    IMAGE_MODEL     (optional) - Model name, defaults to "gemini-3.1-flash-image-preview"

Alternatively, reads from .env file in project root if environment variables are not set.
"""

import json
import os
import sys
import time
from pathlib import Path


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


def load_manifest(manifest_path: str) -> list[dict]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest: list[dict], manifest_path: str) -> None:
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def generate_images(manifest_path: str) -> None:
    # Load .env if needed
    load_env()

    # Validate API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set (check environment or .env file).", file=sys.stderr)
        sys.exit(1)

    model_name = os.environ.get("IMAGE_MODEL", "gemini-3.1-flash-image-preview")

    # Import the new Gemini client
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print(
            "Error: google-genai package is not installed. "
            "Install it with: pip install google-genai",
            file=sys.stderr,
        )
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Load manifest
    manifest = load_manifest(manifest_path)

    pending = [entry for entry in manifest if entry["status"] == "pending" and entry.get("prompt")]
    if not pending:
        print("No pending entries with prompts found. Nothing to generate.")
        return

    print(f"Found {len(pending)} pending image(s) to generate with model '{model_name}'.")

    completed_count = 0
    failed_count = 0

    for idx, entry in enumerate(pending):
        marker_id = entry["marker_id"]
        prompt = entry["prompt"]
        output_path = entry["output_path"]

        print(f"\n[{idx + 1}/{len(pending)}] Generating: {marker_id}")
        print(f"  Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")

        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Call Gemini with multimodal image output
            response = client.models.generate_content(
                model=model_name,
                contents=f"Generate an image: {prompt}",
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                ),
            )

            # Extract image from response
            image_saved = False
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    with open(output_path, "wb") as f:
                        f.write(part.inline_data.data)
                    image_saved = True
                    break

            if not image_saved:
                raise RuntimeError("API returned no image data in response.")

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

        # Persist manifest after every attempt so progress survives crashes
        save_manifest(manifest, manifest_path)

        # Rate-limit between API calls
        if idx < len(pending) - 1:
            time.sleep(2)

    # Summary
    print(f"\nGeneration complete: {completed_count} succeeded, {failed_count} failed.")
    print(f"Manifest updated: {manifest_path}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 generate_images.py <manifest_json_path>", file=sys.stderr)
        sys.exit(1)

    manifest_path = sys.argv[1]
    if not Path(manifest_path).is_file():
        print(f"Error: manifest file not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    generate_images(manifest_path)


if __name__ == "__main__":
    main()
