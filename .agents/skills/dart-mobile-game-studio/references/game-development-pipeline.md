# Game development pipeline

End-to-end process for taking a fuzzy mobile-game idea to a tested MVP that ships to **both
iOS and Android** from one Flutter codebase. The SKILL.md workflow summarizes this; here is
the detail for each stage. Work the stages in order; skip one only with a stated reason.

## 1. Discovery — understand the request
Capture, in one short paragraph each:
- **Core fantasy / goal** — what the player is doing and why it feels good.
- **Genre & reference** — coloring, sliding/jigsaw puzzle, light platformer, drag-and-drop,
  memory/matching, lite runner, tap-reaction, educational mini-game.
- **Audience & age** — drives difficulty, text load, safety, and motion (default 4–8, no-fail).
- **Core verb** — tap, drag, swipe, tilt, move. One primary verb for a simple game.
- **Failure model** — no-fail (kids), score-chase, or win/lose with retries.
- **Session length** — seconds (tap-reaction) vs minutes (platformer level).
- **Platforms & orientation** — assume **iOS + Android**, phone-first; portrait, landscape, or
  both. Note tablet support if asked.

Ask only questions that change the architecture. Otherwise apply the SKILL.md fallbacks
(ages 4–8, no-fail, both orientations, widgets-only unless motion/physics is required) and
record the assumptions. Do not start coding to answer a question prose can answer.

## 2. Mini-GDD
Produce a one-page Game Design Document from `assets/gdd-template.md`. It is the contract for
the MVP. Keep it lean: concept, core loop, controls, progression/levels, art & audio
direction, accessibility notes, **scope cut-line**, and measurable success criteria. Everything
below the cut-line is "later." Get this signed off (explicitly or by stated assumption) before
writing code.

## 3. Mode selection
Pick exactly one of the three rendering modes (full decision rule in
`references/flutter-game-architecture.md`; render-side patterns in
`references/flutter-flame-patterns.md`):

- **Flutter-widgets-only** — no per-frame simulation. Static/turn-based boards, coloring,
  memory, matching, drag-and-drop, tap-reaction. Render with `CustomPainter`/`Canvas`, drive
  repaints from a `ValueNotifier`/`ChangeNotifier` via `AnimatedBuilder`/`ListenableBuilder`,
  take input with `GestureDetector`/`Draggable`. Simplest and most testable — prefer it.
- **Flame** — continuous motion, sprites, particles, collisions, physics. A `FlameGame` runs the
  loop, calling `update(double dt)` and `render(Canvas)` every tick; gameplay lives in
  `Component`/`PositionComponent` subclasses with `onLoad`. Add Forge2D only for real rigid-body
  physics.
- **Hybrid** — Flame gameplay inside a Flutter widget tree via `GameWidget`, with Flutter widgets
  for menus/HUD/settings. Default for action games that also need real UI. Flutter chrome layers
  over the canvas through the **overlays API** (see step 4).

When unsure between widgets-only and Flame, start widgets-only; escalating later is cheaper than
ripping out an engine you didn't need.

## 4. Architecture
- **Pure Dart core.** All rules, state, and the state machine live in plain Dart with **no
  `package:flutter` import**, so the core runs and is unit-tested on the Dart VM with `dart test`
  — no device, no widget pump. Flutter/Flame is a thin renderer over this core. This boundary is
  the single most important architectural decision; protect it.
- **State machine.** Model the flow explicitly, e.g. `menu → playing → paused → (win | lose) →
  menu`. Represent states as an `enum` or sealed class; transitions are pure methods on the model
  returning the next state. Test every transition.
- **Determinism.** Inject a seeded `Random` (the skill ships `assets/seeded_random.dart`) into any
  shuffle/spawn so tests are reproducible. Never call the global `Random()` inside game logic.
- **State management for the shell.** Keep it thin over the model. `ValueNotifier`/`ChangeNotifier`
  is enough for most simple games; Provider/Riverpod/Bloc are fine if the shell genuinely needs
  them — do not add one reflexively. The model holds truth; the notifier just republishes it to
  widgets.
- **Bridging to render:**
  - *Widgets-only:* the model is (or is wrapped by) a `Listenable`; rebuild with
    `ListenableBuilder`/`ValueListenableBuilder`.
  - *Flame:* the `FlameGame` owns a reference to the model; components read it through
    `HasGameReference<MyGame>` (the current mixin; older code/docs call it `HasGameRef`).
    `update(dt)` advances the model; `render` draws the result. Pause with `pauseEngine()` /
    `resumeEngine()` (or the `paused` flag) and surface menus via `overlays.add('PauseMenu')` /
    `overlays.remove(...)`, registered in `GameWidget(overlayBuilderMap: {...},
    initialActiveOverlays: const ['MainMenu'])`.
