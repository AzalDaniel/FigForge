import base64
import io

import pytest
from PIL import Image


@pytest.fixture
def sample_svg(tmp_path):
    """A tiny Figma-shaped SVG: a gradient-filled rect inside a drop-shadow
    group, plus an image-pattern rect (declared 1024px source, real 8px PNG)."""
    buf = io.BytesIO()
    Image.new("RGBA", (8, 8), (200, 150, 100, 255)).save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="680" height="362" viewBox="0 0 680 362">
  <defs>
    <linearGradient id="g1" x1="511" y1="0" x2="511" y2="322" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#EFBF04"/>
      <stop offset="1" stop-color="#896D02" stop-opacity="0"/>
    </linearGradient>
    <filter id="f1" x="419" y="0" width="185" height="330">
      <feOffset dy="4"/><feGaussianBlur stdDeviation="2"/>
      <feColorMatrix values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.25 0"/>
    </filter>
    <pattern id="p1" patternContentUnits="objectBoundingBox" width="1" height="1">
      <use xlink:href="#img1" transform="scale(0.0010571 0.000976562)"/>
    </pattern>
    <image id="img1" width="1024" height="1024" xlink:href="data:image/png;base64,{b64}"/>
  </defs>
  <rect width="680" height="362" fill="#2D2C2C"/>
  <g filter="url(#f1)"><rect x="423" y="0" width="177" height="322" fill="url(#g1)"/></g>
  <rect x="356" y="57" width="282" height="305" fill="url(#p1)"/>
</svg>"""
    p = tmp_path / "sample.svg"
    p.write_text(svg)
    return str(p)
