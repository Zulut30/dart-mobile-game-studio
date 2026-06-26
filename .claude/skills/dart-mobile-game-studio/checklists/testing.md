# Testing checklist

A tick-list a reviewer/agent runs over a Flutter/Dart mobile game's test suite before calling it
tested. It enforces [`references/testing-and-release.md`](../references/testing-and-release.md) and
[`references/testing-e2e-patrol.md`](../references/testing-e2e-patrol.md); it does **not** re-explain
them — read those for the APIs and the *why*. Check each box or note why it doesn't apply.

**The pyramid:** dozens of pure-Dart unit tests, a handful of widget/Flame tests, 1–2 goldens, and a
small set of device E2E flows. Prove gameplay **correctness in pure Dart**; use the slow device layers
only to prove the wiring and native touchpoints. Two gates run before any test claim:

```bash
dart format --output=none --set-exit-if-changed .   # no diff (2-space)
dart analyze                                          # zero issues
```

## Gates first (run before any test claim)
- [ ] `dart format --output=none --set-exit-if-changed .` produces **no diff**.
- [ ] `dart analyze` (and `flutter analyze` for the renderer) reports **zero issues** — not just errors.
- [ ] Test files live in `test/` (unit/widget/Flame/golden) and `integration_test/` (device E2E), each
      ending `_test.dart`.
- [ ] Lower gates are green **before** any device run — no burning a device build on unformatted /
      unanalyzed / unit-failing code.

## Unit — pure model with `dart test` (VM, headless)
- [ ] The model under test has **no `package:flutter` import and no `package:flame` import** — grep the
      file and its imports; it runs under `dart test`, not `flutter test`.
- [ ] **Legal/illegal moves:** a legal move mutates state as specified; an illegal move (out-of-bounds
      tap, move on a locked/matched cell) is rejected and leaves state unchanged.
- [ ] **Scoring** is asserted on a known sequence — exact score after N scripted moves, not just "score
      went up".
- [ ] **Win condition** fires exactly when the rules say (e.g. all matched / target reached) and **not**
      one move early or late.
- [ ] **Lose condition** fires on its trigger (out of moves/lives/time) and not before; if the game has
      no lose state, that is asserted/noted explicitly.
- [ ] **Level loading/decoding** round-trips: a valid level JSON decodes to the expected model; a
      malformed/oversized level is rejected with a typed error, not a crash or silent default.
- [ ] **Systems** (spawn logic, collision verdicts, difficulty ramp) are covered where kept pure; a
      save→load round-trip reproduces identical model state.

## Determinism (seeded RNG)
- [ ] Game logic takes an **injected** seeded `Random` ([`assets/seeded_random.dart`](../assets/seeded_random.dart)) —
      grep confirms **no bare `Random()` and no `DateTime.now()`** in `lib/models/` or `lib/systems/`.
- [ ] **Same seed ⇒ same sequence:** two runs with the same seed produce identical shuffles/spawns
      (assert the full sequence equal, not just the first element).
- [ ] **Different seed ⇒ different sequence** (guards against a stubbed/constant RNG silently passing).
- [ ] Determinism tests stay inside the **VM-tested core** (64-bit `int`); no reliance on web/JS `int`
      semantics for reproducibility.

## State machine transitions
- [ ] Every legal edge of `menu → playing → paused → win/lose → menu` has a test asserting the resulting
      state.
- [ ] **Illegal transitions are rejected** (e.g. cannot pause from `menu`, cannot move while `paused`);
      input in a non-`playing` state is a no-op, not a crash.
- [ ] The machine is exhaustive — adding a state would fail to compile (sealed type + `switch` with no
      `default`); a transition test exists per state.
- [ ] **Pause halts model time** (no `dt` advance while paused) and **resume continues** from the same
      state — asserted in pure Dart, not just visually.

## Edge cases & boundaries
- [ ] Boundary inputs covered: empty board, single element, full/max board, first and last index,
      zero/one move remaining.
- [ ] Repeated/double input (double-tap the same cell, resume-while-not-paused, win-then-tap) is handled
      idempotently.
- [ ] `dt` clamp behavior is tested where logic is time-stepped (a huge `dt` does **not** teleport /
      skip win/lose); fixed-timestep logic is deterministic across render rates.
- [ ] Each **fixed regression bug** has its own test (preferably a unit test) so it can't silently
      return — see Regression below.

## Widget tests — `flutter_test` (`testWidgets`)
- [ ] A tap/drag on a control **routes to the right model call** and the reflected model change appears
      (e.g. score/lives update) — the renderer wiring, not the rules.
- [ ] HUD/menu reflect **model state**: `find.text`/`find.byIcon`/`find.byTooltip` assert score, paused
      vs. playing icon, win/lose screen presence.
- [ ] Accessibility labels are asserted with `find.bySemanticsLabel` on at least the key interactive
      controls.
- [ ] Animated/transition steps use `pump(Duration)` or `pumpAndSettle()` correctly — **`pumpAndSettle`
      is not used on a live game loop** (it times out on perpetual animation); explicit `pump` steps there.

