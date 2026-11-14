# Copi logo and website specification

**Juan — v27 · 14 November 2026**

Exact design values for reproducing the current Copi website and presentation identity. Website source: Juan — v26. The approved logo has the rising pointed i accent from v26, superseding the blunt v14 shape packaged in v25. All sizes below are CSS pixels unless stated otherwise.

## Font specification

```css
font-family: -apple-system, BlinkMacSystemFont,
             "Helvetica Neue", Helvetica, Arial, sans-serif;
```

There is no downloaded font or bundled font file. The browser chooses the first available font: Apple’s system face on Apple platforms, with Helvetica Neue, Helvetica, Arial and generic sans-serif as fallbacks. Consequently the exact letter shapes and widths depend on the operating system. Weight 800 is requested by CSS; the available font determines the rendered face. Inter Extra Bold was used as a fallback in the earlier Figma title, but is not the website’s CSS font.

| Element | Font | Weight | Size | Line height / tracking |
| --- | --- | --- | --- | --- |
| Header logo `cop` | System stack | 800 | 40 | 1; native tracking |
| Main screen statement | System stack | 800 | `clamp(30px, 4.3vw, 46px)` | 1.13; native tracking |
| Opening statement | System stack | 800 | `clamp(28px, 3.6vw, 39px)` | 1.13 |
| Statements at ≤650 px | System stack | 800 | 33; opening 28 | 1.13 |
| Input explanation | System stack | Normal | 16; mobile 14 | Browser normal |
| ES/EN switch | System stack | 650 | 12 | Browser normal |
| Article masthead | Georgia, serif | Bold | 24 | Tracking −0.7 px |
| Article headline | Georgia, serif | 700 | 19 | 1.2 |
| Article quotation | Georgia, serif | Normal | 14 | 1.45 |
| Article date | System stack | Normal | 11 | Browser normal |

Buttons inherit the surrounding font. Most ordinary elements retain browser-normal line height; no global line-height token is defined. The serif treatment belongs to newspaper excerpts, not Copi’s identity.

## Logo construction

Use [the approved reference image](approved-logo-reference.png) and [the exact custom i SVG](approved-custom-i.svg). The logo is lowercase `cop` in the system stack plus a custom vector i, not a standard accented font character.

- Color: text `#121212`; custom i paths `#000000`.
- Custom glyph viewBox: `0 0 74 158`.
- Stem: diagonal top, flat bottom, x coordinates 2–31; baseline at y=154.
- Accent: rising pointed cap separated from the stem; its path has a `translate(0 20)` transform.
- Header text: 40 px, weight 800, line-height 1.
- Glyph placement: a transparent dotless `ı` reserves font-dependent advance; SVG is absolutely positioned inside that inline block.
- SVG size: `.44em × .939em` = 17.6 × 37.56 px at the 40 px logo size.
- SVG offset: left `.015em` = 0.6 px; top `-.08em` = −3.2 px. Margin 0; overflow visible.
- Preserve aspect ratio and the diagonal gap. Do not replace the pointed cap with a tilde, rounded dot, or v14 blunt cap.

Exact approved geometry:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 74 158">
  <path transform="translate(0 20)"
    d="M2 48 C1 27 9 18 25 15 C44 12 58 4 70 0 C61 16 46 23 38 34 C31 42 31 50 31 57 Z"
    fill="#000"/>
  <path d="M2 84 L31 93 L31 154 L2 154 Z" fill="#000"/>
</svg>
```

The earlier full pitch wordmark uses faint `cocococo`, solid `copi`, and faint `lot`. Its recorded settings are weight 800, line-height 1, font size `9.583333cqw` (184 px on a 1920 px canvas), tracking `-.03261em`, on a centered 16:9 white slide. Prefix black opacity rises from 4% to 30%; ending fades from 30% to 4%. Only `copi` is fully opaque. These gradient and tracking settings are logo-specific. The older full-wordmark PNG in v25 contains the superseded blunt glyph; use the approved pointed geometry for new compositions.

There is no established numerical clear-space or minimum-logo-size rule yet. Keep the accent and stem visibly separate at the actual output size. For consistent exchange, outline the text in the design tool or export a rendered image; live system-font text can change between computers.

## Color palette

| Role | Exact value |
| --- | --- |
| Canvas | `#ffffff` |
| Primary text | `#121212` |
| Functional icon / button ink | `#111111` |
| Narrative illustration ink / active step | `#151515` |
| Custom logo glyph | `#000000` |
| Soft controls | `#f4f5f7` |
| Diagram core surfaces | `#f2f3f5` |
| Selected input surface | `#e4e8ef` |
| Article surface | `#f8f8f7` |
| Mismatch highlight | `#f8dfcd` |
| Evidence dot in human handoff | `#e2b58e` |
| Main diagram connector | `#b9c0cc` |
| Scan mark | `#7f8fa7` |
| Inactive step | `#d5d5da` |
| Input explanation | `#64646c` |
| Language switch | `#666975` |
| Article date | `#707078` |
| Article quote | `#55555d` |
| Quote left rule | `#c9ced5` |
| Keyboard focus | `#4265d2` |

