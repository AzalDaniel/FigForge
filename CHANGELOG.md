# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-09

### Added
- `forensics` — parse a Figma-exported SVG into a structured spec: rectangles,
  linear/radial gradients (with stops), drop-shadow filters (color, opacity,
  blur, offset), image patterns (with the source-crop fractions), and embedded
  rasters. Group `<filter>`s are resolved onto their child rects.
- `assets` — `rasterize_svg` (with optional recolour), `extract_embedded_image`
  (decode base64 rasters), `content_crop`, `clean_alpha`, `dematte`.
- `effects` — `vertical_gradient_band`, `radial_glow`, `rim_glow` (from a
  drop-shadow spec), `drop_shadow`, and `bake`.
- `render` — `render_svg`, `render_html` (WeasyPrint → PyMuPDF), `side_by_side`,
  `diff`.
- `lint` — an email-robustness linter (background-size:cover, inline-block
  banner shrink, base64 images, missing `<img width>`, flex/grid, web-font
  fallback), comment- and MSO-aware.
- `figforge` CLI: `lint`, `rasterize`, `extract`, `spec`, `render-svg`,
  `render-html`, `diff`.

[Unreleased]: https://github.com/AzalDaniel/FigForge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AzalDaniel/FigForge/releases/tag/v0.1.0
