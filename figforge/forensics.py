"""Read a Figma-exported SVG into a structured, queryable spec.

Figma exports (and the Anima/Kombai variants of them) encode everything you
need to rebuild an asset 1:1 — exact rectangles, gradient stops, drop-shadow
filters and the pattern transforms that crop a raster into a frame. This module
turns that XML into small dataclasses so a recipe can ask questions like
"where is the gold stripe and what are its gradient stops?" instead of
hand-grepping a 2.7 MB file.

Everything here is read-only and dependency-free (stdlib ``xml`` only); the
heavier pixel work lives in :mod:`figforge.assets` and :mod:`figforge.effects`.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

_SVG = "{http://www.w3.org/2000/svg}"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _num(v, default: float = 0.0) -> float:
    if v is None:
        return default
    m = re.match(r"\s*(-?\d*\.?\d+)", str(v))
    return float(m.group(1)) if m else default


def _href(el) -> str | None:
    for k in ("href", "{http://www.w3.org/1999/xlink}href"):
        if k in el.attrib:
            return el.attrib[k]
    return None


@dataclass
class GradientStop:
    offset: float
    color: str  # "#RRGGBB"
    opacity: float  # 0..1


@dataclass
class Gradient:
    id: str
    kind: str  # "linear" | "radial"
    stops: list  # list[GradientStop]
    coords: dict  # linear: x1,y1,x2,y2 ; radial: cx,cy,r
    units: str  # "userSpaceOnUse" | "objectBoundingBox"

    @property
    def vertical(self) -> bool:
        if self.kind != "linear":
            return False
        return abs(self.coords.get("x1", 0) - self.coords.get("x2", 0)) < 1e-6


@dataclass
class DropShadow:
    """A Figma drop shadow distilled from an SVG ``<filter>``.

    ``color`` is RGB 0..255, ``opacity`` 0..1, ``blur`` is the
    ``feGaussianBlur`` stdDeviation, ``dx``/``dy`` the ``feOffset`` (a negative
    ``dy`` pushes the shadow *up*). ``region`` is the filter's clip box.
    """

    id: str
    color: tuple  # (r, g, b) 0..255
    opacity: float
    blur: float
    dx: float
    dy: float
    region: tuple | None  # (x, y, w, h)


@dataclass
class ImagePattern:
    id: str
    image_id: str
    matrix: tuple  # (a, b, c, d, e, f)
    image_w: int
    image_h: int


@dataclass
class EmbeddedImage:
    id: str
    w: int
    h: int
    href: str  # full data URI


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float
    fill: str  # "#RRGGBB" or "url(#id)" or "none"
    rx: float = 0.0
    filter: str | None = None  # filter id (without url(#...))

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


def _ref_id(value: str | None) -> str | None:
    """``url(#paint0_linear)`` -> ``paint0_linear``."""
    if not value:
        return None
    m = re.search(r"url\(#([^)]+)\)", value)
    return m.group(1) if m else None


def _parse_matrix(transform: str | None) -> tuple:
    """Parse a ``transform`` into (a, b, c, d, e, f). Handles matrix() & scale()."""
    if not transform:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    m = re.search(r"matrix\(([^)]+)\)", transform)
    if m:
        v = [float(x) for x in re.split(r"[ ,]+", m.group(1).strip())]
        if len(v) == 6:
            return tuple(v)
    s = re.search(r"scale\(([^)]+)\)", transform)
    if s:
        v = [float(x) for x in re.split(r"[ ,]+", s.group(1).strip())]
        sx = v[0]
        sy = v[1] if len(v) > 1 else v[0]
        return (sx, 0.0, 0.0, sy, 0.0, 0.0)
    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _color_from_matrix(values: str):
    """Pull (rgb, alpha-multiplier) out of an feColorMatrix ``values`` string.

    Figma shadow matrices look like ``0 0 0 0 R  0 0 0 0 G  0 0 0 0 B  0 0 0 A 0``
    so R,G,B live at indices 4,9,14 and the alpha multiplier at 18.
    """
    nums = [float(x) for x in re.split(r"[ ,\n\t]+", values.strip()) if x]
    if len(nums) < 20:
        return (0, 0, 0), 1.0
    r, g, b, a = nums[4], nums[9], nums[14], nums[18]
    return (round(r * 255), round(g * 255), round(b * 255)), a


class Document:
    """Parsed SVG with helpers to resolve a rect's gradient / shadow / pattern."""

    def __init__(
        self, width, height, rects, gradients, shadows, patterns, images, root
    ):
        self.width = width
        self.height = height
        self.rects = rects  # list[Rect], document order
        self.gradients = gradients  # id -> Gradient
        self.shadows = shadows  # id -> DropShadow
        self.patterns = patterns  # id -> ImagePattern
        self.images = images  # id -> EmbeddedImage
        self.root = root

    # -- resolvers -----------------------------------------------------------
    def gradient_for(self, rect: Rect) -> Gradient | None:
        return self.gradients.get(_ref_id(rect.fill))

    def shadow_for(self, rect: Rect) -> DropShadow | None:
        return self.shadows.get(rect.filter)

    def pattern_for(self, rect: Rect) -> ImagePattern | None:
        return self.patterns.get(_ref_id(rect.fill))

    def pattern_crop(self, pattern_id: str) -> tuple | None:
        """Visible source crop of a pattern as fractions ``(x0, x1, y0, y1)``.

        For an ``objectBoundingBox`` pattern, ``box = a*src_px + e``; solving for
        the box [0..1] gives the source-pixel window, expressed here as 0..1
        fractions of the source image. This is exactly how you find "which slice
        of the photo is shown in the frame".
        """
        pat = self.patterns.get(pattern_id)
        if not pat:
            return None
        a, b, c, d, e, f = pat.matrix
        x0 = (0 - e) / a / pat.image_w
        x1 = (1 - e) / a / pat.image_w
        y0 = (0 - f) / d / pat.image_h
        y1 = (1 - f) / d / pat.image_h
        return (x0, x1, y0, y1)

    def find_rects(self, *, min_w=0, min_h=0, fill_is_gradient=None):
        out = []
        for r in self.rects:
            if r.w < min_w or r.h < min_h:
                continue
            if fill_is_gradient is True and _ref_id(r.fill) not in self.gradients:
                continue
            out.append(r)
        return out


def parse_svg(path: str) -> Document:
    """Parse a Figma-exported SVG file into a :class:`Document`."""
    tree = ET.parse(path)
    root = tree.getroot()

    width = _num(root.get("width"))
    height = _num(root.get("height"))
    if (not width or not height) and root.get("viewBox"):
        vb = [float(x) for x in re.split(r"[ ,]+", (root.get("viewBox") or "").strip())]
        width = width or vb[2]
        height = height or vb[3]

    rects, gradients, shadows, patterns, images = [], {}, {}, {}, {}

    # Figma usually puts a drop-shadow filter on a wrapping <g>, not the rect
    # itself, so resolve a rect's filter from itself or its nearest ancestor.
    parent = {c: p for p in root.iter() for c in p}

    def _ancestor_filter(el):
        cur = el
        while cur is not None:
            fid = _ref_id(cur.get("filter"))
            if fid:
                return fid
            cur = parent.get(cur)
        return None

    for el in root.iter():
        tag = _local(el.tag)

        if tag == "rect":
            rects.append(
                Rect(
                    x=_num(el.get("x")),
                    y=_num(el.get("y")),
                    w=_num(el.get("width")),
                    h=_num(el.get("height")),
                    fill=el.get("fill", "none"),
                    rx=_num(el.get("rx")),
                    filter=_ancestor_filter(el),
                )
            )

        elif tag in ("linearGradient", "radialGradient"):
            stops = []
            for s in el:
                if _local(s.tag) != "stop":
                    continue
                style = s.get("style", "")
                color = s.get("stop-color")
                op = s.get("stop-opacity")
                if color is None:
                    m = re.search(r"stop-color:\s*([^;]+)", style)
                    color = m.group(1).strip() if m else "#000000"
                if op is None:
                    m = re.search(r"stop-opacity:\s*([\d.]+)", style)
                    op = m.group(1) if m else "1"
                stops.append(GradientStop(_num(s.get("offset")), color, _num(op, 1.0)))
            if tag == "linearGradient":
                coords = {k: _num(el.get(k)) for k in ("x1", "y1", "x2", "y2")}
            else:
                coords = {k: _num(el.get(k)) for k in ("cx", "cy", "r")}
            gradients[el.get("id", "")] = Gradient(
                id=el.get("id", ""),
                kind=tag.replace("Gradient", ""),
                stops=stops,
                coords=coords,
                units=el.get("gradientUnits", "objectBoundingBox"),
            )

        elif tag == "filter":
            blur = dx = dy = 0.0
            shadow_color, shadow_opacity, region = (0, 0, 0), 1.0, None
            x, y, w, h = el.get("x"), el.get("y"), el.get("width"), el.get("height")
            if None not in (x, y, w, h):
                region = (_num(x), _num(y), _num(w), _num(h))
            for fe in el.iter():
                t = _local(fe.tag)
                if t == "feGaussianBlur":
                    blur = _num(fe.get("stdDeviation"))
                elif t == "feOffset":
                    dx, dy = _num(fe.get("dx")), _num(fe.get("dy"))
                elif t == "feColorMatrix" and fe.get("values"):
                    shadow_color, shadow_opacity = _color_from_matrix(
                        fe.get("values") or ""
                    )
            shadows[el.get("id", "")] = DropShadow(
                id=el.get("id", ""),
                color=shadow_color,
                opacity=shadow_opacity,
                blur=blur,
                dx=dx,
                dy=dy,
                region=region,
            )

        elif tag == "pattern":
            use = next((c for c in el.iter() if _local(c.tag) == "use"), None)
            if use is not None:
                img_ref = (_href(use) or "").lstrip("#")
                patterns[el.get("id", "")] = ImagePattern(
                    id=el.get("id", ""),
                    image_id=img_ref,
                    matrix=_parse_matrix(use.get("transform")),
                    image_w=0,
                    image_h=0,  # filled in below once images known
                )

        elif tag == "image":
            href = _href(el) or ""
            images[el.get("id", "")] = EmbeddedImage(
                id=el.get("id", ""),
                w=int(_num(el.get("width"))),
                h=int(_num(el.get("height"))),
                href=href,
            )

    # backfill pattern image dimensions now that images are known
    for pat in patterns.values():
        img = images.get(pat.image_id)
        if img:
            pat.image_w, pat.image_h = img.w or 1, img.h or 1

    return Document(width, height, rects, gradients, shadows, patterns, images, root)
