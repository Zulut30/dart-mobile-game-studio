# Flutter widgets mastery (Dart 3 / Flutter)

The renderer toolkit for game UI: menus, HUD, settings, and Flutter-widgets-only games
(`CustomPainter` + gestures). Targets **Dart 3 / Flutter**, analyzer-clean. Everything here is the
**thin renderer** over the pure-Dart core — widgets read an immutable model and emit intents back; no
game rules live in a `build` method. Format with `dart format` (2-space indent, trailing commas for
vertical layout); keep zero analyzer issues under `very_good_analysis`.

The golden rule of this layer: **the widget tree is a function of state, never the owner of it.** The
core (`lib/models/`, `lib/systems/`) decides what happens; the widget decides only how it looks.

## Stateless vs Stateful — and why most game widgets are stateless

- **`StatelessWidget`** — no mutable state; `build(BuildContext)` is a pure function of `final`
  fields. Use it for everything you can: a tile, a card face, a score label, a menu button. If a
  widget's appearance is fully determined by its constructor args plus a listenable you watch, it is
  stateless.
- **`StatefulWidget`** + `State<T>` — only when the widget *owns* a resource with a lifecycle: an
  `AnimationController`, a `FocusNode`, a `TextEditingController`, a `ValueNotifier` it created, a
  `StreamSubscription`, a `Ticker`. The trigger is "I have something to `dispose`", not "I have data
  that changes". Changing **data** belongs in the model and arrives via a listenable.

```dart
// DO — gameplay state lives in the model/notifier, the board is stateless and just renders it.
class BoardView extends StatelessWidget {
  const BoardView({required this.board, required this.onTap, super.key});
  final Board board;                       // immutable snapshot from the core
  final void Function(int index) onTap;    // intent back to the core

  @override
  Widget build(BuildContext context) => GridView.count(/* ... renders board ... */);
}

// DON'T — a StatefulWidget hoarding game rules in its State.
class BoardView extends StatefulWidget { /* ... */ }
class _BoardViewState extends State<BoardView> {
  List<Tile> tiles = [];                   // game state stranded in the UI layer, untestable
  void tap(int i) => setState(() { /* move logic here */ }); // rules in a build path
}
```

> Heuristic: reach for `StatefulWidget` only to hold a *disposable*. Reach for the model + a listenable
> for everything that is *data*.

## Composition over inheritance — build by nesting, never by subclassing widgets

Flutter has no "extend `Container` and override it" idiom. You compose: wrap small widgets in bigger
ones, and factor repetition into **your own** small widgets or helper methods, not into framework
subclasses. Never subclass `Container`, `Text`, `Padding`, etc.

- **Do** extract a reusable piece into a tiny `const`-constructible `StatelessWidget`.
- **Do** keep `build` shallow by naming sub-trees as separate widget classes (each gets its own
  rebuild boundary — see below).
- **Don't** subclass concrete framework widgets; don't build a 200-line `build` with five levels of
  nesting you scroll to read.

```dart
// DO — a small, named, const widget you compose anywhere.
class PillButton extends StatelessWidget {
  const PillButton({required this.label, required this.onPressed, super.key});
  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => FilledButton(
        onPressed: onPressed,
        child: Text(label),
      );
}
```

> Prefer a separate widget **class** over a `Widget _buildFoo()` helper method: a class creates a real
> rebuild boundary and can be `const`, so it skips rebuilding when its parent rebuilds. A helper method
> always re-runs with the parent.

## `const` widgets — the cheapest performance win in the framework

A `const` widget is canonicalized at compile time: when its parent rebuilds, Flutter sees the *same*
instance, skips its `build`, and reuses the element. For a game that rebuilds a HUD every frame, this
is the difference between repainting one label and repainting the whole tree.

- **Do** mark every widget you can `const` — leaf `Text`, `Icon`, `SizedBox`, `Padding`, spacers, and
  any of your own widgets whose args are all compile-time constants.
- **Do** keep constructors `const` (all fields `final`) so callers *can* `const` them.
- **Don't** rebuild static chrome (background, frame, title) inside an animation or per-frame
  listener — hoist it to a `const child` passed *into* the rebuilding builder (see `AnimatedBuilder`).

