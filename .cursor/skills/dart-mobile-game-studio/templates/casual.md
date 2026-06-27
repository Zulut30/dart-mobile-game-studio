# Template: Casual (tap / swipe, no-fail)

A **design brief + architecture skeleton** to start a casual game fast. Fill the brackets, then
implement against the recipe in [`references/game-templates.md`](../references/game-templates.md) and
the process in [`workflows/create-new-game.md`](../workflows/create-new-game.md). This is the design
starting point; it does not re-explain how to code the genre.

**Mode:** Flutter-widgets-only (default). Reach for Flame only if a continuous `update(dt)` loop is
genuinely needed (it usually isn't for casual). One line of *why* in the GDD.

---

## Mini-GDD (filled example — adapt)

- **One-liner:** `<tap falling fruit before it hits the ground>` — a one-verb toy you grasp in 3s.
- **Audience & age:** ages 4–10, general/kids; sessions 30–90s.
- **Core loop:** see a target → tap/swipe it → score + feedback → next target. Repeat; ramps gently.
- **Primary verb:** `<tap | swipe | hold>` — one verb, no combos.
- **Failure model:** **no-fail** *or* soft score-chase (a timer/limited misses, never a punishing
  Game Over). Default no-fail for the youngest.
- **Win / progression:** score milestones, a high-score, gentle speed ramp; no levels needed for v1.
- **Art:** bright high-contrast placeholder shapes (`CustomPainter`); juicy but Reduce-Motion-gated feedback.
- **Scope (in):** one verb, one screen, score + restart, one ramp parameter.
- **Cut-line (later):** themes, power-ups, daily challenge, leaderboards.

## Architecture skeleton (pure Dart, no Flutter import)

```
lib/models/   game_phase.dart   # enum GamePhase { menu, playing, paused, won }  (no 'lost' if no-fail)
              game_state.dart   # immutable: score, elapsed, targets, ramp; copyWith, ==/hashCode
              target.dart       # a tappable entity: id, position(Vec2), kind, spawnedAt
lib/systems/  spawner.dart      # next target(s) from an injected Random + ramp; pure
              scoring.dart       # tap → hit/miss → new score; pure
lib/widgets/  game_screen.dart  # owns state + a Ticker/Timer; renders targets; HUD; restart
```

- **State machine:** `menu → playing → paused → won/back-to-menu`. The model owns it; the widget renders.
- **Determinism:** spawn from an injected seeded `Random` ([`assets/seeded_random.dart`](../assets/seeded_random.dart)) so tests pin the sequence.
- **Time:** if you animate falling targets, drive them off a clamped `dt` even in widgets mode (a `Ticker` with `dt.clamp(0, 1/30)`), so a background hitch doesn't teleport them.

## Genre specifics (what matters here)

- **One verb, instant readability.** If a 4-year-old needs instructions, it's too complex.
- **Generous hit-boxes** (≥ 48dp, larger for kids) — casual taps are imprecise.
- **Juice, gated.** Pop/scale/particle feedback sells the tap — but collapse it to instant under
  `MediaQuery.disableAnimations` (Reduce Motion).
- **No dead ends.** Always a one-tap restart; never a hard Game Over for the youngest band.

## Genre checklist

- [ ] One core verb; playable with no text.
- [ ] No-fail (or a gentle, non-punishing score-chase) chosen and stated.
- [ ] Spawn/ramp driven by an injected seeded `Random`; unit-tested deterministic.
- [ ] Hit-boxes ≥ 48dp; `Semantics` on every interactive target.
- [ ] Feedback gated on Reduce Motion; no free-running loop on menu/pause.
- [ ] `dart test` covers scoring + spawn ramp; no `package:flutter` in `models/`/`systems/`.

## See also
- [`references/game-templates.md`](../references/game-templates.md) — `tap-reaction` recipe (closest implementation).
- [`workflows/create-new-game.md`](../workflows/create-new-game.md) · [`workflows/choose-game-architecture.md`](../workflows/choose-game-architecture.md).
- [`references/accessibility-child-safety.md`](../references/accessibility-child-safety.md) — kids defaults.
