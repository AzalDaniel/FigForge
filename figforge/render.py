"""Render SVGs and HTML emails to PNG, and diff two images.

Verification is half the job: render the Figma master SVG as a 1:1 *target*,
render the HTML (or a section of it) as the *actual*, and compare. WeasyPrint
(>= 53) only emits PDF, so HTML is rasterised via PDF -> PyMuPDF.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw


def render_svg(svg_path: str, width: int) -> Image.Image:
    """Render a whole SVG to an RGB PNG at ``width`` px (height auto)."""
    import cairosvg

    png = cairosvg.svg2png(url=svg_path, output_width=width)
    return Image.open(io.BytesIO(png)).convert("RGB")


def render_html(
    html, page_size, scale: int = 2, base_url: str | None = None
) -> Image.Image:
    """Render an HTML string (or file path) to a PNG.

    ``page_size`` is ``(width_px, height_px)``. Use ``base_url`` (a directory)
    so relative ``<img src>`` paths resolve to local files. Requires
    ``weasyprint`` and ``pymupdf``.
    """
    import fitz  # pymupdf
    from weasyprint import HTML

    w, h = page_size
    if "<" in str(html):
        css = f"@page{{size:{w}px {h}px;margin:0}}body{{margin:0}}"
        doc = HTML(string=f"<style>{css}</style>{html}", base_url=base_url)
    else:
        doc = HTML(filename=html, base_url=base_url)
    pdf = doc.write_pdf()
    page = fitz.open("pdf", pdf)[0]
    pm = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    return Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB")


def side_by_side(
    img_a, img_b, labels=("target", "actual"), height: int = 520
) -> Image.Image:
    """Stack two images horizontally with labels for an eyeball comparison."""

    def fit(im):
        w = int(im.width * height / im.height)
        return im.resize((w, height), Image.Resampling.LANCZOS)

    a, b = fit(img_a.convert("RGB")), fit(img_b.convert("RGB"))
    pad = 16
    out = Image.new("RGB", (a.width + b.width + 3 * pad, height + 28), (20, 20, 22))
    d = ImageDraw.Draw(out)
    d.text((pad, 6), labels[0], fill=(255, 210, 80))
    d.text((a.width + 2 * pad, 6), labels[1], fill=(120, 210, 120))
    out.paste(a, (pad, 22))
    out.paste(b, (a.width + 2 * pad, 22))
    return out


def diff(img_a, img_b):
    """Return (mean_abs_difference_0_1, heatmap_image) for two images.

    Resizes ``b`` to ``a`` first. The score is a quick regression signal; the
    heatmap shows *where* they differ.
    """
    a = np.asarray(img_a.convert("RGB"), float)
    b = np.asarray(img_b.convert("RGB").resize(img_a.size), float)
    d = np.abs(a - b).mean(axis=2)
    score = float(d.mean() / 255.0)
    heat = np.zeros((*d.shape, 3), np.uint8)
    heat[:, :, 0] = np.clip(d, 0, 255).astype(np.uint8)
    return score, Image.fromarray(heat, "RGB")