```dart
// DON'T                                   // DO
Padding(                                    const Padding(
  padding: EdgeInsets.all(8),                 padding: EdgeInsets.all(8),
  child: Text('Score'),                       child: Text('Score'),
)                                           )   // analyzer: prefer_const_constructors
```

## Keys & identity — when the framework must not recycle the wrong element

Flutter matches old and new widgets by *position and runtime type*; a `Key` overrides that match when
position alone is ambiguous. You mostly don't need keys — but in games you have two classic cases:

- **Reordering/shuffling a list of stateful or animating children** (shuffled cards, sortable tiles).
  Without a key, Flutter keeps the element at slot 0 and just swaps its data, so animations and
  `State` follow the *slot*, not the *card*. Give each item a `ValueKey(card.id)` so identity follows
  the card.
- **Forcing a rebuild from scratch** (restart a level, reset a board) — change a parent `key` to throw
  away the old subtree and its `State`.

```dart
// DO — stable identity per card so AnimatedSwitcher/reorder animates the right one.
for (final card in shuffledCards)
  CardView(key: ValueKey(card.id), card: card),

// Use GlobalKey only when you must reach a State/RenderObject across the tree (rare in games);
// it is heavier — prefer Value/ObjectKey for list identity.
```

> Pick the key from a **stable domain id** (`card.id`), never the list index — the index is exactly the
> thing that changes on a shuffle.

## Driving UI from the model — `ValueNotifier` / `ValueListenableBuilder` / `ChangeNotifier`

This is the heart of the renderer. The core exposes observable state; the widget subscribes to the
*smallest slice* it needs and rebuilds only that. Three tools, smallest-to-largest:

- **`ValueNotifier<T>`** — one observable value. Set `.value` to notify; it skips notifying if the new
  value `==` the old, so value-typed models (which you already made `==`-comparable) deduplicate
  rebuilds for free. Watch it with **`ValueListenableBuilder<T>`**, whose `builder` reruns *only* when
  that one value changes — nothing else in the screen rebuilds.
- **`ChangeNotifier`** — a richer model with several fields and methods; call `notifyListeners()` after
  a mutation. Watch with `ListenableBuilder` (or `AnimatedBuilder`), or with `provider`'s
  `Consumer`/`Selector`. `Selector` lets you rebuild only when a *derived* slice changes.
- **State management packages** — `provider` (thin `InheritedWidget` sugar over `ChangeNotifier`) or
  `Riverpod` (compile-safe, testable providers) scale this up for a multi-screen game. For a small
  game, a couple of `ValueNotifier`s passed down, or one `ChangeNotifier` at the top, is plenty —
  don't add a package you can't justify.

Crucially: keep the listenable in the **systems** layer if it imports no Flutter, or in a thin Flutter
adapter that wraps the pure-Dart core. The notifier is the seam; the rules stay testable.

```dart
// DO — one value, one builder, one rebuild boundary. The Scaffold/title never rebuild.
final scoreNotifier = ValueNotifier<int>(0);   // owned by the game controller, disposed by it

ValueListenableBuilder<int>(
  valueListenable: scoreNotifier,
  builder: (context, score, child) => Text('Score: $score'),
);

// DON'T — setState on the whole screen for one field → rebuilds the entire subtree every point.
setState(() => _score++);                       // whole-screen rebuild for a one-int change
```

```dart
// ChangeNotifier as a thin Flutter adapter over the pure-Dart core.
class GameController extends ChangeNotifier {
  GameController(this._engine);            // _engine is pure Dart, no Flutter import
  GameModel _engine;
  GameModel get model => _engine;

  void tap(int index) {
    _engine = _engine.applyTap(index);     // pure reducer returns a new immutable model
    notifyListeners();                     // renderer reacts; rules stayed in _engine
  }
}
```

> `Selector<GameController, int>(selector: (_, c) => c.model.score, builder: ...)` rebuilds only when
> the *score* changes, even though the whole model object was replaced — the antidote to
> over-notifying.

## Animation — `AnimatedBuilder`, implicit & explicit, gated on Reduce Motion

**Reduce Motion is mandatory, not optional.** Read it once via
`MediaQuery.of(context).disableAnimations` (iOS "Reduce Motion" / Android "Remove animations") and
collapse durations to `Duration.zero` so the same code path simply snaps. Never ship motion the user
asked the OS to stop. Also respect `MediaQuery.of(context).textScaler` for any animated text.

