# Image Style Guide

Prompts written for the image generation pipeline should follow these guidelines to ensure a consistent visual language across all chapters.

## Visual Style

- **Clean, modern, flat design.** Avoid photorealistic renders, stock-photo aesthetics, or heavily textured surfaces.
- **Infographic / diagram style.** Prefer structured layouts with clear visual hierarchy: labeled sections, arrows, icons, and concise annotations.
- **Minimal decoration.** Remove unnecessary gradients, drop shadows, and ornamental borders. White space is encouraged.

## Color Palette

| Role        | Color                        |
|-------------|------------------------------|
| Primary     | Blue (#2563EB, #3B82F6)      |
| Secondary   | Gray (#6B7280, #9CA3AF)      |
| Background  | White (#FFFFFF) or very light gray (#F9FAFB) |
| Accent      | Teal (#14B8A6) or amber (#F59E0B) for highlights |
| Text/labels | Dark gray (#1F2937)          |

Stick to this palette unless the subject matter specifically demands other colors (e.g., a chart showing categorical data with distinct hues).

## Text and Labels

- Use **Korean** for all visible text labels, titles, and annotations unless the concept is universally expressed in English (e.g., "API", "HTTP").
- Keep label text short -- two to four words maximum.
- Use a clean sans-serif typeface style.

## Composition

- **Aspect ratio:** 16:9 (landscape) for full-width figures.
- **Resolution:** target at least 1024 x 576 pixels.
- Center the main subject; avoid crowding the edges.
- When showing a process or flow, arrange steps left-to-right or top-to-bottom.

## Content Tone

- Professional and book-quality. The images should feel like they belong in a published technical ebook.
- Avoid humor, clip-art style, or cartoonish exaggeration.
- Prefer abstract or schematic representations of concepts over literal depictions of people or places.

## Prompt Template

When filling in the `prompt` field of the manifest, follow this structure:

```
A clean, flat-design infographic illustrating [CONCEPT]. [SPECIFIC DETAILS about layout, elements, and labels].
Use a modern color palette of blues, grays, and white. Korean text labels. 16:9 aspect ratio.
Professional book-quality illustration, minimal and elegant.
```
