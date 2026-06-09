# figforge engine reference (CLI + library)

`pip install "figforge[render]"` (the `[render]` extra needs system `libcairo` +
`libpango`; `lint`/`forensics`/pure-Pillow ops work without it).

## CLI

```
figforge lint EMAIL.html                              # email-robustness findings (exit 1 if any "high")
figforge spec DESIGN.svg                              # forensic summary: rects, gradients, shadows, patterns
figforge extract DESIGN.svg --image-id ID -o OUT.png  # decode an embedded base64 raster
figforge rasterize GLYPH.svg --width N [--height N] [--recolor RRGGBB] [--supersample 3] -o OUT.png
figforge render-svg DESIGN.svg --width 680 -o OUT.png
figforge render-html EMAIL.html --width 680 --height 1862 [--base-url DIR] -o OUT.png
figforge diff A.png B.png [-o HEAT.png]               # mean abs diff (0..1) + heatmap
```

## Library

```python
import figforge as ff

# forensics
doc = ff.parse_svg("design.svg")            # -> Document
#   doc.rects / doc.gradients / doc.shadows / doc.patterns / doc.images
#   doc.gradient_for(rect) / doc.shadow_for(rect) / doc.pattern_for(rect)
#   doc.pattern_crop(pattern_id) -> (x0,x1,y0,y1) source-crop fractions
#   doc.find_rects(min_w=, min_h=, fill_is_gradient=)

# assets
ff.rasterize_svg(path, width, height=None, recolor=(255,255,255), supersample=3)
ff.extract_embedded_image(svg_path, image_id=None)   # -> PIL.Image (RGBA)
ff.content_crop(img, alpha_threshold=10, sides="ltrb")
ff.clean_alpha(img, floor=40)
ff.dematte(img, luma_threshold=70, erode=1)

# effects (RGBA layers; bake -> flat RGB)
ff.vertical_gradient_band(size, (x,y,w,h), top_color, bottom_color, top_opacity=1.0, bottom_opacity=0.0)
ff.radial_glow(size, (cx,cy), rx, ry, color, peak_opacity=0.4)
ff.drop_shadow(alpha_source, color, opacity, blur, offset=(0,0))
ff.rim_glow(subject, shadow, source_card_px=None)    # shadow = a DropShadow from forensics
ff.bake([(layer, (x,y)), ...], size, background="#RRGGBB")

# render + verify
ff.render_svg(svg_path, width)                       # -> PIL.Image (needs [render])
ff.render_html(html_or_path, (w,h), scale=2, base_url=None)
ff.side_by_side(img_a, img_b, labels=("target","actual"))
ff.diff(img_a, img_b)                                # -> (score_0_1, heatmap_image)

# lint
ff.lint_html(html_string)                            # -> list[Finding(rule, severity, line, message, suggestion)]
```

Colors accept `"#RRGGBB"` or `(r, g, b)`. Everything is deterministic and
dependency-light in the core; rendering is isolated behind the `[render]` extra.

Repo: https://github.com/AzalDaniel/FigForge
