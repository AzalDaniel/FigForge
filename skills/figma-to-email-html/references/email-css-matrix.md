# Bake-vs-CSS decision matrix

Which Figma feature becomes CSS/HTML vs a baked image, and why. "Bake" = render
it into a flat PNG/JPG with `figforge.effects` and drop it in as one `<img>`.

| Figma feature | Gmail (web) | Apple Mail | Outlook (Win, Word engine) | Action |
|---|---|---|---|---|
| Solid fill, text, borders | ✅ | ✅ | ✅ | **CSS/HTML** |
| Web/Google font | partial | ✅ | ❌ (falls back) | CSS **with web-safe fallback**; bake only display headlines |
| Linear/radial gradient (CSS) | partial | ✅ | ❌ | **Bake** (`vertical_gradient_band` / `radial_glow`) |
| `background-image` + `background-size:cover` | unreliable | ✅ | ❌ | **Bake into a foreground `<img>`** (don't use cover) |
| Box-shadow / drop shadow | ❌ | ✅ | ❌ | **Bake** (`drop_shadow` / `rim_glow`) |
| Blur / glow | ❌ | ✅ | ❌ | **Bake** |
| Overlapping layers (`position:absolute`) | ❌ | ❌ | ❌ | **Bake** the composite (`bake`) |
| Rounded corners (`border-radius`) | ✅ | ✅ | ❌ (square) | CSS; bake if the corner is essential |
| Photo / image | ✅ | ✅ | ✅ | host as `<img>` (extract + clean cut-out) |
| Icon (monochrome) | ✅ | ✅ | ✅ | `rasterize --recolor` to transparent PNG |
| Flexbox / Grid layout | ❌ | partial | ❌ | **Tables** instead |
| base64 (`data:`) image | ❌ (stripped) | ✅ | partial | **Host it**; never inline |

## Hard-won rules

- **`background-size:cover` is the #1 trap.** It looks right in the design tool's
  preview and in Apple Mail, then crops differently per client. Bake the
  background + foreground into one image.
- **Full-bleed banners:** wrap in `display:block;width:100%` (or a fixed-px
  table). `display:inline-block` shrink-wraps to content and leaves a gap.
- **Outlook = Word.** For a background you truly need behind text, use a VML
  `<v:rect fill>` fallback inside `<!--[if mso]>`. Simpler: bake it.
- **Width ≈ 600–680px**, fixed. Give every image an explicit `width` attribute
  (Outlook ignores CSS width on some images).
- **Fonts:** ship a stack like `Archivo, Arial, Helvetica, sans-serif`; Outlook
  and Gmail-app won't load the web font.
- **Gmail clips** messages whose HTML exceeds ~102 KB — keep markup lean and host
  images (another reason to avoid base64).
