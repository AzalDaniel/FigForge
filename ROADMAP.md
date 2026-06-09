# figforge roadmap

figforge today does one thing well: turn a **Figma SVG export** into **email-safe,
pixel-faithful HTML assets**, then *verify* the result by rendering and diffing.
This roadmap is about generalizing that — from "one email layout" toward "any
Figma design → HTML/CSS, with no paid tools" — while keeping the
**bake-don't-layer** philosophy that makes the output bulletproof in real email
clients.

It's deliberately incremental: every item below is additive and keeps the
current SVG→bake→table path working.

## Guiding idea: parse → infer → IR → emit

Every serious design-to-code converter shares the same shape — parse the design,
infer its structure, lower it to a neutral **intermediate representation (IR)**,
then emit code from the IR. Builder's Visual Copilot uses the open-source Mitosis
compiler as its IR; Kombai decomposes into *sections → components → styles*. The
lesson for figforge: introduce a small IR between `forensics` and the emitters so
we can **keep pixel-baking decorative regions** (gradients, glows, photos) while
**emitting real semantic markup** (text, buttons, columns) for the rest.

```
ingest (SVG today, +REST API later)
   └─ forensics  → IR (nodes: geometry · role · style · layout)
                     ├─ email emitter   (tables + baked <img>, today)
                     ├─ MJML emitter    (responsive, Outlook-safe — planned)
                     └─ web emitter      (flow/flex HTML — planned)
```

## Phase 1 — near term (sharpen what exists)

- **Data-driven lint.** Back each `lint` rule with a [caniemail](https://www.caniemail.com/)
  feature key + a one-line rationale URL, so the rule set is an auditable,
  contributor-friendly matrix rather than ad-hoc heuristics. Cross-check against
  Campaign Monitor's [CSS-support guide](https://www.campaignmonitor.com/css/)
  (278 properties × 35 clients).
- **Better verification.** Add an SSIM metric with a **per-pixel SSIM map**
  (`skimage.metrics.structural_similarity(..., full=True)`) for the diff heatmap,
  and an optional **CIEDE2000 (ΔE)** color check for gradient/recolor accuracy
  (perceptually uniform, unlike RGB distance). SSIM correlates with human
  perception far better than raw pixel MSE.
- **Optional Playwright/Chromium HTML render backend.** Webmail (Gmail, Apple
  Mail) uses Blink/WebKit-class engines, so a headless-Chromium screenshot is a
  closer "actual" than WeasyPrint. Keep **CairoSVG** for the deterministic SVG
  *reference*. **Honesty note:** no headless engine reproduces Outlook's Word
  engine — figforge's diff verifies *design intent*, not Outlook specifically;
  true Outlook checks need a real client or a paid testing service.
- **Document the math as first-class operations.** The two effect translations
  figforge already does deserve named, documented APIs:
  - *patternTransform crop* — inverting the affine matrix `box = a·src + e` to
    recover which slice of a source raster a frame shows.
  - *silhouette glow vs. box shadow* — `drop-shadow()` / the SVG
    `feGaussianBlur→feOffset→feColorMatrix` chain follows the alpha contour,
    unlike `box-shadow` which follows the border box. This is exactly what
    `rim_glow` exploits.

## Phase 2 — mid term (read intent, extract tokens)

- **Figma REST API ingester.** An SVG export has already flattened away layout
  intent (auto-layout, rows/columns). The REST node tree preserves it —
  `layoutMode`, `primaryAxisAlignItems`/`counterAxisAlignItems`, `itemSpacing`,
  padding, and `absoluteBoundingBox`. Add an optional front-end so `forensics`
  can ingest **either** an SVG (pixel-exact) **or** the node tree (semantic).
  Figma auto-layout maps almost directly to flexbox.
- **Define the IR** (node tree: geometry · role ∈ {text, button, image,
  container, decoration} · style · layout ∈ {flow, absolute, flex-row, flex-col}).
- **DTCG design-token extraction.** Emit colors/spacing/typography/shadows/
  gradients in the [W3C Design Tokens Community Group format](https://www.designtokens.org/)
  (first stable version **2025.10**) — `$value`/`$type`, composite `shadow`/
  `gradient`/`typography` types, `{alias}` references — then hand off to
  [Style Dictionary v4](https://styledictionary.com/info/dtcg/) for CSS variables
  and other platforms. This one feature makes figforge useful to design-system
  teams well beyond email.

## Phase 3 — longer term (full generalization)

- **Structural / component inference** for absolute-only designs (group elements
  into rows/columns/components — the hard part the commercial tools differentiate
  on).
- **MJML emitter.** Emit `mj-section`/`mj-column`/`mj-group` and let
  [MJML](https://mjml.io/) own ghost-tables, VML backgrounds, and column-stacking
  — the most error-prone Outlook-compat work, externalized to a battle-tested
  standard. Highest-leverage emitter to add.
- **Generic-web emitter** (flow/flex HTML) for non-email use, optionally mapping
  extracted tokens onto [Open Props](https://open-props.style/).

## Standards we align with

| Concern | Standard / source |
|---|---|
| Responsive email output | [MJML](https://mjml.io/) |
| Client CSS-support truth | [caniemail.com](https://www.caniemail.com/) · [Campaign Monitor CSS guide](https://www.campaignmonitor.com/css/) |
| Design tokens | [W3C DTCG Format 2025.10](https://www.designtokens.org/) · [Style Dictionary v4](https://styledictionary.com/info/dtcg/) |
| Design ingestion | [Figma REST API](https://developers.figma.com/docs/rest-api/) |
| Verification metrics | [scikit-image](https://scikit-image.org/) (SSIM/MSE/PSNR) · colour-science / colormath (ΔE2000) |

Contributions toward any of these are very welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md). The most immediately useful PRs are new
caniemail-backed `lint` rules and additional `forensics` coverage for Figma /
Anima / Kombai export shapes.