```dart
final reduceMotion = MediaQuery.of(context).disableAnimations;
final d = reduceMotion ? Duration.zero : const Duration(milliseconds: 250);
```

**Implicit animations** — for one-shot UI polish where you only have a start and end value. Just swap a
property and the `Animated*` widget tweens it: `AnimatedContainer`, `AnimatedOpacity`,
`AnimatedAlign`, `AnimatedPositioned`, `AnimatedScale`, `TweenAnimationBuilder`. Drive the duration
from `reduceMotion`. No controller to dispose.

```dart
// DO — implicit, Reduce-Motion-aware; collapses to an instant snap when motion is off.
AnimatedScale(
  scale: pressed ? 0.92 : 1,
  duration: reduceMotion ? Duration.zero : const Duration(milliseconds: 120),
  child: const CardFront(),
);
```

**Explicit animations** — for looping, reversible, or continuously driven motion (a pulsing hint, a
shake-on-wrong, a coin spin). You own an **`AnimationController`** in a `State` (with
`SingleTickerProviderStateMixin` for the `vsync`), shape it with a **`Tween`** + `CurvedAnimation`, and
**must `dispose`** it. Wrap only the moving subtree in **`AnimatedBuilder`** and pass the static part
as its `const child` so it is built once, not every frame.

```dart
class HintPulse extends StatefulWidget {
  const HintPulse({required this.child, super.key});
  final Widget child;
  @override
  State<HintPulse> createState() => _HintPulseState();
}

class _HintPulseState extends State<HintPulse> with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late final Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _scale = Tween(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _c, curve: Curves.easeInOut),
    );
    if (!WidgetsBinding.instance.platformDispatcher.accessibilityFeatures
        .disableAnimations) {
      _c.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _c.dispose();                          // a leaked controller leaks a Ticker — frame after frame
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _scale,
        // The child is built ONCE and reused every frame — only the Transform rebuilds.
        child: widget.child,
        builder: (context, child) => Transform.scale(scale: _scale.value, child: child),
      );
}
```

> Read `disableAnimations` from `WidgetsBinding.instance.platformDispatcher.accessibilityFeatures` in
> `initState` (no `context` MediaQuery yet), or from `MediaQuery.of(context)` in
> `build`/`didChangeDependencies`. Either way, **gate before you animate.**

## `CustomPainter` — vector art and the Flutter-widgets-only game surface

For a static/turn-based game you don't need Flame; a `CustomPaint` + `CustomPainter` draws the whole
board with the same 2D `Canvas` API Flame uses. Implement two methods: `paint(Canvas, Size)` draws,
and **`shouldRepaint(old)`** decides whether to repaint — return `true` only when inputs actually
changed, so you don't repaint a static board 60 times a second.

- **Do** make the painter take an *immutable* model in its constructor and compare it in
  `shouldRepaint` (`old.board != board`) — your value-equality pays off again.
- **Do** scale all geometry off the passed `Size` (and `MediaQuery.devicePixelRatio` if you cache),
  never hard-coded pixels — that is your phone/tablet responsiveness for the canvas.
- **Do** repaint efficiently by passing a `Listenable` to `CustomPaint(painter:)` via the
  `repaint:`-style pattern (a painter constructed with `super(repaint: notifier)`) so it repaints on
  notify without rebuilding the widget.
- **Don't** allocate `Paint`/`Path` objects per `paint` call in a hot loop if you can hoist constants;
  don't put game logic in `paint` — it only reads the model and draws.

```dart
class BoardPainter extends CustomPainter {
  const BoardPainter(this.board);
  final Board board;                       // immutable snapshot

  @override
  void paint(Canvas canvas, Size size) {
    final cell = size.width / board.cols;  // geometry derived from Size → responsive
    final fill = Paint()..color = const Color(0xFF3366CC);
    for (final tile in board.filledTiles) {
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(tile.col * cell, tile.row * cell, cell, cell),
          const Radius.circular(6),
        ),
        fill,
      );
    }
  }

  @override
  bool shouldRepaint(BoardPainter old) => old.board != board; // value equality → repaint only on change
}

// Used as: CustomPaint(painter: BoardPainter(board), size: Size.square(side))
```

## Gestures → model intents — the input boundary

A `GestureDetector` (or `Listener` for raw pointers) is the *only* place input enters. It must do one
thing: translate a touch into a **named intent** and hand it to the controller. No rules, no `setState`
of game data, no branching on game state inside the callback.

