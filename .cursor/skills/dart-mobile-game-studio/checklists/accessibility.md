# Accessibility checklist

A tick-list a reviewer/agent runs over the **renderer layer** (`lib/widgets/`, `lib/game/` overlays,
`lib/style/`) to confirm the game is usable with a screen reader, large text, and reduced motion on
**both** iOS (VoiceOver) and Android (TalkBack). It enforces the policies in
`references/dart/flutter-widgets-mastery.md` (Semantics, Reduce Motion, text scaling, tap targets),
`references/flutter-game-architecture.md` (a11y hooks), and `references/testing-and-release.md`
(QA + Families gate); it does not re-explain them. Check each box or note why it doesn't apply.
**Verify on a real device with the screen reader actually on** — `find.bySemanticsLabel` proves a
label exists, not that the flow is navigable.

Two automated gates back much of this (widget test, `package:flutter_test`):

```dart
final h = ensureSemantics();
await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
await expectLater(tester, meetsGuideline(androidTapTargetGuideline)); // 48x48
await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));     // 44x44
await expectLater(tester, meetsGuideline(textContrastGuideline));     // WCAG AA
h.dispose();
```

## Semantics on every control (no silent painted buttons)
- [ ] Every `CustomPaint`/`GestureDetector`-only control is wrapped in `Semantics` with a `label`; no painted/gesture-only button reaches the tree unlabeled (TalkBack/VoiceOver would skip it).
- [ ] Stateful controls (toggle, slider, selected tile, checkbox) expose a `value` that reflects current state ("on"/"off", "3 of 12"), not just a static `label`.
- [ ] Actionable nodes set the correct role/flags: `button: true` for buttons, `enabled:` reflecting real interactivity (a disabled control reads as disabled, not tappable), `hint:` for non-obvious actions.
- [ ] Built-in widgets (`IconButton`, `FilledButton`, `Slider`, `Checkbox`) are preferred over hand-painted controls where one fits — they ship correct semantics free; only *custom* surfaces are hand-annotated.
- [ ] `IconButton`/icon-only controls carry a `tooltip:`/`Semantics` label (a bare `Icon` has no accessible name).
- [ ] Label **values** ("3 of 12 matched", "You win") come from pure-model getters and are formatted at the edge — `package:flutter` does not leak into `models/` to build a string.
- [ ] `meetsGuideline(labeledTapTargetGuideline)` passes — every node with a tap/long-press action also has a label.

## MergeSemantics / ExcludeSemantics (clean reading order)
- [ ] Composite controls (icon + text, label + value) are wrapped in `MergeSemantics` so the reader announces them as **one** node, not two fragments.
- [ ] Purely decorative art (background, starfield, particle layer, ornamental frame) is wrapped in `ExcludeSemantics` (or `Semantics(excludeSemantics: true)`) so it is not exposed — never 64 unlabeled decorative tiles as 64 nodes.
- [ ] `image`/`Icon` decoration that conveys no meaning is hidden; only images that carry information get a label.
- [ ] Traversal order is logical (reads top-to-bottom / play-relevant); `Semantics(sortKey: OrdinalSortKey(...))` is used only where the visual order and DOM order genuinely diverge.

## Text scaling (Dynamic Type / font size)
- [ ] Text honors the OS text size: nothing locks a font that clips or overflows at the largest setting; verified at max system font scale on a real device.
- [ ] Text scale is read via the non-deprecated `MediaQuery.textScalerOf(context)` / `textScaler` — **not** the deprecated `textScaleFactor`.
- [ ] Any clamp uses `TextScaler` (e.g. `textScaler.clamp(maxScaleFactor: ...)`), and the clamp is justified — text is allowed to grow, not pinned to one size.
- [ ] Layouts flex with grown text (wrap/scroll/ellipsis as designed); no "yellow-and-black" overflow stripes and no truncated label at large scale.
- [ ] Animated/painted text reads `textScaler` too (a `TextPainter` in a `CustomPainter` is sized off the scaler, not a hard-coded `fontSize`).

