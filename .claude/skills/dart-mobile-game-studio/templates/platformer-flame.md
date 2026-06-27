# Template: Platformer (Flame)

A **design brief + architecture skeleton** for a light platformer. Fill the brackets, implement
against the [`simple-platformer` recipe](../references/game-templates.md) and the Flame patterns in
[`references/flutter-flame-patterns.md`](../references/flutter-flame-patterns.md). Wire the loop with
[`workflows/setup-flame-project.md`](../workflows/setup-flame-project.md) + [`add-game-loop.md`](../workflows/add-game-loop.md).

**Mode:** Flame (`FlameGame` + `GameWidget`), hybrid shell — Flame for the play surface, Flutter
overlays for menu/HUD/pause. Continuous `update(dt)` motion ⇒ Flame, not widgets.

---

## Mini-GDD (filled example — adapt)

- **One-liner:** `<run and jump across platforms to reach the goal>`.
- **Audience & age:** ages 6+, general/kids; sessions 1–3 min/level.
- **Core loop:** move → jump → avoid/clear hazards → reach the goal → next level.
- **Primary verb:** move (left/right) + jump; on-screen buttons or tap zones (no tiny controls for kids).
- **Failure model:** retry-friendly — a fall/hazard restarts the level (no lives sink for kids), or limited hearts for older.
- **Win / progression:** hand-authored levels (JSON), increasing length/gaps; collectibles optional.
- **Art:** placeholder rects/sprites; parallax optional; clear platform vs hazard contrast.
- **Scope (in):** one level, move/jump, gravity, platform collisions, goal, restart.
- **Cut-line (later):** enemies, collectibles, moving platforms, more levels, parallax.

## Architecture skeleton

```
lib/models/   level.dart        # pure: platforms, hazards, spawn, goal (parsed from JSON)
              physics_config.dart# gravity, moveSpeed, jumpVelocity (immutable tuning)
              run_state.dart     # phase, player pos/vel, collected, result; pure step logic where possible
lib/systems/  level_loader.dart # JSON -> Level; pure, validated
              physics.dart       # integrate(pos, vel, dt, config) + AABB platform resolve; pure-ish
lib/game/     platformer_game.dart # FlameGame: World + CameraComponent.withFixedResolution
              player_component.dart# PositionComponent; mirrors model; HasCollisionDetection hitbox
              hud_overlay (Flutter overlay: controls, pause, result)
```

- **Clamp `dt` yourself** — Flame does NOT. `final d = math.min(dt, 1/30);` before integrating, so a
  hitch/backgrounding can't tunnel the player through a platform.
- **World/Camera, not screen coords** — gameplay lives in a `World`; `CameraComponent.withFixedResolution`
  gives resolution independence; HUD is a Flutter overlay (never sized to the world).
- **Collisions via `CollisionCallbacks`** + simple `RectangleHitbox`; the *verdict* (landed? died?
  reached goal?) is decided in pure Dart, the component just forwards the event.
- **Levels are JSON data**, parsed by a pure loader — testable without a device.

## Genre specifics (what matters here)

- **Frame-rate independence** — all motion `* dt` (clamped); identical at 60 and 120 Hz.
- **Forgiving controls for kids** — coyote time, generous jump buffer, big tap zones.
- **No hot-path allocation** in `update`/`render` (no `new Vector2`/`Paint` per frame); pool/reuse.
- **Accessibility** at the Flutter layer — the bare canvas is invisible to screen readers; label
  overlay controls; honor Reduce Motion (e.g. reduce parallax/screen-shake).

## Genre checklist

- [ ] `dt` clamped before integration; movement frame-rate independent.
- [ ] Gameplay in a `World` + `CameraComponent`; HUD/controls as Flutter overlays.
- [ ] Collisions via `HasCollisionDetection` + hitboxes; outcome decided in pure Dart.
- [ ] Levels as validated JSON; physics/win logic unit-tested (`dart test`), no `package:flutter` in core.
- [ ] No allocation in `update`/`render`; pause stops the engine (`pauseEngine()`); Reduce Motion honored.

## See also
- [`references/flutter-flame-patterns.md`](../references/flutter-flame-patterns.md) · [`references/game-templates.md`](../references/game-templates.md) (`simple-platformer`).
- [`workflows/setup-flame-project.md`](../workflows/setup-flame-project.md) · [`add-game-loop.md`](../workflows/add-game-loop.md) · [`run-performance-audit.md`](../workflows/run-performance-audit.md).
- [`checklists/flame-quality.md`](../checklists/flame-quality.md).
