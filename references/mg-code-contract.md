# ChatCut Desktop Motion Graphic code contract

Desktop validates every Motion Graphic before registering it. Read this before
authoring `create_motion_graphic_from_code` payloads.

## Injected globals

Motion Graphic code imports nothing. Only these names exist beyond the code
itself, `item.props`, ordinary browser globals, and React plus its hooks:

`AbsoluteFill`, `Easing`, `Img`, `interpolate`, `interpolateColors`, `Loop`,
`random`, `Sequence`, `Series`, `spring`, `useCurrentFrame`, `useVideoConfig`,
`Video`, `React`.

There is no `Remotion` namespace. The web runtime injects a much larger set
(`FitText`, `Audio`, `staticFile`, transform/d3/culori helpers, Remotion's
shapes and text helpers); those 59 names are **rejected** on Desktop, so build
the same result from HTML, CSS, SVG, or the list above.

## Rules the validator enforces

1. Pure JavaScript JSX, no TypeScript, no `import`, no `export default`.
2. Define `const Component = ({ item }) => { ... }` and read every editable
   value from `item.props`.
3. Never append fallbacks such as `|| "Default"` or `?? false` after a declared
   property — declared properties already have values.
4. No `Sequence` wrappers inside the component; express timing with flat
   frame-driven logic.
5. No inline logic inside JSX props; precompute every value.
6. The root element is `<div style={rootStyle}>` with
   `{position:"absolute", inset:0}`. `AbsoluteFill` is a component, never a
   style object, and never the root.
7. `width`/`height` on the asset are the natural box around the local
   composition. Full-frame beats may use the timeline size; overlays use a
   bounded box and are positioned by `edit_item`.
8. Never use emoji, arrows, triangles, or icon-font glyphs; draw marks with CSS
   geometry or one inline `<svg>` that shares a coordinate system.
9. `Img`/`Video` sources must come from image/video properties holding project
   asset ids, never URLs or paths.
10. Keep inline `<svg>` markup frame-invariant and animate the wrapper
    (`transform`, `opacity`) instead; that is also the cheaper export path.

## Pitfalls that cost round trips

- **Prefer `React.createElement`** for repeated elements (grids, particles,
  lists). It sidesteps JSX-in-string parsing surprises and reads clearly for
  generated loops.
- **Do not depend on `Easing` method names or `interpolate` option keys.**
  Define local helpers instead, so the graphic cannot fail on an API detail:

  ```javascript
  const clamp01 = (v) => Math.min(1, Math.max(0, v));
  const prog = (start, len) => clamp01((frame - start) / len);
  const easeOut = (t) => 1 - Math.pow(1 - t, 3);
  const mix = (a, b, t) => a + (b - a) * t;
  ```

- **Deterministic randomness:** use a local hash, not `Math.random()`, or the
  graphic changes on every rendered frame and export:

  ```javascript
  const hash = (n) => {
    const s = Math.sin(n * 12.9898) * 43758.5453;
    return s - Math.floor(s);
  };
  ```

- **Staggering:** `start = base + i * stepFrames`, then drive each element with
  `prog(start, len)`. Letter reveals use an `overflow:hidden` wrapper with the
  inner span translated `120% -> 0`.
- **Bars and other growth:** fixed-size track plus an inner fill with
  `transform: scaleY(t)` and `transformOrigin: "bottom center"` (cheap, stable
  export). Rows use `scaleX(t)` with `transformOrigin: "left center"`.
- **Text layout:** flex or grid with `gap`, natural wrapping, and headroom for
  the largest animated state. Never position readable text with independent
  hardcoded `top` values.
- **Backgrounds:** the root is transparent by default. An asset that paints a
  surface must expose a `transparentBackground` boolean property.

## Validated 30-second recipe

Canvas 1920x1080 @ 30 fps, 900 frames.

| Asset | Size | Duration | Placement |
| --- | --- | --- | --- |
| Background: drifting dual glow, slow grid, rising particles | 1920x1080 | 900 | V1 at frame 0 |
| Scene 1: title — letters rise in, growing rule, HUD corners | 1920x1080 | 240 | V2 at 0 |
| Scene 2: three process rows sliding in with progress fills | 1920x1080 | 210 | V2 at 240 |
| Scene 3: counter plus five bars growing from the baseline | 1920x1080 | 240 | V2 at 450 |
| Scene 4: rotating mark, wordmark, CTA pill, end fade | 1920x1080 | 210 | V2 at 690 |

Palette that reads well on the dark background:
base `#05070F`, accent `#22D3EE`, secondary glow `#A855F7`, deep accent
`#6366F1`, text `#F8FAFC`, secondary text `#94A3B8`, cards
`rgba(255,255,255,0.06)`.

Every scene fades in over about 12 frames and out over its last about 24, which
makes back-to-back placement read as a dissolve.

## Verification and export

- Contact sheet: `preview_timeline` with `views:["viewer"]` and 12-20
  `viewerFrames` across the piece.
- Detail: re-render the settled frame of each scene alone so the cell is large
  enough to read small text.
- Export: `local_export` with `format:"video"`, `resolution:"1080p"`, `fps:30`
  and a **relative** `outputPath`; absolute paths open a native Save dialog.
  Renders finish in the background — poll `track_progress` with
  `{"target":"export","action":"status","jobId":"..."}`.