## Reduce Motion (Remove animations)
- [ ] `MediaQuery.of(context).disableAnimations` (build) / `WidgetsBinding.instance.platformDispatcher.accessibilityFeatures.disableAnimations` (`initState`) is read **before** any animation and durations collapse to `Duration.zero` so motion snaps instead of playing.
- [ ] Looping/auto-reversing controllers are gated: `if (!WidgetsBinding.instance.platformDispatcher.accessibilityFeatures.disableAnimations) _c.repeat(...)` — no free-running tween when the user asked the OS to stop motion.
- [ ] The setting is never overridden "for polish"; reduced-motion is the user's choice, and the snapped path still leaves the game fully playable (state changes still land, just without the transition).
- [ ] Parallax/screen-shake/confetti and other vestibular-trigger effects are disabled (not merely shortened) under Reduce Motion.

## Touch target size (kids' fingers + a11y)
- [ ] Every interactive target is ≥ 48×48 logical px (Android floor; go larger for kids), enforced with `SizedBox`/`ConstrainedBox`/`MaterialTapTargetSize` — small visual icons keep a padded hit area.
- [ ] No overlapping `GestureDetector`s fight over one gesture; hit areas don't collide.
- [ ] `meetsGuideline(androidTapTargetGuideline)` (48×48) and `meetsGuideline(iOSTapTargetGuideline)` (44×44) both pass in a widget test.

## Contrast & not color-alone
- [ ] Text/icon vs background meets WCAG 2.1 AA: **4.5:1** for normal text, **3:1** for large text (≥18pt, or ≥14pt bold) — verified with a contrast checker, not by eye.
- [ ] `meetsGuideline(textContrastGuideline)` passes in a widget test for the key screens (menu, HUD, win/lose).
- [ ] Light **and** dark themes both pass contrast; nothing is hard-coded to one brightness such that the other fails.
- [ ] State is **never** signalled by color alone — correct/wrong, selected, current-player, team, matched: each pairs color with a second cue (shape, icon, label, text, pattern, or position) so colorblind players can tell them apart.
- [ ] Required/error states use an icon or text in addition to a red tint; success uses more than green.

## Screen-reader navigability (VoiceOver + TalkBack)
- [ ] With VoiceOver (iOS) **on**, you can swipe through every control in a sensible order and complete a full play loop (start → play → win/lose → restart) without sighted guesswork.
- [ ] With TalkBack (Android) **on**, the same full loop works; back-gesture/button behaves and no control is unreachable.
- [ ] Focus lands somewhere sensible after navigation/route changes (new screen, opened dialog) and isn't trapped behind an overlay; dismissing returns focus.
- [ ] Off-screen / occluded content (a panel behind a modal) is excluded from traversal so the reader doesn't read hidden nodes.
- [ ] Tested with the reader on a real device, not only via `find.bySemanticsLabel` in tests.

## Live-region announcements (don't spam, don't go silent)
- [ ] Key dynamic outcomes (win, lose, level-up, score milestone, "wrong, try again") are announced **once** via `Semantics(liveRegion: true, ...)` so the reader speaks them without the user hunting for the change.
- [ ] Live regions are scoped to genuinely-important changes — the per-frame score/timer is **not** a live region (it would talk over everything every frame).
- [ ] A transient announcement (snackbar-style) uses a live region or `SemanticsService.announce(...)` rather than relying on the user to find a silently-updated label.

## Manual QA pass (before handoff)
- [ ] Screen reader on (VoiceOver **and** TalkBack), largest system font, and Reduce Motion **all on at once** — the game is still navigable, legible, and playable end to end.
- [ ] Run on both an iOS device/simulator and an Android device/emulator — semantics, font scaling, and back-button behavior differ across platforms.
- [ ] Accessibility line of the Families/release gate (`references/testing-and-release.md`) is satisfied: `Semantics(label:/value:/...)` on every interactive control, large text respected, reduced motion respected.
