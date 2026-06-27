# Template: Endless Runner (Flame)

A **design brief + architecture skeleton** for a lite endless runner (auto-run, tap-to-jump/dodge).
Fill the brackets, implement against the [`endless-runner-lite` recipe](../references/game-templates.md)
and [`references/flutter-flame-patterns.md`](../references/flutter-flame-patterns.md).

**Mode:** Flame (`FlameGame` + `GameWidget`), hybrid shell. Continuous scroll + spawn ⇒ Flame.

---

## Mini-GDD (filled example — adapt)

- **One-liner:** `<auto-run; tap to jump obstacles; go as far as you can>`.
- **Audience & age:** ages 6+, general/kids; sessions 30–90s.
- **Core loop:** auto-run → obstacle approaches → tap to jump/dodge → score by distance → repeat → crash → restart.
- **Primary verb:** tap (jump) — one button; maybe hold for higher jump.
- **Failure model:** single-life score-chase (crash = run ends), instant restart. Kids: generous hit-boxes + a slow start.
- **Win / progression:** distance/score, gentle speed ramp, high-score; no "win", just a personal best.
- **Art:** placeholder runner + obstacles; parallax background optional.
- **Scope (in):** auto-run, one obstacle type, jump, collision→end, score, restart.
- **Cut-line (later):** obstacle variety, pickups, speed tiers, themes, parallax.

## Architecture skeleton

```
lib/models/   run_config.dart   # immutable: baseSpeed, rampPerSec, gravity, jumpVelocity
              run_state.dart     # phase, distance, speed, alive; pure ramp/score logic
lib/systems/  spawner.dart       # next obstacle gap/type from an injected Random + difficulty; pure
              scoring.dart        # distance/score from elapsed * speed; pure
lib/game/     runner_game.dart    # FlameGame: World + Camera; scroll; spawn; HasCollisionDetection
              obstacle_pool.dart  # ComponentPool — recycle obstacles, no per-spawn allocation
              player_component.dart, hud_overlay (Flutter: score, pause, game-over)
```

- **Clamp `dt`** (Flame doesn't) before advancing scroll/physics — a hitch must not skip the player into an obstacle.
- **Object pooling is mandatory** — obstacles spawn/despawn constantly; recycle via `ComponentPool`
  (no `new`/GC churn each second). Off-screen → `removeFromParent()` returns it to the pool.
- **No allocation in `update`/`render`** — hoist `Vector2`/`Paint`/`Rect` to fields; mutate in place.
- **Spawn from an injected seeded `Random`** — deterministic runs are testable and tunable.
- **World/Camera** for scroll; HUD is a Flutter overlay.

## Genre specifics (what matters here)

- **Bounded component count** — pool + despawn off-screen so a long run can't accumulate thousands of nodes.
- **Fair difficulty ramp** — gaps must always be clearable at the current speed (test the spawner's min-gap vs jump arc).
- **Generous, readable hit-boxes** for kids; a brief invulnerable start.
- **Reduce Motion** — cut parallax/shake; the run itself stays playable.

## Genre checklist

- [ ] `dt` clamped; scroll/physics frame-rate independent.
- [ ] Obstacles pooled (`ComponentPool`); off-screen recycled; component count bounded.
- [ ] Zero allocation in `update`/`render`; `Vector2`/`Paint`/`Rect` are reused fields.
- [ ] Spawn/ramp from an injected seeded `Random`; gaps always clearable (unit-tested); core has no `package:flutter`.
- [ ] HUD/game-over as Flutter overlays; `pauseEngine()` on pause; Reduce Motion honored.

## See also
- [`references/flutter-flame-patterns.md`](../references/flutter-flame-patterns.md) · [`references/game-templates.md`](../references/game-templates.md) (`endless-runner-lite`).
- [`references/performance-checklist.md`](../references/performance-checklist.md) · [`workflows/run-performance-audit.md`](../workflows/run-performance-audit.md) · [`checklists/flame-quality.md`](../checklists/flame-quality.md).
