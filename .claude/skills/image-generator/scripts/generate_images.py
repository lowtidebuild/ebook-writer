#!/usr/bin/env python3
"""
generate_images.py - Generate images for pending manifest entries via Google Gemini API.

Usage:
    python3 generate_images.py <manifest_json_path>

Example:
    python3 generate_images.py output/images/image_manifest.json

Environment variables:
    GEMINI_API_KEY  (required) - Google Gemini API key
    IMAGE_MODEL     (optional) - Model name, defaults to "imagen-3.0-generate-002"
"""

import json
import os
import sys
import time
from pathlib import Path


def load_manifest(manifest_path: str) -> list[dict]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest: list[dict], manifest_path: str) -> None:
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def generate_images(manifest_path: str) -> None:
    # ------------------------------------------------------------------
    # Validate API key
    # ------------------------------------------------------------------
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    model_name = os.environ.get("IMAGE_MODEL", "imagen-3.0-generate-002")

    # ------------------------------------------------------------------
    # Import the Gemini client library
    # ------------------------------------------------------------------
    try:
        import google.generativeai as genai
    except ImportError:
        print(
            "Error: google-generativeai package is not installed. "
            "Install it with: pip install google-generativeai",
            file=sys.stderr,
        )
        sys.exit(1)

    genai.configure(api_key=api_key)

    # ------------------------------------------------------------------
    # Load manifest
    # ------------------------------------------------------------------
    manifest = load_manifest(manifest_path)

    pending = [entry for entry in manifest if entry["status"] == "pending" and entry.get("prompt")]
    if not pending:
        print("No pending entries with prompts found. Nothing to generate.")
        return

    print(f"Found {len(pending)} pending entry/entries to generate with model '{model_name}'.")

    # ------------------------------------------------------------------
    # Obtain the image generation model
    # ------------------------------------------------------------------
    try:
        imagen_model = genai.ImageGenerationModel(model_name)
    except Exception as exc:
        print(f"Error: failed to load model '{model_name}': {exc}", file=sys.stderr)
        sys.exit(1)

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

            # Call the Gemini image generation API
            result = imagen_model.generate_images(
                prompt=prompt,
                number_of_images=1,
                safety_filter_level="block_only_high",
                aspect_ratio="16:9",
            )

            if not result.images:
                raise RuntimeError("API returned no images.")

            # Save the first generated image
            image = result.images[0]

            # google.generativeai Image objects expose _pil_image or
            # a save() helper depending on the SDK version.
            if hasattr(image, "save"):
                image.save(output_path)
            elif hasattr(image, "_pil_image"):
                image._pil_image.save(output_path)
            else:
                # Fallback: attempt to write raw bytes
                with open(output_path, "wb") as img_file:
                    img_file.write(image._image_bytes)

            entry["status"] = "completed"
            completed_count += 1
            print(f"  Saved: {output_path}")

        except Exception as exc:
            error_msg = str(exc)
            entry["status"] = "failed"
            entry["error"] = error_msg
            failed_count += 1
            print(f"  FAILED: {error_msg}", file=sys.stderr)

        # Persist manifest after every attempt so progress is not lost
        save_manifest(manifest, manifest_path)

        # Rate-limit: pause between API calls
        if idx < len(pending) - 1:
            time.sleep(2)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
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
