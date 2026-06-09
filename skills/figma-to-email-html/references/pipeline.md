# Pipeline — per-stage detail

Depth for each step of the figma-to-email-html method. The SKILL.md is the
checklist; this is the "how" you read when a step needs it.

## 1. Forensics — `figforge.parse_svg`

```python
import figforge as ff
doc = ff.parse_svg("design.svg")
doc.width, doc.height            # frame size
doc.rects                        # list[Rect]: .x .y .w .h .fill .rx .filter, .right .bottom .cx .cy
doc.gradients                    # id -> Gradient(.kind .stops[GradientStop(.offset .color .opacity)] .coords .vertical)
doc.shadows                      # id -> DropShadow(.color(rgb) .opacity .blur .dx .dy .region)
doc.patterns                     # id -> ImagePattern(.image_id .matrix .image_w .image_h)
doc.images                       # id -> EmbeddedImage(.w .h .href)
doc.gradient_for(rect)           # resolve a rect's url(#..) gradient
doc.shadow_for(rect)             # resolve a rect's (or its parent <g>'s) drop shadow
doc.pattern_for(rect)            # resolve a rect's image pattern
doc.pattern_crop(pattern_id)     # (x0,x1,y0,y1) fractions of the source actually shown
```

The CLI summary: `figforge spec design.svg`.

**Read it like this:** every node is either *CSS-able* or *bake-it*. Solid
rectangles, plain text, simple borders, links → CSS/HTML. Gradients, drop
shadows, blurs, custom-font headlines, photos, anything overlapping → bake to a
flat image (step 3). When in doubt, bake — it always renders.

## 2. Asset extraction

```python
img = ff.extract_embedded_image("design.svg", "image1")   # decode an embedded base64 raster
img = ff.clean_alpha(img, floor=40)        # drop faint baked glow, keep the subject + AA edge
img = ff.dematte(img, luma_threshold=70)   # remove the dark fringe from cutting off a dark bg
img = ff.content_crop(img, sides="b")      # trim only the bottom margin (legs flush to a band)
```

Icons from vector glyphs: `figforge rasterize glyph.svg --width 48 --recolor FFFFFF -o icon.png`
(`--recolor` forces a flat tint; output is transparent — no black boxes).

## 3. Effects — recipes

All return RGBA layers; `bake` flattens a bottom-to-top stack onto a solid bg.

- **Gradient band (hard-edged rectangle):** `vertical_gradient_band(size, (x,y,w,h), top_color, bottom_color, top_op, bottom_op)`.
  Email-safe replacement for a CSS gradient; crisp vertical edges (unlike a soft
  background image that clients crop inconsistently).
- **Radial glow / spotlight:** `radial_glow(size, (cx,cy), rx, ry, color, peak_opacity)`.
- **Silhouette rim-glow from a Figma drop shadow:** `rim_glow(subject, shadow, source_card_px=(card_w, subject_w))`.
  `shadow` is a `DropShadow` from forensics; `source_card_px` rescales the blur
  from the design's card space to the subject image's pixels. A white, low-opacity,
  slightly-upward shadow is the typical subtle glow behind a cut-out.
- **Generic drop shadow:** `drop_shadow(subject, color, opacity, blur, offset=(dx,dy))`.
- **Bake:** `bake([(layerA,(x,y)), (layerB,(x,y))], size, background="#RRGGBB") -> RGB`.
  Compose the section's dark background + gradient band + glow + photo into ONE
  image; reference it as a single `<img width=...>`.

## 4. Layout

Table-based, inline CSS, ~600px max width. See `../assets/email-skeleton.html`.
Hosted https image URLs only. Explicit `width` on every `<img>`. Whole-banner
links use `display:block;width:100%` (never `inline-block`, which shrink-wraps).

## 5. Verify

```bash
figforge render-svg design.svg --width 680 -o target.png
figforge render-html email.html --width 680 --height 1800 -o actual.png
figforge diff target.png actual.png -o heat.png
```

`diff` returns a mean-absolute-difference in 0..1 plus a heatmap. < ~0.02–0.03 is
effectively a match; otherwise the red areas of `heat.png` show where to fix.
Helper: `scripts/verify.py design.svg email.html`.

## 6. Lint

`figforge lint email.html` → findings (rule, severity, line, fix). Rules:
`background-size-cover`, `inline-block-banner`, `base64-image`, `img-without-width`,
`position-absolute`, `flex-or-grid`, `webfont-no-fallback`, `bgimage-no-vml`.
It is comment- and Outlook-`[if mso]`-aware (won't flag VML boilerplate).