## Flame component tests — `flame_test`
- [ ] (Mode 2/3 only.) Components are tested against a real loop via `testWithFlameGame` /
      `testWithGame<MyGame>` with `ensureAdd` + `ready()`; time advanced by `game.update(dt)` (seconds),
      not wall-clock.
- [ ] A component reacts as specified to an `update` (gravity/movement) and to a collision verdict,
      using `flame_test` vector matchers (`closeToVector`) for position assertions.
- [ ] Hybrid mode: a `GameWidget` mounts in the tree (`pumpWidget` + `pump`) and the game reaches
      `isLoaded`.

## Golden tests (visual regression)
- [ ] Goldens cover **stable, text-free** visuals only (board/sprite layout) — no rasterized text, no
      live/animating scene (those flake across machines).
- [ ] Reference PNGs are **committed**; `flutter test --update-goldens` was run intentionally and the
      diffs reviewed before commit, not blindly regenerated.
- [ ] Goldens are kept few (1–2) and pinned/deterministic (fixed size, shadows disabled or font pinned)
      so they don't flake in CI.

## Integration tests — `integration_test` (device/emulator)
- [ ] `IntegrationTestWidgetsFlutterBinding.ensureInitialized()` is called; tests live in top-level
      `integration_test/` and drive the **real app** (`app.main()`).
- [ ] A full in-Flutter flow is covered: launch → `Play` → drive the core loop → reach the **win**
      screen (and a lose path if one exists), using **seeded** input so the run is reproducible.
- [ ] A target device/emulator/simulator is confirmed (`flutter devices`) before the run — there is no
      headless path for this layer.

## Patrol E2E — native flows (device/emulator)
- [ ] (Only if native touchpoints exist.) `patrol` is a **`dev`-only** dependency, the `patrol:` block
      sets the real `package_name`/`bundle_id`, and tests run via **`patrol test`** (not
      `flutter test`, which skips the native automator).
- [ ] **Lifecycle:** background (`pressHome` / recents) then foreground → state preserved and **no `dt`
      spike on resume** — the part `integration_test` cannot do.
- [ ] **Permissions:** any legitimately-requested native dialog is tested on **both** granted and denied
      branches (`grantPermissionWhenInUse()` / `denyPermission()`), and the app behaves gracefully when
      denied.
- [ ] **Notifications:** a scheduled notification is opened (`openNotifications`) and tapped, deep-linking
      back to the right screen (if the game sends any).
- [ ] **Per-platform** flows tagged and run on **both** iOS simulator and Android emulator (Android back
      button, iOS swipe-back, dark mode, safe-area/notch).
- [ ] Seed is injected via `--dart-define` so E2E can't depend on device entropy or wall-clock.

## Kids-safety negative suites (privacy-first builds)
- [ ] **No native permission prompt** ever appears across the full loop —
      `expect(await $.platform.mobile.isPermissionDialogVisible(), isFalse)`.
- [ ] **No purchase surface:** no IAP UI, no price strings, no store sheet reachable (monetization
      disallowed in kids builds).
- [ ] **No ads:** no ad SDK init, no ad surface, no rewarded entry point.
- [ ] **No accounts / sign-in UI** exists at all; no external link exits without a verified parental gate.
- [ ] Static backstop: Advertising-ID permission **absent** from the merged `AndroidManifest.xml`; no
      IDFA/ATT call on iOS.

## Smoke (the fast PR gate)
- [ ] A minimal `smoke`-tagged set proves "boots and plays one round": launch → `Play` → first
      interaction registers → a slice toward win, plus the kids-safety negative assertion.
- [ ] Smoke is the **per-PR** gate (`patrol test --tags smoke` / the VM layers); if smoke is red, the
      pipeline stops.

## Regression
- [ ] Every previously-fixed bug has a dedicated test (unit where possible, else E2E) tagged
      `regression`, pinned to that bug so it can't silently recur.
- [ ] Regression + per-platform suites run **nightly/pre-release**, not on every PR (device E2E is slow
      and flaky).

## Coverage of outcomes
- [ ] **Win path** asserted (unit + at least one device/integration flow).
- [ ] **Lose path** asserted, or the absence of a lose state stated explicitly.
- [ ] **Edge/error path** asserted (malformed level, illegal input, boundary board) — not only the happy
      path.
- [ ] `dart test --coverage=coverage` (or `flutter test --coverage`) was generated and the model's
      win/lose/transition branches are actually exercised (not just imported).

## Honest pass reporting
- [ ] A claim of "tests pass" / "build succeeds" is made **only** after running it and seeing the
      output — VM layers (`dart test`/`flutter test`) and device layers (`integration_test`/`patrol`)
      reported separately.
- [ ] If there is no toolchain/device here, the handoff says **"not run in this environment"** and lists
      the exact commands plus the device requirement — no asserted pass that wasn't observed.
- [ ] The handoff quotes **real output**: `dart test`/`flutter test` pass/fail counts, the analyzer
      summary, and the native runner's pass/fail for any E2E run.
