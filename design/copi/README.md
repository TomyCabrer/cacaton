# Copi shared design kit — Juan — v25

For teammates building the website, pitch or presentation. This packages Juan’s existing design decisions; it does not restyle the shared drill. Start with [the visual website reference](juan-v25/website-reference.html) (download/open in a browser) and [the logo preview](juan-v25/logos/wordmark-preview.png).

## What is current

Juan liked the aesthetic and animations of v21. V22 added article previews and ES/EN switching; v23 removed editorial subheadings; v24 made the railway/controller context explicit. The included website reference is an unchanged copy of v24. V25 is the shared handoff, not a new website design. Earlier revisions and collaborators’ work remain separate.

The faint-prefix / solid-`copi` / faint-ending wordmark was explicitly approved in v3/v4. The latest local letterform is v14’s broad sculpted cap and short stem, also used by the v24 website. Its presence here records the current direction rather than inventing a separate final-logo approval. The early overlapping C/O/P monogram was exploratory and is not the default identity.

## Assets to use

| Asset | Purpose |
| --- | --- |
| [copi.svg](juan-v25/logos/copi.svg) | Compact current website identity; live font text plus exact custom i geometry |
| [custom-i.svg](juan-v25/logos/custom-i.svg) | Exact v14 vector letterform; preserve the cap, diagonal gap and baseline |
| [wordmark.html](juan-v25/logos/wordmark.html) | Preserved v14 full wordmark on a 16:9 white canvas |
| [wordmark-preview.png](juan-v25/logos/wordmark-preview.png) | Fixed rendered v14 wordmark for slides; avoids font substitution |
| [approved-wordmark-reference.png](juan-v25/logos/approved-wordmark-reference.png) | Earlier approved composition, before the custom accent revisions |
| [icons](juan-v25/icons/) | Individual SVGs: voice, rule, train, arrows, eye, alert, person |
| [illustrations](juan-v25/illustrations/) | Static SVG scenes: observation, comparison, mismatch, human decision, protocol review |
| [tokens.css](juan-v25/tokens.css) | Reusable surface, color, typography and depth values |
| [motion.css](juan-v25/motion.css) | Extracted animation classes/keyframes and reduced-motion override |
| [website-reference.html](juan-v25/website-reference.html) | Self-contained animated, bilingual reference with navigation |

Voice/rule/train and arrow paths are extracted from the website; eye/alert/person are normalized to the same 24-unit icon style for reuse. Illustrations are static exports of the website scenes; the comparison export includes the three input symbols normally rendered as buttons. They carry no live-data meaning.

The compact SVG contains system-font text, so rendering varies by machine. Use the PNG for consistent full-wordmark slides, or outline the text in your presentation/design tool before exchanging a final vector. Do not replace the custom i with a stock tilde. Do not stretch or recolor the mark. Keep the faint wordmark portions decorative; information must remain readable without them. The wordmark’s tight tracking and opacity gradients are identity-specific exceptions, not a template for body text.

## Presentation criteria

- White canvas, near-black text and symbols, generous whitespace. One sentence and one meaningful visual per screen. Keep the first screen explicit: “Copi is the AI copilot for railway controllers.”
- Use the system stack in `tokens.css`, weight 800 for main statements. Website headings are 30–46 px (33 px on narrow screens); scale proportionally for projection. The older Figma title used Inter Extra Bold as a rendering fallback. Ordinary text uses the reading font, natural tracking and sentence case.
- Center the main composition. Keep secondary evidence behind an action or in discreet attributed source previews. Avoid decorative eyebrows, editorial subheadings, visible revision labels, repeated cards and ornamental dashboards. Revision labels belong in filenames and handoff notes.
- Use pale cool gray for surfaces and soft depth only on actual controls. Primary controls have approximately 25 px corners. Symbols use black 2.2-unit strokes on a 24×24 grid with round caps and joins. Large narrative illustrations scale their strokes deliberately.
- Peach `#f8dfcd` highlights a mismatch, accompanied by an exclamation mark and words. Connector gray is decorative, not a body-text color. Blue `#4265d2` identifies keyboard focus. Avoid gradients outside the preserved wordmark, decorative chrome, and color-only status.
- Keep both source articles attributed and accessible; their presence is context, not official endorsement. The archived reference preserves its existing article text; this handoff does not independently verify the news or make new factual claims.

## Motion language

| Motion | Current reference | Meaning |
| --- | --- | --- |
| Next / previous screen | 450 ms; ±35 px horizontal move + fade; cubic-bezier(.2,.8,.2,1) | A deliberate step through the story |
| Inputs arriving | 650 ms; 20 px upward arrival; 0 / 150 / 300 ms delays | Distinct evidence sources assemble |
| Connector drawn | 1.1 s, 100 ms delay | Evidence is compared |
| Observation signal / scan | 1.1 s / 1.5 s, two repetitions | Conceptual observation, not a live processing indicator |
| Mismatch reveal | 600 ms after 700 ms; small scale settle | Attention moves to the conflict |
| Human handoff | 1 s after 200 ms; 70 px horizontal arrival | Evidence reaches the person deciding |
| Control press | Scale 0.97 | Immediate tactile feedback |

Reuse the animated HTML for the complete sequence; `motion.css` is the portable vocabulary and requires matching classes/SVG structure. Do not add perpetual loops, fake typing, simulated live telemetry or animations implying completed operational actions. For slides, reveal evidence before the discrepancy, then hand it to the human. Keep navigation manual and provide a static version. Reduced motion disables animation/transitions and exposes completed connector strokes.

## Accessibility and meaning

Provide visible keyboard focus, accessible icon-button names, keyboard navigation and touch targets at least 44 px. The existing reference has a known 39 px step-button width on narrow screens; enlarge that when adapting it rather than treating it as the target standard. Maintain readable contrast and avoid relying on animation or color to convey the point. Give standalone illustrations descriptive alt text; hide decorative icons from assistive technology when adjacent text already names them.

Copi supports human decisions. The pitch animations are conceptual, not connected AI, operational telemetry or validated safety outcomes. Acknowledgment is not execution; absence of evidence is not a confirmed omission. Preserve sources, timestamps, conflicts and unknowns in any operational illustration. The MVP is trains only. Do not claim zero error, certified safety, independent redundancy, or proven lives saved.

## Quick handoff check

Open the HTML locally, step through all five screens, switch ES/EN, and compare your slides against it. Check at presentation size and narrow width. Review keyboard focus and reduced motion. Import the supplied SVGs rather than mixing icon families. Preserve collaborator authorship; label later Juan revisions with the next version number.