Individual narrative connectors also use `#dedfe3`, `#bec3cc`, `#c6cbd4`, `#aeb7c5`. These are decorative grays, not body-text colors. Convey a mismatch with shape and text as well as peach.

## Layout and surfaces

| Property | Desktop | At ≤650 px |
| --- | --- | --- |
| Header | 100 high; padding 28 px 6% | 85 high; padding 24 |
| Main | Centered, max-width 900; side padding 28 | Side padding 24 |
| Stage | Minimum height 535 | Minimum height 510 |
| Illustration area | Height 320 | Height 290 |
| Opening illustration | Height 195 | Height 165 |
| Main statement | Max-width 730; top margin 15 | Same width limit |
| Opening statement | Max-width 700 | Same width limit |
| Interactive diagram | Max-width 690 | Responsive |
| Navigation | Padding 15px 0 35px; gap 16 | Gap 8 |
| Previous/next buttons | 54 × 54; radius 25 | 48 × 48 |
| Input buttons | 90 × 90; radius 28 | 65 × 65; radius 22 |
| Article grid | Two equal columns; gap 26; margin 26px 0 25px | One column; gap 22 |
| Article surface | Padding 20px 22px; radius 20; min-height 213 | Padding 18px 20px; no min-height |
| Language switch | Min 44 × 44; radius 18 | Same |

Global `box-sizing: border-box`. The heading is centered and the logo sits at the left of the header; the language switch sits at the right. Each screen has one main sentence and one narrative illustration. No decorative subheadings or visible revision labels.

Soft control material:

```css
background: #f4f5f7;
border: 0;
border-radius: 25px;
box-shadow:
  inset 0 1px 1px #fff,
  inset 0 -1px 2px #70798528,
  0 3px 7px #232c3a12;
```

Article shadow: `0 3px 14px #2025300a`. Quote left border: `2px solid #c9ced5`, with 12 px left padding. Links inherit color and have no underline. Depth is restrained and attached to surfaces, not individual letters.

## Icons and illustrations

Custom inline SVG paths; no icon package, external illustration service or image-generation model is used in this website reference.

- Functional icon grid: `viewBox="0 0 24 24"`, displayed 24 × 24 px.
- Stroke: 2.2 units, `#111`, `fill="none"`, round caps and joins.
- Input icons: 43 × 43 px, reduced to 32 × 32 on mobile.
- Narrative scene grid: `viewBox="0 0 700 320"`; displayed responsively. Larger paths use explicit strokes around 4–9 units.
- Symbols: waveform = orders/communications; clipboard = protocol; train = telemetry/context; eye = observation; exclamation = mismatch; person = human decision.
- Static reusable SVGs are in [the icon kit](../juan-v25/icons/) and [illustration kit](../juan-v25/illustrations/). Those shapes remain applicable; v25’s logo files do not represent the newest approved accent.

## Animation specification

Primary easing: `cubic-bezier(.2,.8,.2,1)`.

| Effect | Duration / delay | Geometry and behavior |
| --- | --- | --- |
| Page forward/back | 450 ms / 0 | Fade 0→1; x +35 or −35 px → 0; primary easing |
| Evidence arrival | 650 ms / 0, 150, 300 ms | Fade 0→1; y 20→0 px; primary easing |
| Connector reveal | 1100 ms / 100 ms | Dash array 450; dash offset 450→0; `ease`; retain final state |
| Observation signal | 1100 ms; repeat twice | Opacity .35→1→.35; `ease-in-out` |
| Scan | 1500 ms; repeat twice | x −45→45→−45 px; `ease-in-out` |
| Mismatch | 600 ms / 700 ms | Fade in; y 15→0; scale .8→1.06→1; primary easing |
| Human handoff | 1000 ms / 200 ms | Fade in; x −70→0; primary easing |
| Input hover/selection | 200 ms | Lift −5 px; selected surface `#e4e8ef` |
| Button press | Immediate | Scale .97 |
| Step indicator | 250 ms | Dot width 7→23 px and background change |

Motion illustrates observation, comparison, discrepancy and handoff. It does not represent connected AI processing or completed real-world actions. Navigation is manual, with buttons, step selection, keyboard arrows and horizontal touch gestures. The ES/EN switch retains the current screen.

Reduced-motion implementation:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
  }
  .draw { stroke-dashoffset: 0; }
}
```

## Accessibility and reproduction

Keyboard focus uses a 3 px `#4265d2` outline with 5 px offset. Icon buttons have accessible names; the logo is named “Copi”; narrative SVGs have descriptions. Maintain meaningful text when motion is disabled.

Target at least 44 × 44 px for controls. The current reference has 39 px-wide mobile step buttons, a known exception to improve when adapting it. Reduced motion removes animations and transitions; the existing CSS still applies instantaneous press/hover transforms.

Use [the complete v26 website snapshot](website-reference.html) to reproduce the exact layout and animation sequence. Open locally in a browser; it requires no framework, external fonts or build step. For presentations, use the same system-stack direction or the documented Inter Extra Bold fallback, the approved pointed i, a white canvas, near-black symbols, and one sentence per frame. Keep newspaper typography confined to attributed source excerpts.
