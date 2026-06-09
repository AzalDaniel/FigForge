---
name: figma-to-email-html
description: >-
  Converts a Figma design (frame, component, or exported SVG) into faithful,
  email-safe HTML/CSS without paid tools like Anima, Kombai, or Postcards. Use
  when someone shares a Figma export or URL and wants pixel-accurate HTML for an
  email, newsletter, or template; wants to bake gradients, shadows, or glows
  into images; extract icons/photos as transparent PNGs; or make markup render
  the same across Gmail, Outlook, and Apple Mail. Drives a forensics ->
  asset-extraction -> effect-baking -> render+diff -> robustness-lint loop using
  the open-source `figforge` Python package as the engine.
metadata:
  author: azaldaniel
  version: "0.1.0"
  homepage: https://github.com/AzalDaniel/FigForge
---

# Figma → email-safe HTML/CSS (the figforge method)

Rebuild a Figma design as HTML/CSS that renders 1:1 in real email clients —
free, no Anima / Kombai / Postcards. **You** write the table-based HTML; the
open-source **`figforge`** engine does the deterministic, error-prone parts:
reading exact specs out of the Figma SVG, extracting and baking assets, and
verifying the result against the source by rendering and diffing.

## When to use this

- A Figma frame or SVG export needs to become an HTML **email, newsletter, or template**.
- Gradients / shadows / blurs / custom fonts must survive **Outlook & Gmail**.
- You need transparent **icon PNGs**, a **photo cut-out**, or a **baked hero** image.

Not for interactive web apps (JS, fl*ex*/grid layouts) — this targets static,
email-safe HTML.

## Why this method (the generalization)

Email clients don't render CSS like browsers: Outlook (Word engine) ignores
`background-size`, CSS gradients and `position`; Gmail strips base64 images and
clips large HTML. The reliable, **general** move for *any* Figma design:

> Read the design's exact geometry and effects from its SVG, **bake** anything
> CSS can't do reliably into flat images, lay everything out in **tables**, and
> **verify** by rendering + diffing against the source.

`figforge` makes each of those a single call, so every Figma email reduces to the
same pipeline instead of a fresh forensic expedition.

## Setup

```bash
pip install "figforge[render]"     # render extras need system libcairo + libpango
figforge --help
```

Input: the Figma **SVG export** (Figma → Export → SVG, per frame). The SVG
encodes exact rectangles, gradient stops, drop shadows and image crops — that is
the source of truth, more reliable than eyeballing the canvas.

## Pipeline — copy this checklist and tick as you go

```
- [ ] 1. Forensics   figforge spec design.svg            (or figforge.parse_svg)
- [ ] 2. Assets      extract photos / rasterize icons (white) → transparent PNGs
- [ ] 3. Effects     bake gradients/glows/shadows (+ photo) into flat <img>s
- [ ] 4. Layout      hand-write table-based, inline-CSS HTML (assets/email-skeleton.html)
- [ ] 5. Verify      render the SVG + the HTML, diff; loop until ~1:1
- [ ] 6. Lint        figforge lint email.html; fix every finding before sending
```

## 1 — Forensics

`figforge spec design.svg` prints the rects (x/y/w/h/fill), gradient stops,
drop-shadow filters, and image patterns with their source-crop fractions. In
code, `doc = figforge.parse_svg("design.svg")` gives `doc.rects`,
`doc.gradient_for(rect)`, `doc.shadow_for(rect)`, `doc.pattern_crop(pattern_id)`.

Decide, per element: **pure CSS** (solid fills, plain text, simple borders) vs
**bake to image** (gradients, shadows, blurs, custom-font headings, photos). The
decision table is in [references/email-css-matrix.md](references/email-css-matrix.md).

## 2 — Assets

- **Photo / embedded raster:** `figforge extract design.svg --image-id image1 -o photo.png`,
  then clean it: `figforge.dematte(figforge.clean_alpha(img))` and
  `figforge.content_crop(img, sides="b")` to trim a margin (e.g. so a cut-out
  sits flush on a band).
- **Icon / glyph:** `figforge rasterize icon.svg --width 48 --recolor FFFFFF -o icon.png`
  — forces a flat colour on a transparent background (no black boxes on dark sections).

## 3 — Effects: bake what email CSS can't render

Use the `figforge.effects` library (a few lines — there's no CLI for compositing):

```python
import figforge as ff

doc = ff.parse_svg("design.svg")
band = next(r for r in doc.rects if doc.gradient_for(r))   # a gradient stripe
grad = doc.gradient_for(band)
shadow = next(s for s in doc.shadows.values() if s.color == (255, 255, 255))  # e.g. a glow

S = 2  # render at 2x for retina
layer = ff.vertical_gradient_band(
    (W * S, H * S), (band.x * S, band.y * S, band.w * S, band.h * S),
    grad.stops[0].color, grad.stops[-1].color,
    grad.stops[0].opacity, grad.stops[-1].opacity,
)
subject = ff.dematte(ff.clean_alpha(ff.extract_embedded_image("design.svg", "image1")))
glow = ff.rim_glow(subject, shadow, source_card_px=(card_w, subject.width))
hero = ff.bake([(glow, (0, 0)), (layer, (0, 0)), (subject, (x, y))],
               (W * S, H * S), background="#2D2C2C")
hero.save("hero.png")     # one flat image — renders identically everywhere
```

Rule of thumb: **one flat baked `<img>` beats a stack of CSS layers** in email.
Per-effect recipes (gradient bands, radial/rim glows, drop shadows, flush crops):
[references/pipeline.md](references/pipeline.md).

## 4 — Layout

Hand-write **table-based, inline-CSS** HTML. Start from
[assets/email-skeleton.html](assets/email-skeleton.html). Reference baked images
by **hosted https URL** (never base64). Give **every `<img>` an explicit `width`**.

## 5 — Verify (the 1:1 loop)

```bash
figforge render-svg design.svg --width 680 -o target.png        # the design, as-is
figforge render-html email.html --width 680 --height 1800 -o actual.png
figforge diff target.png actual.png -o heat.png                 # score + heatmap
```

Or run [scripts/verify.py](scripts/verify.py) `design.svg email.html`. If the
score is high, the heatmap shows *where*; fix step 2/3/4 and re-diff. Don't trust
an ESP's in-app preview — it lies about Outlook/Gmail.

## 6 — Lint (robustness gate)

```bash
figforge lint email.html
```

Flags the email-killers: `background-size:cover`, `inline-block` banner shrink,
base64 images, missing `<img width>`, flex/grid, web-font with no fallback. Fix
every **high** finding before you send.

## Principles (apply throughout)

1. **Bake, don't layer** — a flat `<img>` renders identically everywhere; CSS
   backgrounds + `cover` + overlap do not.
2. **Pin widths** — explicit px on images and banner tables; never rely on
   `inline-block` to fill width.
3. **No base64 in email** — host assets, reference them by https URL.
4. **Verify against the source** — render + diff, not the in-app preview.

## Engine reference

Full `figforge` CLI and library API: [references/figforge-cli.md](references/figforge-cli.md).
Source, issues, and license (Apache-2.0): https://github.com/AzalDaniel/FigForge
