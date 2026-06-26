# Workflow: Add state management

**Goal:** Wire a thin reactive layer between your pure-Dart game model and the Flutter UI — choosing the lightest tool that scopes rebuilds, never letting state-management own game truth.

## When to use
- You have (or are about to build) a pure-Dart model and need Flutter widgets to render it and feed input back.
- HUD/score/lives/board need to update on screen without rebuilding the whole tree every frame.
- You are deciding between `ValueNotifier`/`ChangeNotifier` and a package (Provider/Riverpod/Bloc) and want the package-policy-correct call.
- A Flame `GameWidget` game needs a few reactive HUD overlays driven by model state.

**Not for:** the per-frame Flame render loop (that runs in `Component.update(dt)` / `render`, not a `setState` path — see `references/flutter-flame-patterns`); or persistence (see the save workflow). State management here means *UI observing model changes*, nothing more.

## Prerequisites
- A pure-Dart model exists or is stubbed: a class holding state + rules, **no `package:flutter` import**, unit-tested with `dart test`. See `references/flutter-game-architecture`.
- You know your three modes (Flutter-widgets / Flame / hybrid `GameWidget`) — `references/flutter-game-architecture`.
- `flutter analyze` is clean and `dart format` (2-space) is enforced — `references/quality-policy`.

---

## Doctrine (read first)
1. **The model holds truth.** State management is a *thin* adapter that (a) exposes the model to widgets and (b) forwards intents back into it. Rules, the state machine (`menu → playing → paused → win/lose → menu`), scoring, and `dt` clamping live in pure Dart — never in a `ChangeNotifier`, a `Notifier`, or a `Bloc`. The reactive layer must be deletable/swappable without touching a single rule.
2. **Default to the framework, not a package.** `ValueNotifier` / `ChangeNotifier` + `ListenableBuilder` ship with Flutter, need zero deps, and cover almost every simple 2D game. Reach for a package only when you hit a real, named limit (see Step 1). This is the `references/package-policy` rule: minimal deps, justify every addition.
3. **Scope every rebuild.** Never wrap a whole screen in one builder that rebuilds on any change ("rebuild-the-world"). Use `ListenableBuilder` / `ValueListenableBuilder` (framework) or `Selector` / `select` (packages) so each widget rebuilds only when *its* slice changes. Pass the static subtree as the builder's `child` so it is built once.
4. **Own the lifecycle.** Every `ChangeNotifier`/`ValueNotifier`/`Notifier` you create must be `dispose()`d. Leaked listeners are the #1 state bug. (`ChangeNotifier.dispose` discards resources; per Flutter docs removing a listener is O(N), so don't churn them.)

---

## STEP 1 — Choose the tool (decision table)

Start at the top. Drop down a row **only** when you can name the limit you're hitting.

| Pick | When (the *named* trigger) | Cost |
|---|---|---|
| **`ValueNotifier<T>`** | One or a few independent scalar/value slices (`score`, `lives`, `timeLeft`, current `GameState`). Model is immutable value types. | 0 deps. Lightest. |
| **`ChangeNotifier`** (your controller) | One controller coordinates several fields + intents (`tapTile`, `startLevel`, `pause`) and you want one object to listen to. | 0 deps. |
| **`Provider` + `ChangeNotifierProvider`** | The controller must be reachable from many widgets *deep* in the tree and threading it through constructors is getting ugly; you want `ChangeNotifierProvider` to auto-`dispose` it and `Selector` for scoped rebuilds. | +1 dep (`provider`). |
| **`Riverpod`** | Compile-safe DI, multiple interacting providers, auto-dispose of per-level/per-screen state, testable overrides, or `family` for parameterized levels. Outgrows `InheritedWidget`-style lookup. | +1 dep (`flutter_riverpod`). |
| **`Bloc`/`Cubit`** | The team standard is explicit event→state streams, or you need an auditable event log / time-travel. Heaviest; rarely needed for simple 2D games. | +1 dep (`flutter_bloc`). |

**Default for a new simple game:** `ChangeNotifier` controller wrapping the pure model, with `ValueNotifier`s (or model-derived getters) for hot HUD fields. Do not add a package unless a row below "ChangeNotifier" is justified in your handoff under `references/package-policy`.

> Any package choice MUST be recorded in the handoff with the specific trigger from this table. "It's familiar" is not a trigger.

**Done when:** you've named your tool and the one-line reason. If the reason is a package, you've cited the package-policy justification.

---

## STEP 2 — (Framework path) Build the thin adapter

This is the recommended path for the vast majority of simple 2D games. No package.

