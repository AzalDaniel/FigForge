# figforge

[![CI](https://github.com/AzalDaniel/FigForge/actions/workflows/ci.yml/badge.svg)](https://github.com/AzalDaniel/FigForge/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/figforge)](https://pypi.org/project/figforge/)
[![Python](https://img.shields.io/pypi/pyversions/figforge)](https://pypi.org/project/figforge/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Turn Figma SVG exports into email-safe, pixel-faithful HTML assets.**

figforge is the engine distilled from a real Figma → HTML-email rebuild. The
one-off fixes that job needed — a baked hero image, transparent white icons, a
silhouette rim-glow, a cut-out aligned flush to a band — turned out to be
instances of a handful of general operations. figforge is those operations, so
the next email is a short recipe, not a forensic expedition.

## Why it exists

Browsers render Figma's CSS faithfully; **email clients do not.** Outlook's Word
engine ignores `background-size`, CSS gradients and `position`; Gmail strips
base64 images and clips large HTML. The reliable move is to **bake design into
flat images** and keep the HTML to tables — but doing that 1:1 with the design,
by hand, is fiddly. figforge automates the fiddly parts and *verifies* the result.

## The five parts

| Module | What it does |
|---|---|
| `forensics` | Parse a Figma SVG into a spec: rects, gradient stops, drop-shadow filters, image-pattern crops, embedded rasters. |
| `assets` | Rasterise SVG layers (with optional recolour), decode embedded `<image>` rasters, content-crop, clean alpha, de-matte. |
| `effects` | Gradient bands (hard edges), radial + silhouette-rim glows from a shadow spec, and `bake()` to flatten layers into one image. |
| `render` | Render an SVG or HTML email to PNG; `side_by_side` + `diff`. |
| `lint` | Flag email-robustness hazards (`background-size:cover`, inline-block banner shrink, base64 images, missing `<img width>`, flex/grid, web-font fallback). |

## Install

```bash
pip install figforge                 # core: forensics, image ops, effects, lint
pip install "figforge[render]"       # + SVG/HTML rendering
```

The `[render]` extra (`cairosvg`, `weasyprint`, `pymupdf`) needs system libraries
that pip can't install:

```bash
# Debian/Ubuntu
sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0
# macOS
brew install cairo pango
```

`lint` and `forensics` (and the pure-Pillow helpers) work without the extra.

## Quick start

```bash
figforge lint email.html                                   # catch client gotchas
figforge rasterize icon.svg --width 48 --recolor FFFFFF -o icon.png
figforge extract master.svg --image-id image1 -o photo.png # decode an embedded raster
figforge render-svg master.svg --width 680 -o target.png   # 1:1 reference
figforge render-html email.html --width 680 --height 1862 -o actual.png
figforge diff target.png actual.png -o heat.png
```

```python
import figforge as ff

doc = ff.parse_svg("master.svg")
band = next(r for r in doc.rects if doc.gradient_for(r))    # a gradient stripe
grad = doc.gradient_for(band)
shadow = next(s for s in doc.shadows.values() if s.color == (255, 255, 255))

man = ff.dematte(ff.clean_alpha(ff.extract_embedded_image("master.svg", "image1")))
glow = ff.rim_glow(man, shadow, source_card_px=(300, man.width))
hero = ff.bake([(glow, (0, 0)), (man, (0, 0))], size=man.size, background="#2D2C2C")
hero.save("hero.png")
```

A complete, dependency-light example is in [`examples/quickstart.py`](examples/quickstart.py).

## Principles it encodes

1. **Bake, don't layer.** One flat `<img>` renders identically everywhere; CSS
   backgrounds + `cover` + overlap do not.
2. **Pin widths.** Give images and banner tables explicit pixel widths; never
   rely on `inline-block` to fill width.
3. **No base64 in email.** Host assets; reference them by https URL.
4. **Verify against the source.** Render the design and diff — don't trust an
   in-app preview, which lies about Outlook/Gmail.

## Use it as an agent skill

figforge ships an [Agent Skill](https://agentskills.io) that teaches AI coding
agents the full Figma → email-safe HTML method (the `figforge` engine plus the
client-robustness principles). Install it into your agent:

```bash
npx skills add AzalDaniel/FigForge --skill figma-to-email-html
```

The skill (`skills/figma-to-email-html/`) is the *method*; this package is the
*engine* it drives.

## Contributing

Issues and PRs welcome — especially new lint rules for client gotchas you've hit.
See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).
Where this is headed — a Figma REST ingester, an intermediate representation,
DTCG token extraction and an MJML emitter — is in [ROADMAP.md](ROADMAP.md).

## License

[Apache License 2.0](LICENSE). The Apache-2.0 grant includes an explicit
patent license, which is the safer default for a rendering/diffing tool.
