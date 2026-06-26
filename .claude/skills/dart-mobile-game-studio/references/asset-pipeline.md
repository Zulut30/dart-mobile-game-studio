# Asset pipeline

How to produce, declare, bundle, and load art / audio / level data for a Flutter +
Flame mobile game (iOS + Android) without copyrighted material, and how to keep it crisp
and lean across phones and tablets.

## Golden rule

**No copyrighted assets.** Never add third-party characters, logos, brand fonts, sprite
rips, ripped sprite atlases, or licensed music/SFX. Use only:

1. **Generated placeholder vector art** drawn in code (`CustomPainter` + `Canvas`, or
   `flutter_svg` for hand-authored SVGs you own).
2. **Assets the user explicitly provides and owns** (confirm ownership before bundling;
   place under `assets/`).

Keep the bundle lean and offline-first — a kids-safe app must never fetch art, audio, or
levels from the network at runtime.

## Where assets live and how they are declared

Flame's recommended project layout (matches the engine's default cache prefixes):

```text
assets/
├─ images/        # PNG sprites, atlases — Flame.images / game.images default prefix
│  ├─ player.png
│  └─ tiles.png
├─ audio/         # SFX + music — FlameAudio default prefix (assets/audio/)
│  ├─ tap.mp3
│  └─ music.mp3
├─ levels/        # level_001.json ... (data, not code)
└─ svg/           # owned vector art for flutter_svg / Flutter-widget mode
```

Declare directories in `pubspec.yaml` under `flutter:` (exactly 2-space indent; directory
entries **must** end with `/`):

```yaml
flutter:
  assets:
    - assets/images/
    - assets/audio/
    - assets/levels/
    - assets/svg/
```

Notes:
- Flame's `Images` cache prefixes paths with `assets/images/` and `FlameAudio` with
  `assets/audio/`, so you pass **bare filenames** to their loaders (e.g. `images.load('player.png')`,
  `FlameAudio.play('tap.mp3')`) — not the full path.
- `rootBundle` / `DefaultAssetBundle` (used for JSON levels in widget mode) want the **full**
  path (`assets/levels/level_001.json`).
- Name assets semantically (`tile_grass.png`, `btn_jump.png`), never by appearance.

## Mode 1 — Flutter-widgets-only: placeholder vector art in code

For static / turn-based games (coloring, memory, sliding puzzle, drag-and-drop), draw
bright, high-contrast primitives so the game is playable before any real art exists.

`CustomPainter` (no asset files, scales perfectly at any density):

```dart
class TokenPainter extends CustomPainter {
  const TokenPainter({required this.color});
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color..isAntiAlias = true;
    canvas.drawCircle(size.center(Offset.zero), size.shortestSide / 2, paint);
  }

  @override
  bool shouldRepaint(TokenPainter old) => old.color != color;
}

// Usage: const SizedBox.square(dimension: 64, child: CustomPaint(painter: TokenPainter(color: Colors.orange)));
```

Owned SVG via `flutter_svg` (justify the dep; pure-Dart, no native code):

```dart
import 'package:flutter_svg/flutter_svg.dart';

SvgPicture.asset(
  'assets/svg/star.svg',
  width: 48,
  height: 48,
  colorFilter: const ColorFilter.mode(Colors.amber, BlendMode.srcIn),
  semanticsLabel: 'Star', // accessibility label
);
```

Build a small "art kit": a palette of 6–8 friendly colors and a set of primitive shapes,
so every screen can be assembled without external files. Material `Icons` are also fine.

## Mode 2 — Flame: images, sprites, and atlases

Load and cache in `onLoad`, retrieve synchronously during the loop with `fromCache`.

```dart
import 'package:flame/components.dart';
import 'package:flame/game.dart';
import 'package:flame/sprite.dart';

class MyGame extends FlameGame {
  @override
  Future<void> onLoad() async {
    await images.loadAll(['player.png', 'tiles.png']); // game-scoped cache, freed on dispose
    final player = SpriteComponent.fromImage(
      images.fromCache('player.png'),
      size: Vector2.all(64),
    );
    add(player);
  }
}
```

- `game.images` is a per-game `Images` cache that frees automatically when the
  `GameWidget` is removed; `Flame.images` is a global singleton (use for assets shared
  across screens, clear manually with `Flame.images.clearCache()`).
- `SpriteComponent.fromImage(...)` / `await game.loadSprite('player.png')` build a single
  sprite; pass `srcPosition` + `srcSize` to slice one region out of an atlas.

**Sprite sheets / texture atlases** — pack many frames into one PNG to cut draw setup and
load count:

```dart
final sheet = SpriteSheet(image: images.fromCache('tiles.png'), srcSize: Vector2.all(16));
final grass = sheet.getSprite(0, 0); // row, column

// Frame animation from a horizontal strip:
final data = SpriteAnimationData.sequenced(
  textureSize: Vector2.all(64),
  amount: 2,
  stepTime: 0.1,
);
final anim = SpriteAnimationComponent.fromFrameData(images.fromCache('player.png'), data);
```

Atlas guidance: keep sheet dimensions power-of-two-friendly where practical, group sprites
that render together, and prefer one atlas per scene over many tiny PNGs.