### 2a. Pure model (no Flutter import — already exists)
```dart
// lib/game/snake_model.dart  — pure Dart, dart test covers this
enum GameStatus { menu, playing, paused, won, lost }

class SnakeModel {
  SnakeModel(this._rng);
  final Random _rng;            // injected seeded Random — deterministic tests
  GameStatus status = GameStatus.menu;
  int score = 0;

  void start() { status = GameStatus.playing; score = 0; }
  void pause() { if (status == GameStatus.playing) status = GameStatus.paused; }

  /// Advance one tick. dt is clamped by the CALLER's loop, not here-by-magic.
  void tick(double dt) {
    if (status != GameStatus.playing) return;
    // ... rules: move, eat, collide, set status = won/lost, bump score ...
  }
}
```

### 2b. Controller = thin `ChangeNotifier` over the model
The controller adds **zero rules**. It owns the model, exposes read-only views, forwards intents, and calls `notifyListeners()` after a mutation. It clamps `dt` (UI/timing concern) before delegating.
```dart
// lib/game/game_controller.dart
import 'package:flutter/foundation.dart';
import 'snake_model.dart';

class GameController extends ChangeNotifier {
  GameController(this._model);
  final SnakeModel _model;

  GameStatus get status => _model.status;          // read-only views
  int get score => _model.score;

  void start()  { _model.start();  notifyListeners(); }   // forward intent
  void pause()  { _model.pause();  notifyListeners(); }

  /// Called from the loop (Ticker/GameWidget). Clamp dt here — a UI concern.
  void onFrame(double rawDt) {
    if (_model.status != GameStatus.playing) return;
    final dt = rawDt.clamp(0.0, 1 / 30);   // survive stalls; model stays pure
    _model.tick(dt);
    notifyListeners();
  }

  // If you OWN this notifier in a State, dispose it there (Step 4).
}
```
> Decision: per-frame games call `notifyListeners()` each tick — that's fine **because** the builders below are scoped. A whole-screen builder here would be the rebuild-the-world anti-pattern.

### 2c. Scoped rebuilds in the widget tree
Own the controller in a `State` and rebuild only the slices that change.
```dart
class GameScreen extends StatefulWidget {
  const GameScreen({super.key});
  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  late final GameController _c = GameController(SnakeModel(Random(42)));

  @override
  void dispose() { _c.dispose(); super.dispose(); }   // STEP 4 — mandatory

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Rebuilds ONLY when the controller notifies. The big static board
        // passed as `child` is built once and reused across rebuilds.
        ListenableBuilder(
          listenable: _c,
          child: const _StaticBoardChrome(),        // not rebuilt
          builder: (context, child) => Row(
            children: [Text('Score ${_c.score}'), child!],
          ),
        ),
        // The board itself reads the controller wherever it needs a slice.
        Expanded(child: BoardView(controller: _c)),
      ],
    );
  }
}
```

### 2d. Single-value slices → `ValueListenableBuilder`
When a field is a lone value, expose a `ValueNotifier` and use the value-reporting builder (it hands you the new value, no `.value` read):
```dart
final ValueNotifier<int> lives = ValueNotifier(3);
// ...
ValueListenableBuilder<int>(
  valueListenable: lives,
  builder: (context, value, _) => HeartsRow(count: value),  // rebuilds on lives only
);
```
> `AnimatedBuilder` is the same widget specialized for `Animation` objects — reach for it only when an `Animation`/`AnimationController` is the listenable.

**Done when:** HUD/score update on screen; the static board is not rebuilt each tick (verify with `debugPrint` in a builder or `flutter run --profile` + DevTools "Track Widget Rebuilds"); no rule code lives in the controller.

---

## STEP 3 — (Package path) Only if Step 1 named a trigger

Keep the **same pure model + thin controller**. The package only changes *how widgets reach it and scope rebuilds*. Add the dep, run `dart pub get`, justify it in the handoff.

