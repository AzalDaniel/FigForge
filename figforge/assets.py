"""Get clean raster assets out of a Figma export.

Two sources of truth in a Figma SVG:
  * vector layers (icons, shapes) -> rasterise with cairosvg, optionally
    forcing a flat colour (e.g. make a black-exported glyph white-on-transparent);
  * embedded ``<image>`` rasters (photos) -> decode the base64 directly, no
    rasteriser needed, then crop / de-matte the cut-out.

These were the exact moves that turned black-box icons into clean white glyphs
and a haloed cut-out into a crisp one.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def rasterize_svg(
    svg_path: str,
    width: int,
    height: int | None = None,
    recolor: tuple | None = None,
    supersample: int = 1,
) -> Image.Image:
    """Rasterise an SVG to a transparent-background RGBA PNG.

    ``recolor=(r, g, b)`` forces every pixel to that colour while keeping the
    rendered alpha — the trick for turning any-coloured source glyphs into a
    uniform tint (white icons on a dark section). ``supersample`` renders larger
    then downsamples for crisper anti-aliasing.
    """
    import cairosvg  # imported lazily so the rest of the package has no hard dep

    out_w = width * max(1, supersample)
    out_h = (height or width) * max(1, supersample)
    png = cairosvg.svg2png(url=svg_path, output_width=out_w, output_height=out_h)
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    if recolor is not None:
        a = np.array(img)
        a[:, :, 0], a[:, :, 1], a[:, :, 2] = recolor
        img = Image.fromarray(a, "RGBA")
    if supersample > 1:
        img = img.resize((width, height or width), Image.Resampling.LANCZOS)
    return img


def extract_embedded_image(svg_path: str, image_id: str | None = None) -> Image.Image:
    """Decode an embedded base64 ``<image>`` from an SVG into a PIL image.

    With ``image_id`` returns that specific element; otherwise the first/only
    embedded image. Avoids any rasteriser — the photo is already a PNG/JPEG.
    """
    svg = Path(svg_path).read_text(encoding="utf-8")
    if image_id:
        tag = re.search(rf'<image\b[^>]*\bid="{re.escape(image_id)}"[^>]*>', svg)
        scope = tag.group(0) if tag else ""
    else:
        tag = re.search(r"<image\b[^>]*>", svg)
        scope = tag.group(0) if tag else ""
    m = re.search(r'(?:xlink:href|href)="data:image/[^;]+;base64,([^"]+)"', scope)
    if not m:
        raise ValueError(f"no embedded base64 image found for id={image_id!r}")
    return Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert("RGBA")


def content_crop(
    img: Image.Image, alpha_threshold: int = 10, sides: str = "ltrb"
) -> Image.Image:
    """Crop transparent margins down to the visible content.

    ``sides`` selects which edges to crop (any of ``l r t b``) — e.g. ``"b"``
    crops only the bottom margin, which is how the body-man's legs were made to
    sit flush on the CTA band.
    """
    a = np.array(img.convert("RGBA"))[:, :, 3]
    ys, xs = np.where(a > alpha_threshold)
    if len(xs) == 0:
        return img
    left = xs.min() if "l" in sides else 0
    right = xs.max() + 1 if "r" in sides else img.width
    top = ys.min() if "t" in sides else 0
    bottom = ys.max() + 1 if "b" in sides else img.height
    return img.crop((left, top, right, bottom))


def clean_alpha(img: Image.Image, floor: int = 40) -> Image.Image:
    """Zero out faint alpha (< ``floor``) — removes a baked, low-opacity glow
    while keeping the subject and its anti-aliased edge."""
    a = np.array(img.convert("RGBA"))
    al = a[:, :, 3]
    al[al < floor] = 0
    a[:, :, 3] = al
    return Image.fromarray(a, "RGBA")


def dematte(img: Image.Image, luma_threshold: int = 70, erode: int = 1) -> Image.Image:
    """Remove a dark fringe left by cutting a subject off a dark background.

    Drops semi-transparent edge pixels that are also dark (luma < threshold),
    then optionally erodes the alpha by ``erode`` px to crisp the boundary.
    """
    a = np.array(img.convert("RGBA")).astype(np.float32)
    al = a[:, :, 3]
    luma = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
    fringe = (al > 0) & (al < 235) & (luma < luma_threshold)
    al[fringe] = 0
    if erode > 0:
        size = erode * 2 + 1
        eroded = Image.fromarray(al.astype(np.uint8)).filter(
            ImageFilter.MinFilter(size)
        )
        al = np.minimum(al, np.array(eroded).astype(np.float32))
    a[:, :, 3] = al
    return Image.fromarray(a.astype(np.uint8), "RGBA")
