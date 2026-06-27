# Template: Coloring (tap-to-fill regions)

A **design brief + architecture skeleton** for a coloring book. Fill the brackets, implement against
the [`coloring-shapes` recipe](../references/game-templates.md) and
[`workflows/create-new-game.md`](../workflows/create-new-game.md).

**Mode:** Flutter-widgets-only (`CustomPainter`/`Canvas` + hit-testing). No game loop, fully
accessible, easiest to test. Never reach for Flame here.

---

## Mini-GDD (filled example — adapt)

- **One-liner:** `<tap a region of a picture to fill it with the picked color>`.
- **Audience & age:** ages 3–9, kids; open-ended sessions.
- **Core loop:** pick a color → tap a region → it fills → repeat until happy. **No-fail, no timer.**
- **Primary verb:** tap (region) + tap (palette swatch).
- **Failure model:** none — it's a toy. Optional "all regions filled" celebration.
- **Win / progression:** a gallery of pictures; unlock more by finishing (or all open for the youngest).
- **Art:** vector line-art (`Path`s) — regions are closed paths; a friendly 8–12 color palette.
- **Scope (in):** one picture, palette, fill, undo, clear, save image.
- **Cut-line (later):** patterns/gradients, stickers, more pictures, share.

## Architecture skeleton (pure Dart, no Flutter import)

```
lib/models/   picture.dart      # immutable: List<Region> (id, path-ref, fillColorToken?)
              region.dart        # id, neighbor/bounds metadata, current color token (int)
              palette.dart       # ordered color tokens; selected index
              coloring_state.dart# picture + palette + undo stack; copyWith, ==/hashCode
lib/systems/  fill_system.dart  # applyFill(state, regionId, colorToken) -> new state; pure
              picture_loader.dart# parse picture JSON (regions + path data) -> Picture; pure
lib/widgets/  coloring_screen.dart # CustomPainter draws regions by color token; hit-test on tap
              palette_bar.dart  # swatches with Semantics
```

- **Color as data token, not `Color`.** The pure model stores an `int`/enum token; the painter maps
  token → `Color` at the renderer edge (keeps `models/` Flutter-free and VM-testable).
- **Regions as data (JSON):** path geometry + region ids in `assets/`, parsed by a pure loader.
- **Hit-testing:** `Path.contains(offset)` in the painter/gesture layer maps a tap to a region id;
  the model just records `regionId → token`.

## Genre specifics (what matters here)

- **Never rely on color alone** — regions are also outlined; the picked swatch shows a check + label
  so a color-blind child can play.
- **Undo is essential** (kids mis-tap constantly); keep a bounded undo stack in the model.
- **Save the artwork** (`RepaintBoundary` → image) without any network/share for a kids build.
- **No "wrong" fills** — any region accepts any color; this is expression, not a puzzle.

## Genre checklist

- [ ] Color stored as a data token in the model; `Color` only at the renderer edge.
- [ ] Regions/picture are JSON data, parsed by a pure loader, unit-tested.
- [ ] Undo + clear; bounded undo stack; `dart test` covers fill + undo.
- [ ] `Semantics` on every swatch and region; playable without color alone.
- [ ] No-fail, no timer, no network; save stays on-device.

## See also
- [`references/game-templates.md`](../references/game-templates.md) — `coloring-shapes` recipe.
- [`references/asset-pipeline.md`](../references/asset-pipeline.md) — vector art + level/picture JSON.
- [`workflows/create-new-game.md`](../workflows/create-new-game.md) · [`references/accessibility-child-safety.md`](../references/accessibility-child-safety.md).