### Provider (deep-tree access + scoped rebuild)
```dart
// pubspec.yaml: provider: ^6.1.5
ChangeNotifierProvider(
  create: (_) => GameController(SnakeModel(Random(42))),  // auto-disposed by provider
  child: const GameScreen(),
);

// Scoped rebuild — Selector rebuilds only when score changes:
Selector<GameController, int>(
  selector: (_, c) => c.score,
  builder: (_, score, child) => Row(children: [Text('Score $score'), child!]),
  child: const _StaticBoardChrome(),     // built once
);
// Read without listening (e.g. in a callback): context.read<GameController>().start();
// Listen to a slice inline: context.select<GameController,int>((c) => c.score);
```
> `ChangeNotifierProvider` calls `dispose` for you, so you do **not** dispose it yourself (don't double-dispose).

### Riverpod (compile-safe DI, auto-dispose, parameterized levels)
```dart
// pubspec.yaml: flutter_riverpod: ^3.3.2 — wrap app in ProviderScope(child: MyApp())
// Notifier holds the thin controller logic; model stays pure underneath.
class GameNotifier extends Notifier<GameState> {
  @override
  GameState build() => GameState.initial();         // initial state
  void start() => state = state.started();
}
final gameProvider = NotifierProvider<GameNotifier, GameState>(GameNotifier.new);

class ScoreText extends ConsumerWidget {
  const ScoreText({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Scoped: rebuild only when score slice changes.
    final score = ref.watch(gameProvider.select((s) => s.score));
    return Text('Score $score');
  }
}
```
> Riverpod auto-disposes providers when no longer watched (use `autoDispose` / per-screen scope) — good for per-level state. `@riverpod` codegen exists; only adopt it if you also add `build_runner` (extra dep — justify). Overrides in `ProviderScope` make widget tests trivial.

### Bloc/Cubit (explicit event→state; rarely needed)
```dart
// pubspec.yaml: flutter_bloc: ^9
class GameCubit extends Cubit<GameState> {
  GameCubit(this._model) : super(GameState.menu());
  final SnakeModel _model;                 // pure model still owns rules
  void start() { _model.start(); emit(GameState.from(_model)); }
}
// Scoped rebuild:
BlocSelector<GameCubit, GameState, int>(
  selector: (s) => s.score,
  builder: (_, score) => Text('Score $score'),
);
```

**Done when:** the package is added with a justified trigger, rebuilds are scoped via `Selector`/`select`/`BlocSelector`, and the pure model/tests are unchanged.

---

## STEP 4 — Lifecycle & disposal (do not skip)
- **You created it → you dispose it.** Any `ChangeNotifier`/`ValueNotifier`/`AnimationController`/`Cubit` you instantiate in a `State` is disposed in `State.dispose()`.
- **The framework created it → don't.** `ChangeNotifierProvider` and Riverpod `autoDispose` handle disposal — disposing yourself = double-dispose crash.
- **Pause on lifecycle change.** Pause the game on background, resume on foreground, via `AppLifecycleListener` (or `WidgetsBindingObserver`); route it through a controller intent, not by mutating the model directly.
- Never call `notifyListeners()`/`emit`/`state =` after dispose. Guard frame callbacks if a tick can outlive the screen.

**Done when:** opening/closing the screen repeatedly shows no leaked-listener warnings and `flutter analyze` is clean.

---

## STEP 5 — Test the seam
Test the **pure model** with `dart test` (fast, no Flutter). Test the **thin reactive layer** with `flutter_test`:
```dart
test('controller forwards start and notifies', () {
  final c = GameController(SnakeModel(Random(1)));
  var notes = 0; c.addListener(() => notes++);
  c.start();
  expect(c.status, GameStatus.playing);
  expect(notes, 1);
  c.dispose();
});

testWidgets('score text rebuilds only on score change', (tester) async {
  // pump a widget reading the score slice; bump score; expect one rebuild.
});
```
- Riverpod: override providers in `ProviderScope(overrides: [...])` for deterministic widget tests.
- Bloc: `bloc_test` for `expect` sequences.
- See `references/testing-and-release` for the full ladder.

**Done when:** model logic tests pass under `dart test`; one reactive test proves intent→notify→scoped-rebuild; analyzer clean; `dart format` applied.

---

## Common pitfalls
- **Rebuild-the-world:** one `ListenableBuilder`/`Consumer` around the whole screen. Fix: scope per slice; pass the static subtree as `child`.
- **Rules leaking into the controller/Notifier/Bloc.** If you can't delete the state-management layer and keep all rules, the model isn't pure. Move logic back into pure Dart.
- **`flutter` imported into the model.** The model must compile under `dart test` with no Flutter. Grep for `package:flutter` in `lib/game/`.
- **Forgotten `dispose()`** → leaked listeners, "setState after dispose", growing memory. (Removing listeners is O(N); don't add/remove per frame.)
- **Double-dispose:** disposing a notifier that `ChangeNotifierProvider`/Riverpod already owns.
- **Adding a package with no named trigger** — violates `references/package-policy`. Start with `ValueNotifier`/`ChangeNotifier`.
- **`dt` clamped inside the model.** Clamp in the controller/loop (UI/timing concern); keep the model a pure function of `dt`.
- **Mutable state shared by reference** so widgets see changes without a notify (stale or out-of-order UI). Notify explicitly after every mutation, or expose immutable snapshots.

## Cross-links
- `references/flutter-game-architecture` — model/UI/loop separation, the three modes, folder layout.
- `references/flutter-flame-patterns` — driving HUD overlays from a Flame `GameWidget`; the render loop is **not** this seam.
- `references/package-policy` — when a dependency is justified (record the trigger).
- `references/quality-policy` — analyzer-clean, `const`, `dispose`, null-safe, 2-space format.
- `references/ui-and-animations` — `ListenableBuilder` vs `AnimatedBuilder`, Reduce Motion gating.
- `references/testing-and-release` — `dart test` vs `flutter_test`, provider/bloc test helpers.
- `assets/flutter_game_widget_template.dart`, `assets/seeded_random.dart` — scaffolds to copy.
