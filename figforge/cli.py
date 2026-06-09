"""figforge command line.

figforge lint email.html
figforge rasterize icon.svg --width 48 --recolor FFFFFF -o icon.png
figforge extract master.svg --image-id image1_521_50 -o photo.png
figforge spec master.svg                 # dump the forensic spec
figforge render-svg master.svg --width 680 -o ref.png
figforge render-html email.html --width 680 --height 1862 -o out.png
figforge diff a.png b.png -o heat.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _hex_to_rgb(s: str) -> tuple:
    s = s.lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="figforge",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("lint", help="flag email-client robustness hazards")
    s.add_argument("html")

    s = sub.add_parser("rasterize", help="SVG -> PNG (optional recolour)")
    s.add_argument("svg")
    s.add_argument("--width", type=int, required=True)
    s.add_argument("--height", type=int)
    s.add_argument("--recolor")
    s.add_argument("--supersample", type=int, default=3)
    s.add_argument("-o", required=True)

    s = sub.add_parser("extract", help="decode an embedded raster from an SVG")
    s.add_argument("svg")
    s.add_argument("--image-id")
    s.add_argument("-o", required=True)

    s = sub.add_parser("spec", help="print the forensic spec of an SVG")
    s.add_argument("svg")

    s = sub.add_parser("render-svg", help="render an SVG to PNG")
    s.add_argument("svg")
    s.add_argument("--width", type=int, default=680)
    s.add_argument("-o", required=True)

    s = sub.add_parser("render-html", help="render an HTML email to PNG")
    s.add_argument("html")
    s.add_argument("--width", type=int, default=680)
    s.add_argument("--height", type=int, default=2000)
    s.add_argument("--base-url")
    s.add_argument("-o", required=True)

    s = sub.add_parser("diff", help="diff two images (score + heatmap)")
    s.add_argument("a")
    s.add_argument("b")
    s.add_argument("-o")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if args.cmd == "lint":
        from .lint import lint_html

        findings = lint_html(Path(args.html).read_text(encoding="utf-8"))
        if not findings:
            print("clean — no email-robustness hazards found.")
            return 0
        for f in findings:
            print(f)
        print(f"\n{len(findings)} finding(s).")
        return 1 if any(f.severity == "high" for f in findings) else 0

    if args.cmd == "rasterize":
        from .assets import rasterize_svg

        recolor = _hex_to_rgb(args.recolor) if args.recolor else None
        rasterize_svg(
            args.svg, args.width, args.height, recolor, supersample=args.supersample
        ).save(args.o)
        print("wrote", args.o)

    elif args.cmd == "extract":
        from .assets import extract_embedded_image

        extract_embedded_image(args.svg, args.image_id).save(args.o)
        print("wrote", args.o)

    elif args.cmd == "spec":
        from .forensics import parse_svg

        doc = parse_svg(args.svg)
        print(f"size: {doc.width:g} x {doc.height:g}")
        print(
            f"rects: {len(doc.rects)}  gradients: {len(doc.gradients)}  "
            f"shadows: {len(doc.shadows)}  patterns: {len(doc.patterns)}  "
            f"images: {len(doc.images)}"
        )
        for r in doc.find_rects(min_w=20, min_h=20):
            g = doc.gradient_for(r)
            extra = ""
            if g:
                stops = "->".join(f"{s.color}@{s.opacity:.2g}" for s in g.stops)
                extra = f" grad[{g.kind}]={stops}"
            print(
                f"  rect x={r.x:g} y={r.y:g} w={r.w:g} h={r.h:g} fill={r.fill}{extra}"
            )

    elif args.cmd == "render-svg":
        from .render import render_svg

        render_svg(args.svg, args.width).save(args.o)
        print("wrote", args.o)

    elif args.cmd == "render-html":
        from .render import render_html

        html = Path(args.html).read_text(encoding="utf-8")
        render_html(html, (args.width, args.height), base_url=args.base_url).save(
            args.o
        )
        print("wrote", args.o)

    elif args.cmd == "diff":
        from PIL import Image

        from .render import diff

        score, heat = diff(Image.open(args.a), Image.open(args.b))
        print(f"mean abs diff: {score:.4f}")
        if args.o:
            heat.save(args.o)
            print("wrote", args.o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