## Audio (with a mute toggle)

Use `flame_audio` (wraps `audioplayers`). Default directory is `assets/audio/`; pass bare
filenames. Use short royalty-free or user-owned clips only; generate simple tones if none
are provided.

```dart
import 'package:flame_audio/flame_audio.dart';

await FlameAudio.audioCache.loadAll(['tap.mp3', 'music.mp3']); // preload to avoid first-play lag

FlameAudio.play('tap.mp3');                 // one-shot SFX
FlameAudio.bgm.play('music.mp3', volume: .25); // looping music, pause/resume with the game
FlameAudio.bgm.stop();

// Rapid-fire SFX: a pool avoids allocating a player per shot.
final pool = await FlameAudio.createPool('tap.mp3', minPlayers: 1, maxPlayers: 3);
await pool.start();
```

**Mute is non-negotiable.** Gate playback behind a setting (a pure-Dart `Settings` model
exposed via `ValueNotifier`/`ChangeNotifier`), default conservative, and persist it:

```dart
void playTap() {
  if (settings.soundEnabled) FlameAudio.play('tap.mp3');
}
// On mute: FlameAudio.bgm.stop(); on app pause: FlameAudio.bgm.pause();
```

Never autoplay loud audio. Keep files small (`.mp3`/`.ogg`/`.m4a`); music must loop
seamlessly. Stop/pause BGM on lifecycle changes so it does not play in the background.

## Level / game data — JSON, not code

Keep levels as **data** so non-engineers can tweak them and tests can load fixtures.
Decode in the **pure-Dart core** (no `package:flutter` imports) so `dart test` validates it
on the VM with no device.

```dart
class LevelData {
  const LevelData({required this.schemaVersion, required this.id, required this.tiles});
  final int schemaVersion;
  final String id;
  final List<int> tiles;

  factory LevelData.fromJson(Map<String, dynamic> json) {
    final version = json['schemaVersion'] as int? ?? 1; // tolerate missing keys
    return LevelData(
      schemaVersion: version,
      id: json['id'] as String,
      tiles: (json['tiles'] as List).cast<int>(),
    );
  }
}
```

Loading the bytes is the renderer's job, kept out of the core:

```dart
// Flutter widget mode:
import 'package:flutter/services.dart' show rootBundle;
final raw = await rootBundle.loadString('assets/levels/level_001.json');

// Flame:
final raw = await game.assets.readJson('levels/level_001.json'); // AssetsCache, prefix assets/
final level = LevelData.fromJson(jsonDecode(raw) as Map<String, dynamic>);
```

Include a `schemaVersion`, fail gracefully on missing/extra keys, and store test fixtures
under `test/fixtures/`. Use a seeded `Random` (`assets/seeded_random.dart`) for any
procedural placement so levels are deterministic and unit-testable.

## Sizing & density across phones and tablets

- **Design in logical pixels** against a reference canvas; in Flame fix the visible world
  with a camera viewport (`FixedResolutionViewport(resolution: Vector2(360, 640))` or
  `FixedAspectRatioViewport`) and let it letterbox/scale — do not hardcode device sizes.
- In Flutter-widget mode, size from `LayoutBuilder` / `MediaQuery` constraints and
  `MediaQuery.devicePixelRatio`; lay out with `Flexible`/`AspectRatio`, not magic numbers.
- **Resolution-aware raster assets:** ship variants in `2.0x/` and `3.0x/` subfolders next
  to the 1.0x file; Flutter's `AssetImage` auto-picks by `devicePixelRatio`. Declare only
  the base path — variants bundle automatically. (Flame loads exactly the file you name, so
  for sprites either provide a single high-res atlas or branch on `devicePixelRatio`.)

  ```text
  assets/images/btn_jump.png
  assets/images/2.0x/btn_jump.png
  assets/images/3.0x/btn_jump.png
  ```

- Prefer **vector** (`CustomPainter` / `flutter_svg`) for UI chrome to dodge per-density
  exports entirely; reserve PNG atlases for detailed sprites.
- Test on the smallest phone and a large tablet; honor safe-area insets (`SafeArea`,
  notches, rounded corners) and both orientations if supported.

## What NOT to do

- Don't fetch art/audio/levels over the network at runtime (offline-first, kids-safe).
- Don't bundle analytics/ads SDKs, tracking pixels, or anything reading IDFA/GAID inside
  an "asset" package.
- Don't ship huge unused textures or uncompressed audio; keep `flutter build --analyze-size`
  honest.
- Don't load images/audio on the hot path — preload in `onLoad`, retrieve from cache.
- Don't embed level rules in Dart code; keep them in JSON the core decodes.

## Accessibility hooks

- Give meaningful art a `semanticsLabel` (`SvgPicture.asset(..., semanticsLabel: ...)`) or
  wrap widgets in `Semantics(label: ..., button: true, ...)`.
- Respect `MediaQuery.disableAnimations` (Reduce Motion) — swap animated sprites for static
  frames when set.
- The mute toggle and a captions/visual-cue fallback make audio non-essential, as kids-safe
  review requires.
