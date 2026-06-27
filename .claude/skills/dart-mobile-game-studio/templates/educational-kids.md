# Template: Educational Kids (letters / numbers / shapes)

A **design brief + architecture skeleton** for an early-learning mini-game (alphabet, counting,
shapes, colors, phonics). Self-contained. The **kids-safety and accessibility bars are binding from
step 0**, not an afterthought — read [`references/accessibility-child-safety.md`](../references/accessibility-child-safety.md) first.

**Mode:** Flutter-widgets-only. Calm, tap/drag interactions; no loop, no pressure.

---

## Mini-GDD (filled example — adapt)

- **One-liner:** `<tap the letter the voice says / count the apples / match the shape>`.
- **Audience & age:** ages 2–6, **kids (Apple Kids Category + Google Play Families)**; sessions open-ended.
- **Core loop:** present a prompt (audio + visual) → child responds (tap/drag) → warm feedback → next, gently harder.
- **Primary verb:** tap / drag-to-place; large targets, forgiving.
- **Failure model:** **strictly no-fail** — a wrong tap gives a gentle "try again", never a loss, score, or red X.
- **Win / progression:** invisible difficulty ramp; lots of praise; no scores/timers/stars that pressure.
- **Art:** big friendly shapes, high contrast; one concept on screen at a time.
- **Scope (in):** one concept (e.g. letters A–E), prompt, response, positive feedback, gentle ramp.
- **Cut-line (later):** more concepts, progress for parents, voice packs, localization.

## Architecture skeleton (pure Dart, no Flutter import)

```
lib/models/   concept.dart      # immutable: a learnable item (letter/number/shape) + prompt/answer set
              lesson_state.dart  # current item, queue, attempts, masteredSet; phase; ==/hashCode
lib/systems/  lesson_loader.dart# parse concept/lesson JSON -> items; pure, validated
              lesson_logic.dart  # respond(state, choice) -> new state (correct? gentle retry, advance); pure
              progression.dart   # pick next item from an injected Random + light spaced-repetition; pure
lib/widgets/  lesson_screen.dart # big targets; audio prompt; warm feedback; parental gate for exit/settings
```

- **No-fail logic** — `respond` never produces a "lose"; a wrong choice re-prompts encouragingly and
  keeps the item in the queue. Model this explicitly (no `lost` phase).
- **Prompts are data** (text + audio + image refs) in JSON; a pure loader validates them.
- **Spaced repetition, lightly** — `progression` favors not-yet-mastered items via an injected seeded
  `Random`; deterministic for tests.

## Genre specifics — kids-safety & a11y are the product

- **Parental gate** on anything outside play — settings, exit-to-store, links, purchases (math/hold
  challenge an adult passes). Required by both stores.
- **No tracking / analytics / ads / AdvertisingId / external links / accounts** — offline-first, no
  personal data. Minimal permissions (no Android `INTERNET` if offline).
- **Accessibility-first** — audio prompts + `Semantics`; never rely on reading or color; huge tap
  targets; honor Reduce Motion and text scaling.
- **Warm, pressure-free** — no countdowns, no scores that punish, no dark patterns or urgency.

## Genre checklist

- [ ] Strictly no-fail; wrong answers re-prompt gently (no loss/score/timer); modelled in pure Dart.
- [ ] Parental gate on settings/exit/links/purchases; no external links in the child flow.
- [ ] No tracking/ads/analytics/AdvertisingId/accounts; offline; minimal permissions.
- [ ] Audio + `Semantics` prompts; playable without reading or color; targets ≥ 64dp for toddlers.
- [ ] Concepts/prompts are validated JSON; logic + progression unit-tested; no `package:flutter` in core.
- [ ] Passes `scripts/dart-doctor.py --only kids-safety,accessibility` clean.

## See also
- [`references/accessibility-child-safety.md`](../references/accessibility-child-safety.md) — **binding** kids rules (read first).
- [`assets/privacy-checklist.md`](../assets/privacy-checklist.md) · [`checklists/accessibility.md`](../checklists/accessibility.md).
- [`workflows/create-new-game.md`](../workflows/create-new-game.md) · [`templates/quiz.md`](quiz.md).
