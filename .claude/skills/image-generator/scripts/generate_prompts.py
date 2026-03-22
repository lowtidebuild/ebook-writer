#!/usr/bin/env python3
"""Generate image prompts from templates based on image type classification.

Usage:
    python3 generate_prompts.py \
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
        # Skip entries that already have prompts
        if entry.get("prompt"):
            skipped_count += 1
            continue

        image_type = entry.get("image_type")
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
