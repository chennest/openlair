# Frontend style decision

## Decision

- `lairweb/` (Vue 3 + TypeScript web admin) uses the **Apple Liquid Glass** visual language — the calm, premium look of apple.com / Apple Newsroom / the latest macOS — as its default UI style.
- The authoritative design system lives in the agent skill at [`agents/skills/apple-design-skill/`](../agents/skills/apple-design-skill/) (source: [`naplesblue/apple-design-skill`](https://github.com/naplesblue/apple-design-skill), MIT; cloned locally without `.git` history so it can be tracked in this repo).
- **The style rules, tokens, components, and motion spec ARE the skill files.** Treat the skill as the single source of truth; do not maintain a parallel summary here. Frontend work must load and follow the skill.

## Skill files (the actual style guide)

| File | Role |
|---|---|
| `SKILL.md` | Entry point — philosophy, workflow, anti-slop list, self-check. Read first. |
| `design-system.md` | Full spec: color, type scale, spacing/radius/shadow tiers, glass recipe, material depth grammar, responsive. |
| `tokens.css` | `:root` custom properties — drop into the project, reference via `var(--…)`. |
| `components.md` | Copy-paste HTML+CSS: glass nav, unified panel list, card grid, segmented control, tags, buttons, colored CTA, toggle, live dot. |
| `patterns.md` | Page-level recipes (reading 720 / grid 1080 containers · detail / index / home / form archetypes) + decision trees. |
| `motion.md` | Fluid interaction layer for summoned/dismissed surfaces: springs, interruptibility, same-path enter/exit, materialize, reduced-motion. |
| `app.md` | App / iOS shell layer: device frame (exact iPhone spec), status bar, large-title-collapse nav, tab bar, edge-anchored bottom sheet, safe areas, mobile-first rules. |
| `icons.md` | Line-icon layer: curated Lucide inline SVG set (24-grid, one stroke), grayscale `currentColor`, accent only on action/active, size table, restraint rules. |
| `checklist.md` | The standalone "done" gate. |
| `review.md` | Review-mode workflow for auditing existing UI against the system. |
| `reference.html` | Rendered living style guide — open in a browser; the ground-truth look. |
| `examples/` | Rendered example pages (`account.html`, `wallet.html`) plus screenshots. |

## Core rules (condensed from `SKILL.md`)

1. **Unified surface > fragmented cards** — one white panel with hairline dividers, not a pile of cards.
2. **Glass is seasoning, not the dish** — `backdrop-filter` only where layers overlap (nav / overlay / colored CTA).
3. **Restraint is luxury** — whitespace and hierarchy before borders/fills/icons/numbers.
4. **Hierarchy from weight + size + grayscale, not color** — color is accent only (one blue).
5. **Apple quality lives in details** — negative tracking, `tabular-nums`, hairlines, gentle hover lift, 180%-saturation glass, scroll-edge nav.

## How to use in frontend work

- **Build mode** (from `SKILL.md`): read `design-system.md` → drop in `tokens.css` → pick a page recipe from `patterns.md` → compose from `components.md` → apply `motion.md` for interactive layers (and `app.md` + `icons.md` for app/iOS-style screens) → check against `reference.html` → run the `checklist.md` gate.
- **Review mode** (`review.md`): audit existing CSS/pages, score against the system, return prioritized `file:line`-cited fixes mapped back to tokens.
- **Vue**: the skill is framework-agnostic. Translate the CSS into SFC scoped styles / a global token layer while keeping the **exact token values**, the panel-not-cards pattern, and the glass-only-on-overlap rule. Use flex/grid + `gap`, `clamp()` sizing, and the ~`680px` responsive breakpoint from `design-system.md`.
- **Triggers** that should load the skill: "Apple style", "liquid glass", "make it look like apple.com", "clean / premium / minimal", "苹果风", "液态玻璃".

## License note

Skill files are MIT (naplesblue; motion layer MIT © Emil Kowalski; icons ISC © Lucide Contributors). It teaches a visual language and ships no Apple assets; not affiliated with or endorsed by Apple Inc.
