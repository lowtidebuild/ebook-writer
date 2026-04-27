#!/usr/bin/env python3
"""Generate image prompts from templates based on image type classification.

Usage:
    .venv/bin/python3 .claude/skills/image-generator/scripts/generate_prompts.py \
        --manifest output/images/image_manifest.json \
        --templates .claude/skills/image-generator/references/prompt_templates/ \
        --style-guide .claude/skills/image-generator/references/image_style_guide.md

Reads the manifest, applies type-specific prompt templates to entries
where image_type is set but prompt is null, and saves the manifest in-place.
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load_template(templates_dir: str, image_type: str) -> str:
    """Load a prompt template for the given image type, with generic fallback."""
    template_path = os.path.join(templates_dir, f"{image_type}.txt")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    # Fallback to generic template
    generic_path = os.path.join(templates_dir, "generic.txt")
    if os.path.exists(generic_path):
        with open(generic_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    # Hardcoded fallback if no template files exist
    return (
        "A clean, professional infographic. {description}\n"
        "Style: Modern flat design, minimal decoration.\n"
        "Colors: Blue (#2563EB), gray (#6B7280), white background.\n"
        "Aspect ratio: 16:9 landscape, 1024x576px minimum.\n"
        "Quality: Professional book-quality illustration."
    )


def generate_prompt(template: str, description: str) -> str:
    """Fill in the template with the image description."""
    return template.replace("{description}", description)


# Default provider routing per image type.
# - "diagram": deterministic local SVG renderer for text-heavy diagrams.
# - "gemini": Google Gemini multimodal image output. Cheap and stable; used for
#   illustrative content where text accuracy is less critical.
# - "codex": optional god-tibo-imagen (gti) backend via local Codex CLI auth.
# - "openai": Paid OpenAI Images API (gpt-image-*). Reserved for explicit
#   override when caller wants the official API for reliability.
DEFAULT_PROVIDER_ROUTING = {
    "architecture": "diagram",
    "process_flow": "diagram",
    "comparison_table": "diagram",
    "concept_diagram": "gemini",
    "metaphor": "gemini",
}

VALID_PROVIDERS = {"diagram", "codex", "gemini", "openai"}


def resolve_provider(image_type: str) -> str:
    """Pick a provider for the given image type.

    A global override via IMAGE_PROVIDER (diagram|codex|gemini|openai)
    wins over the per-type default. Unknown types fall back to gemini.
    """
    override = os.environ.get("IMAGE_PROVIDER", "").strip().lower()
    if override in VALID_PROVIDERS:
        return override
    return DEFAULT_PROVIDER_ROUTING.get(image_type, "gemini")


def ensure_output_path(entry: dict, manifest_path: str, provider: str) -> None:
    """Fill or correct output_path once provider routing is known."""
    suffix = ".svg" if provider == "diagram" else ".png"
    existing = entry.get("output_path")
    if existing:
        path = Path(existing)
        if provider == "diagram" and path.suffix.lower() != ".svg":
            entry["output_path"] = str(path.with_suffix(".svg"))
        return

    stem = entry.get("output_stem")
    if not stem:
        marker_id = entry.get("marker_id")
        if not marker_id:
            return
        stem = str(Path(manifest_path).parent / marker_id)
        entry["output_stem"] = stem
    entry["output_path"] = str(Path(stem).with_suffix(suffix))


def main():
    parser = argparse.ArgumentParser(description="Generate image prompts from templates")
    parser.add_argument("--manifest", required=True, help="Path to image_manifest.json")
    parser.add_argument("--templates", required=True, help="Path to prompt_templates/ directory")
    parser.add_argument("--style-guide", required=False, help="Path to image_style_guide.md")
    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        print(f"Error: Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.templates):
        print(f"Warning: Templates directory not found: {args.templates}", file=sys.stderr)
        print("Using hardcoded fallback template.", file=sys.stderr)

    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    generated_count = 0
    skipped_count = 0

    entries = manifest if isinstance(manifest, list) else manifest.get("entries", manifest.get("images", []))

    for entry in entries:
        image_type = entry.get("image_type")

        # Always (re)assign provider when missing so existing manifests get
        # routed correctly on subsequent runs. Don't overwrite user-set values.
        if not entry.get("provider") and image_type:
            entry["provider"] = resolve_provider(image_type)
        provider = entry.get("provider") or resolve_provider(image_type or "")
        ensure_output_path(entry, args.manifest, provider)

        # Skip entries that already have prompts
        if entry.get("prompt"):
            skipped_count += 1
            continue

        description = entry.get("description", "")

        if not image_type or not description:
            skipped_count += 1
            continue

        template = load_template(args.templates, image_type)
        entry["prompt"] = generate_prompt(template, description)
        generated_count += 1

    # Save manifest in-place
    with open(args.manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Generated {generated_count} prompts for {generated_count} images "
          f"({skipped_count} skipped)")


if __name__ == "__main__":
    main()
