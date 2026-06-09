#!/usr/bin/env python3
"""Verify an email HTML against its Figma SVG by rendering both and diffing.

    python verify.py design.svg email.html [width]

Writes verify_target.png, verify_actual.png, verify_heat.png and prints the
mean-absolute-difference (0..1). < ~0.03 is effectively a 1:1 match; otherwise
the red regions of verify_heat.png show where to fix. Requires `figforge[render]`.
"""

import sys
from pathlib import Path

import figforge as ff


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    svg, html = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 680

    target = ff.render_svg(svg, width)
    target.save("verify_target.png")

    actual = ff.render_html(
        Path(html).read_text(encoding="utf-8"),
        (width, max(target.height, 2000)),
        base_url=Path(html).resolve().parent.as_uri() + "/",
    )
    actual.save("verify_actual.png")

    score, heat = ff.diff(target, actual)
    heat.save("verify_heat.png")
    verdict = "~match" if score < 0.03 else "review verify_heat.png"
    print(f"mean abs diff = {score:.4f}  ({verdict})")
    return 0 if score < 0.03 else 1


if __name__ == "__main__":
    sys.exit(main())
