"""Re-create Figma effects as flat raster layers.

The point of baking effects into PNGs is email robustness: a single ``<img>``
renders identically in Outlook, Gmail and everywhere, whereas CSS gradients,
``background-size:cover`` and layered backgrounds do not. Each function returns
an RGBA layer; :func:`bake` stacks them onto a background into one flat image.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def _hex(c):
    if isinstance(c, (tuple, list)):
        return tuple(c[:3])
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def vertical_gradient_band(
    size, rect, top_color, bottom_color, top_opacity=1.0, bottom_opacity=0.0
) -> Image.Image:
    """A hard-edged rectangle with a vertical colour+opacity gradient.

    ``rect`` is ``(x, y, w, h)`` in the layer's own pixels. Edges are crisp
    (a real rectangle, not a soft gaussian band) — matching how Figma draws a
    gradient-filled rect, and avoiding the "hazy one side / hard the other"
    artefact you get when a soft background image is cropped by an email client.
    """
    W, H = size
    x, y, w, h = [int(round(v)) for v in rect]
    top, bot = np.array(_hex(top_color), float), np.array(_hex(bottom_color), float)
    out = np.zeros((H, W, 4), float)
    for row in range(max(0, y), min(H, y + h)):
        t = (row - y) / h
        out[row, x : x + w, :3] = top * (1 - t) + bot * t
        out[row, x : x + w, 3] = (top_opacity * (1 - t) + bottom_opacity * t) * 255
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def radial_glow(size, center, rx, ry, color, peak_opacity=0.4) -> Image.Image:
    """A soft elliptical radial glow (a spotlight) as an RGBA layer."""
    W, H = size
    cx, cy = center
    Y, X = np.mgrid[0:H, 0:W].astype(float)
    g = np.exp(-(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2))
    out = np.zeros((H, W, 4), float)
    out[:, :, :3] = _hex(color)
    out[:, :, 3] = np.clip(g, 0, 1) * peak_opacity * 255
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def drop_shadow(alpha_source, color, opacity, blur, offset=(0, 0)) -> Image.Image:
    """A Figma-style drop shadow from a subject's alpha.

    ``alpha_source`` is a PIL image (its alpha channel is used) or a 2-D array.
    Returns an RGBA layer = blurred, offset silhouette in ``color`` at
    ``opacity``. A *white* shadow with a small upward offset is exactly the
    subtle rim-glow Figma puts behind a cut-out (see :func:`rim_glow`).
    """
    if isinstance(alpha_source, Image.Image):
        al = np.array(alpha_source.convert("RGBA"))[:, :, 3].astype(float)
    else:
        al = np.asarray(alpha_source, float)
    H, W = al.shape
    blurred = np.array(
        Image.fromarray(al.astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(radius=blur)
        )
    ).astype(float)
    dx, dy = int(round(offset[0])), int(round(offset[1]))
    blurred = np.roll(blurred, (dy, dx), axis=(0, 1))
    if dy < 0:
        blurred[dy:, :] = 0
    elif dy > 0:
        blurred[:dy, :] = 0
    out = np.zeros((H, W, 4), float)
    out[:, :, :3] = _hex(color)
    out[:, :, 3] = blurred * opacity
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def rim_glow(subject, shadow, source_card_px=None) -> Image.Image:
    """Build the silhouette rim-glow for ``subject`` from a :class:`DropShadow`.

    ``shadow`` is a ``figforge.forensics.DropShadow`` (or anything with
    ``color``, ``opacity``, ``blur``, ``dx``, ``dy``). Figma specifies the blur
    in the *card's* coordinate space; pass ``source_card_px=(card_w, subject_w)``
    to scale the blur/offset from card pixels to the subject image's pixels.
    """
    blur, dx, dy = shadow.blur, shadow.dx, shadow.dy
    if source_card_px:
        card_w, subj_w = source_card_px
        scale = subj_w / float(card_w)
        blur *= scale
        dx *= scale
        dy *= scale
    return drop_shadow(subject, shadow.color, shadow.opacity, blur, (dx, dy))


def bake(layers, size, background) -> Image.Image:
    """Composite a bottom-to-top stack of (image, (x, y)) layers onto a flat
    background colour and return a single RGB image — the email-safe deliverable.
    """
    W, H = size
    canvas = Image.new("RGBA", (W, H), _hex(background) + (255,))
    for layer in layers:
        img, pos = layer if isinstance(layer, tuple) else (layer, (0, 0))
        if img is None:
            continue
        canvas.alpha_composite(img.convert("RGBA"), (int(pos[0]), int(pos[1])))
    return canvas.convert("RGB")
