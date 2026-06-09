"""figforge — turn Figma exports into email-safe, pixel-faithful HTML assets.

A small toolkit distilled from a real Figma -> HTML-email rebuild. It
generalises the moves that fixed that email into reusable parts:

- forensics : read a Figma-exported SVG into a structured spec (rects,
              gradients, drop-shadow filters, image patterns, embedded rasters).
- assets    : rasterise SVG layers (with optional recolour), pull embedded
              rasters out of an SVG, content-crop and de-matte cut-outs.
- effects   : build gradient bands, radial / silhouette-rim glows from a
              drop-shadow spec, and bake layered composites.
- render    : render an SVG or an HTML email to PNG and diff two images.
- lint      : flag email-client robustness hazards (background-size:cover,
              inline-block banner shrink, base64 images, ...).

The one-off hero / body / icon fixes that started it are just one *recipe*
built on these parts — see ``examples/`` for a runnable demo.
"""

from .assets import (
    clean_alpha,
    content_crop,
    dematte,
    extract_embedded_image,
    rasterize_svg,
)
from .effects import (
    bake,
    drop_shadow,
    radial_glow,
    rim_glow,
    vertical_gradient_band,
)
from .forensics import (
    Document,
    DropShadow,
    EmbeddedImage,
    Gradient,
    GradientStop,
    ImagePattern,
    Rect,
    parse_svg,
)
from .lint import Finding, lint_html
from .render import diff, render_html, render_svg, side_by_side

__version__ = "0.1.0"

__all__ = [
    "Document",
    "Rect",
    "Gradient",
    "GradientStop",
    "DropShadow",
    "ImagePattern",
    "EmbeddedImage",
    "parse_svg",
    "rasterize_svg",
    "extract_embedded_image",
    "content_crop",
    "clean_alpha",
    "dematte",
    "vertical_gradient_band",
    "radial_glow",
    "rim_glow",
    "drop_shadow",
    "bake",
    "render_svg",
    "render_html",
    "side_by_side",
    "diff",
    "lint_html",
    "Finding",
]