- **Do** convert pixel coordinates to a board coordinate at the boundary, then call a single
  `controller.method(...)`. Use `onTapUp`/`onTapDown` with `details.localPosition` (already local to
  the widget), and `onPanUpdate`/`onPanEnd` for drags.
- **Do** wrap tap targets to at least 48×48 logical px (`SizedBox`/`ConstrainedBox`) for kids' fingers
  and a11y.
- **Don't** mutate model state in the callback; don't read `globalPosition` when you mean local; don't
  stack overlapping detectors that fight over the same gesture.

```dart
// DO — pixel → board coord → one intent. The controller (pure core behind it) decides legality.
GestureDetector(
  onTapUp: (details) {
    final cell = (details.localPosition.dx / cellSize).floor();
    controller.selectColumn(cell);         // a named intent; rules live in the core
  },
  child: const BoardView(),
);

// DON'T — logic in the gesture callback.
onTapUp: (d) => setState(() {
  if (board[i].isEmpty && turn == Player.red) board[i] = Player.red; // rules stranded in UI
}),
```

## Layout for phones + tablets — `MediaQuery`, `LayoutBuilder`, `SafeArea`

Games run on a 5-inch phone and a 13-inch tablet; lay out from *constraints*, not constants.

- **`SafeArea`** — wrap the game surface so the board/HUD avoid notches, status bars, the home
  indicator, and rounded corners. Non-negotiable on modern phones.
- **`LayoutBuilder`** — gives you the parent's `BoxConstraints`; size the board off
  `min(maxWidth, maxHeight)` to keep it square and switch HUD placement (side panel on wide tablets,
  top bar on tall phones) off an aspect-ratio threshold.
- **`MediaQuery`** — `size`, `orientation`, `padding`/`viewInsets` (keyboard), `devicePixelRatio`,
  `textScaler`, `disableAnimations`. Use `MediaQuery.sizeOf(context)` /
  `MediaQuery.orientationOf(context)` (the targeted `*Of` accessors) to subscribe to *only* that field
  and avoid rebuilding on unrelated MediaQuery changes.
- **`OrientationBuilder`** for portrait/landscape layout swaps; `AspectRatio`/`FittedBox` to keep the
  play area proportional.

```dart
// DO — square, centered, safe-area'd, responsive to the actual box; subscribes to one field.
SafeArea(
  child: LayoutBuilder(
    builder: (context, constraints) {
      final side = math.min(constraints.maxWidth, constraints.maxHeight);
      final wide = constraints.maxWidth / constraints.maxHeight > 1.3; // tablet/landscape
      final board = SizedBox.square(dimension: side, child: const BoardView());
      return wide
          ? Row(children: [const SidePanelHud(), Expanded(child: Center(child: board))])
          : Column(children: [const TopBarHud(), Expanded(child: Center(child: board))]);
    },
  ),
);

// DON'T — fixed pixels; overflows a small phone, leaves a tablet mostly empty, ignores the notch.
SizedBox(width: 400, height: 600, child: BoardView());
```

> Read `textScaler` (not the deprecated `textScaleFactor`) and let text grow; never lock a font size
> that clips at large Dynamic Type. Use `MediaQuery.textScalerOf(context)` if you must clamp a label.

## Semantics — a label on every control, no silent buttons

Touch-only buttons drawn with `CustomPaint`/`GestureDetector` are invisible to TalkBack/VoiceOver
unless you describe them. Wrap interactive surfaces in **`Semantics`** with at least a `label`, and a
`value` for stateful controls; mark `button: true`, `enabled:`, and use `hint:` for non-obvious
actions.

- **Do** give every control a `label`; give toggles/sliders a `value`; announce dynamic changes with
  `liveRegion: true` (e.g. "You win").
- **Do** collapse a composite control (icon + text) with `MergeSemantics`, and hide purely decorative
  art with `ExcludeSemantics` so the reader isn't spammed.
- **Do** trust built-in widgets (`IconButton`, `FilledButton`, `Slider`) — they ship correct
  semantics; you only annotate your *custom* surfaces.
- **Don't** leave a painted/gesture-only button unlabeled; don't expose 64 decorative tiles as 64
  unlabeled nodes.