- **Systems.** List what you need and keep each in its own file: input, scoring, spawn, collision
  (`HasCollisionDetection` on the game + `CollisionCallbacks`/`onCollisionStart` on components),
  progression, audio, persistence.
- **Folder layout.** `lib/models/` (pure Dart core), `lib/systems/`, `lib/game/` (Flame), `lib/
  widgets/` (Flutter UI), `assets/` (art, audio, level JSON), `test/`. Small, single-purpose files.
  Levels are **data (JSON)**, not code — validate against `assets/level-schema-template.json`.

## 5. MVP implementation
- Build the smallest version that delivers the core loop **once, end to end** — one level, one win
  condition, one lose/no-fail path.
- Start from `assets/flame_game_template.dart` (Flame/hybrid) or
  `assets/flutter_game_widget_template.dart` (widgets-only); follow the per-genre recipe in
  `references/game-templates.md`.
- Write excellent, analyzer-clean Dart: `const` constructors, `dart format` (2-space indent), and
  the quality bar in `references/dart/README.md`. No premature systems (no shop, no online, no
  achievements) unless the GDD's core loop needs them.
- Use placeholder vector art only — `CustomPainter` shapes or `flutter_svg`/user-owned assets. **No
  copyrighted characters, logos, fonts, music, or sprites.** See `references/asset-pipeline.md`.

## 6. Tests (`dart test`)
- Unit-test the pure model with `dart test`: legal/illegal moves, scoring, win/lose detection,
  level load + validation, every state transition, and deterministic (seeded) shuffles/spawns.
- Widget behavior uses `flutter_test`; Flame components, when worth it, use
  `flame_test` — `testWithFlameGame`/`testWithGame<T>` give a ready game where you `await
  game.ready()` and advance time with `game.update(dt)`; `testGolden` for pixel goldens (avoid
  text in goldens). Keep most coverage in the device-free pure-core tests. Detail in
  `references/testing-and-release.md`.

## 7. Build & verify
- Discover the project and run gates with `scripts/verify-flutter-project.sh` (runs `dart analyze`
  + `dart test`, and `flutter test` if widgets exist).
- Provide explicit commands and report **real output**:
  - `dart format --output=none --set-exit-if-changed .`
  - `dart analyze` (or `flutter analyze`)
  - `dart test` (pure core) and `flutter test` (widgets)
  - Release builds: `flutter build appbundle` and `flutter build apk --split-per-abi` (Android),
    `flutter build ipa` (iOS, requires macOS + Xcode signing).
- **Report honestly.** Only claim a build or tests passed if you ran them and saw the output. If
  there is no toolchain/project here, say so and hand over the exact commands — never assert green.

## 8. Review (kids / privacy / a11y / perf)
Run `scripts/dart-doctor.py <project>`, then walk `assets/review-checklist.md` and
`assets/privacy-checklist.md`:
- **Child safety & privacy (both stores).** No tracking, third-party analytics, ads, or
  AdvertisingId (IDFA/GAID); no external links, accounts, or dark patterns; offline-first; no
  personal data; minimal permissions; parental gate for anything sensitive. Must satisfy **both**
  the Apple Kids Category **and** Google Play Families policy.
- **Accessibility.** Wrap interactive controls in `Semantics` (label/value/button); honor text
  scaling, Reduce Motion (`MediaQuery.disableAnimations`), and screen readers (VoiceOver/TalkBack).
  See `references/accessibility-child-safety.md`.
- **Performance.** Frame budget, `const` widgets, `RepaintBoundary`, Flame draw/update cost, no
  jank. See `references/performance-checklist.md`.

## 9. Handoff
Finish with a concise report:
- **Built:** the loop and features that work now.
- **Mode chosen & why** (widgets-only / Flame / hybrid).
- **Changed files:** list with a one-line purpose each (absolute paths).
- **Commands run + real output** (or exactly why none ran).
- **Assumptions, open risks, and next steps.** Provide a checklist and a risk list — **no
  store-approval or compliance guarantees**, ever.

## Scope discipline
The GDD cut-line is the contract. Anything past it is "later," and you say so rather than
silently building it. A polished tiny game beats a broken big one — doubly so for kids' apps,
where reliability and a clean privacy posture are the whole product.
