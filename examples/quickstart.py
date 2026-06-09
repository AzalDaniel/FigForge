"""figforge quickstart — runs end to end on a synthetic SVG, no external assets.

    python examples/quickstart.py

Shows the three things figforge is for: read a Figma-style SVG (forensics),
rebuild a design element as a flat email-safe image (effects), and check an
email snippet for client-robustness hazards (lint).
"""

from pathlib import Path

import figforge as ff

OUT = Path(__file__).parent / "_out"
OUT.mkdir(exist_ok=True)

# 1) A minimal Figma-style export: a dark band with a gold gradient-stripe rect.
SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="320" height="200" viewBox="0 0 320 200">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="180" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#EFBF04"/>
      <stop offset="1" stop-color="#896D02" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="320" height="200" fill="#2D2C2C"/>
  <rect x="120" y="0" width="80" height="180" fill="url(#g)"/>
</svg>"""
svg_path = OUT / "sample.svg"
svg_path.write_text(SVG)

doc = ff.parse_svg(str(svg_path))
band = next(r for r in doc.rects if doc.gradient_for(r))
grad = doc.gradient_for(band)
print(
    f"forensics: band at x={band.x:g} w={band.w:g}; gradient "
    f"{grad.stops[0].color} -> {grad.stops[-1].color}@{grad.stops[-1].opacity:g}"
)

# 2) Rebuild that band as a flat, email-safe image, with a soft glow behind it.
S = 2
layer = ff.vertical_gradient_band(
    (320 * S, 200 * S),
    (band.x * S, band.y * S, band.w * S, band.h * S),
    grad.stops[0].color,
    grad.stops[-1].color,
    grad.stops[0].opacity,
    grad.stops[-1].opacity,
)
glow = ff.radial_glow(
    (320 * S, 200 * S), (160 * S, 90 * S), 70 * S, 55 * S, "#ffffff", 0.22
)
baked = ff.bake(
    [(glow, (0, 0)), (layer, (0, 0))], (320 * S, 200 * S), background="#2D2C2C"
)
baked.save(OUT / "baked_band.png")
print(f"effects:   wrote {OUT / 'baked_band.png'} ({baked.size[0]}x{baked.size[1]})")

# 3) Lint an email snippet for client-robustness hazards.
snippet = (
    '<a style="display:inline-block"><table style="width:100%"></table></a>'
    '<td style="background-size:cover"></td><img src="x.png">'
)
findings = ff.lint_html(snippet)
print(f"lint:      {len(findings)} finding(s)")
for f in findings:
    print(f"  - [{f.severity}] {f.rule} (line {f.line})")