```dart
// DO — a painted, gesture-driven button made screen-reader-usable.
Semantics(
  label: 'Pour blue paint',
  button: true,
  enabled: canPour,
  child: GestureDetector(onTap: canPour ? onPour : null, child: const PaintWell()),
);

// Announce a state change once, audibly:
Semantics(liveRegion: true, label: won ? 'You win!' : '', child: const SizedBox.shrink());

// Hide decoration from the reader:
ExcludeSemantics(child: const StarfieldBackground());
```

## Lifecycle & `dispose` — every resource you `init`, you `dispose`

A `State` that creates a resource must release it in **`dispose()`** (called once when the element is
permanently removed), or it leaks for the life of the app. The `initState → didChangeDependencies →
build → … → dispose` lifecycle is yours to honor.

**Must-dispose checklist:** `AnimationController`, `Ticker`/`TickerProvider`, `ValueNotifier` /
`ChangeNotifier` *you created* (and remove any `addListener` you added), `StreamSubscription`,
`FocusNode`, `TextEditingController`, `ScrollController`, `OverlayEntry`, `Timer`.

- **Do** create disposables in `initState` (or `didChangeDependencies` if they need `context`/
  inherited data), and tear them down in reverse in `dispose`.
- **Do** guard async callbacks that touch state with `if (!mounted) return;` — a `Future` can complete
  after the widget is gone.
- **Don't** call `setState` after `dispose`; don't `dispose` a notifier you were *given* (the owner
  disposes it); don't forget `removeListener` for a listener you added to a shared notifier.

```dart
@override
void initState() {
  super.initState();
  _controller = AnimationController(vsync: this, duration: const Duration(seconds: 1));
  _scoreSub = scoreStream.listen(_onScore);
  _focus = FocusNode();
}

@override
void dispose() {
  _focus.dispose();
  _scoreSub.cancel();
  _controller.dispose();                   // release in reverse; nothing survives the widget
  super.dispose();
}

void _onScore(int s) {
  if (!mounted) return;                    // the stream may outlive the widget
  setState(() => _score = s);
}
```

## Hybrid: Flutter chrome over a Flame surface (`GameWidget` overlays)

When an action game (Flame) still needs real Flutter menus/HUD, embed the game with `GameWidget` and
layer Flutter widgets via **`overlayBuilderMap`** + `initialActiveOverlays`. The game toggles overlays
with `game.overlays.add('PauseMenu')` / `.remove(...)`; the overlay builders are ordinary Flutter
widgets — so every pattern above (stateless composition, `ValueListenableBuilder` HUD, `Semantics`,
Reduce Motion) applies to them unchanged.

```dart
// DO — Flutter menus as overlays; the menu is a normal const-friendly StatelessWidget.
GameWidget<MyGame>.controlled(
  gameFactory: MyGame.new,
  overlayBuilderMap: {
    'PauseMenu': (context, game) => PauseMenu(onResume: () => game.overlays.remove('PauseMenu')),
  },
  initialActiveOverlays: const ['PauseMenu'],
);
```

> Keep score/lives in a `ValueNotifier` the Flame game owns and the Flutter HUD overlay watches with
> `ValueListenableBuilder` — one notifier, two readers (the in-game `TextComponent` HUD and the Flutter
> overlay), one source of truth. Details of the Flame side live in `../flutter-flame-patterns.md`.

## The widget-layer bar in miniature

1. **Stateless by default;** `StatefulWidget` only to own a disposable.
2. **Compose, never subclass** framework widgets; extract small `const` widgets, not 200-line `build`s.
3. **`const` everything you can** — it is free rebuild-skipping.
4. **Model owns state; widgets read it** through `ValueListenableBuilder` / `Selector` at the smallest
   rebuild boundary. No whole-screen `setState` for one field.
5. **Gestures emit intents** to the controller; zero rules in callbacks.
6. **Gate motion on `disableAnimations`;** collapse durations to zero, never override the user's OS
   choice.
7. **`shouldRepaint` returns `true` only on real change** (lean on value equality).
8. **Layout from constraints** (`LayoutBuilder`/`MediaQuery`/`SafeArea`), never fixed pixels; respect
   `textScaler`.
9. **`Semantics` on every custom control;** merge composites, exclude decoration.
10. **Dispose every resource;** guard async with `mounted`. No Flutter imports leak into the core.
