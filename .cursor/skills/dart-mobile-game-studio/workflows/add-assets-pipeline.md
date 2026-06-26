# Workflow: Add the assets pipeline

**Goal:** Wire a Flutter game's assets (placeholder vector art, images/atlases, fonts, audio) into `pubspec.yaml` and load them correctly per mode — with zero copyrighted material.

## When to use
- Bootstrapping a new game and you need art/audio/fonts available at runtime.
- Switching a prototype from "all `CustomPainter`" to bundled image/atlas assets for Flame.
- Adding a font, a sound effect, or background music to an existing game.
- A build fails with `Unable to load asset` / `Unable to find a default font` — almost always a missing `pubspec.yaml` declaration or a path typo.

## Prerequisites
- A Flutter project (`flutter create` already run) with a `pubspec.yaml`.
- Decided the rendering **mode** (Flutter-widgets / Flame / hybrid `GameWidget`) — it changes *how* assets load, not *whether* they're declared. See `references/flutter-game-architecture.md`.
- Read `references/asset-pipeline.md` (source of this workflow) and `references/accessibility-child-safety.md` (audio defaults, no copyrighted assets).
- Flame games: `flame` in deps; audio: `flame_audio`; SVG: `flutter_svg`. Justify each per `references/package-policy.md`.

## Doctrine for this pipeline
- **No copyrighted assets — ever.** Ship placeholder vector art you author (`CustomPainter` / `flutter_svg`), Material/Cupertino icons, or user-owned files only. No ripped sprites, fonts, sound effects, or music. This is a kids-safety + legal gate, not a preference. See `checklists/asset-licensing.md`.
- **Prefer vectors for UI, rasters for Flame.** `CustomPainter`/SVG scale to any density with no `@2x/@3x` variants. Flame draws from `dart:ui` `Image`s, so gameplay sprites are PNGs (ideally one atlas).
- **Declare, then load.** Every runtime asset MUST be listed in `pubspec.yaml`. Undeclared paths throw at load time, not build time.
- **Audio off by default, gated, mixable.** Game starts muted-respecting (honor system mute / a settings flag); never autoplay loud music. See Step 6 and `references/accessibility-child-safety.md`.

---

## STEPS

### 1. Lay out the asset folders
Use one predictable tree at the project root. Flame, by convention, looks under `assets/images` and `assets/audio` (its default prefixes), so match that:

```
assets/
  images/        # PNG sprites + atlases for Flame (rasters)
  audio/         # short SFX + music (ogg/mp3/wav)
  data/          # level JSON, tuning tables (see add-level-data workflow)
  fonts/         # .ttf / .otf you are licensed to ship
lib/
  art/           # CustomPainter / SVG placeholder art (Dart, not a bundled asset)
```

Create them:
```bash
mkdir -p assets/images assets/audio assets/data assets/fonts lib/art
```
Keep folder and file names **lowercase_with_underscores**, no spaces — paths are case-sensitive on device.

### 2. Decide art strategy per surface
| Surface | Use | Why |
| --- | --- | --- |
| Menus, HUD, buttons, icons, simple shapes | `CustomPainter` or `flutter_svg` (`SvgPicture.asset`) | Resolution-independent, no density variants, tiny, easy to recolor for theming/contrast. |
| Flame gameplay sprites / animations | PNG image, ideally a **single atlas** | Flame renders `dart:ui` images; one atlas = one GPU texture = fewer draw calls. See `references/performance-checklist.md`. |
| Tilemaps | Tiled `.tmx` + tileset PNG (`flame_tiled`) | Only if the genre needs it; otherwise procedural. |

**Authoring placeholder art (no copyright risk):** draw it in code. A `CustomPainter` that draws the player as a rounded rect + circle eyes is a perfectly shippable placeholder. See `references/ui-and-animations.md` and `assets/flutter_game_widget_template.dart`.

### 3. Declare assets in `pubspec.yaml`
Under the existing `flutter:` key. **Indentation is two spaces and significant.**

```yaml
flutter:
  uses-material-design: true

  assets:
    # A trailing slash includes every file directly in the folder (non-recursive).
    - assets/images/
    - assets/audio/
    - assets/data/
    # Or list individual files when you want them explicit:
    # - assets/images/sprites.png
```
Notes:
- A directory entry (`assets/images/`) bundles files **in that folder only**, not subfolders — list each subfolder separately.
- SVGs loaded via `flutter_svg` are ordinary assets — declare them here too.
- Re-run `flutter pub get` after editing, and **full-restart** (not hot-reload) the app; the asset manifest is read at startup.

### 4. Resolution / density variants (raster UI images only)
Skip this entirely if your UI art is vectors (the recommended default). If you *do* ship raster UI images, Flutter resolves density from sibling subfolders — declare only the **base** path:

```
assets/images/icon_star.png        # 1x (base)
assets/images/2.0x/icon_star.png   # 2x
assets/images/3.0x/icon_star.png   # 3x
```
```yaml
    assets:
      - assets/images/icon_star.png   # declare the base; variants resolve automatically
```
Flutter picks the variant matching `MediaQuery.devicePixelRatio` for `Image.asset` / `AssetImage`. **Flame does not use this resolution-variant system** — it loads the exact path you give `images.load(...)`, so author Flame sprites at their target pixel size and don't rely on `2.0x/` folders for them.

### 5. Load images per mode

**5a. Flutter-widgets / SVG (menus, HUD):**
```dart
// Vector — preferred for UI.
import 'package:flutter_svg/flutter_svg.dart';
SvgPicture.asset('assets/images/logo.svg', width: 96);

// Raster with density variants.
Image.asset('assets/images/icon_star.png', width: 32);
```

**5b. Flame — preload in `onLoad`, then build sprites** (grounded in Flame docs):
```dart
class MyGame extends FlameGame {
  late final SpriteSheet sheet;

  @override
  Future<void> onLoad() async {
    // Preload once; cached for the game's lifetime.
    await images.loadAll(['player.png', 'enemy.png', 'sprites.png']);
    // (or images.loadAllImages() to load everything under assets/images/)

    final atlas = images.fromCache('sprites.png');
    sheet = SpriteSheet(image: atlas, srcSize: Vector2.all(16));
  }
}
```
- Inside a `FlameGame`, paths are **relative to `assets/images/`** — pass `'player.png'`, not `'assets/images/player.png'`.
- `Sprite.load('player.png')` and `SpriteAnimation.load(...)` work outside a game instance via the global `Flame.images` cache.
- **Atlas → animation** (Flame `SpriteSheet`):
  ```dart
  final run = sheet.createAnimation(row: 0, stepTime: 0.1, to: 6);
  ```
- For tool-built atlases, `flame` ships a TexturePacker loader (`fromAssetData` / packer integration) and `flame_texturepacker`; an Aseprite JSON loader exists too. Only add these packages if you actually export from those tools — justify per `references/package-policy.md`.

**5c. Hybrid `GameWidget`:** identical to 5b for game assets; load Flutter UI assets (5a) in the surrounding widget tree. See `assets/flame_game_template.dart`.

### 6. Audio (`flame_audio`)
Audio files go in `assets/audio/` (Flame's default audio prefix) and must be declared (Step 3). Preload to avoid first-play stutter (grounded in Flame docs):

```dart
@override
Future<void> onLoad() async {
  await FlameAudio.audioCache.loadAll(['tap.mp3', 'music.mp3']);
}

// Short SFX — gate on a user setting; never autoplay.
if (settings.soundOn) FlameAudio.play('tap.mp3');

// Background music tied to game pause/resume lifecycle.
if (settings.musicOn) FlameAudio.bgm.play('music.mp3');
```
- **Kids-safety:** music/SFX OFF unless the user opted in; expose a mute toggle in settings; pause `bgm` on app background (`FlameAudio.bgm.pause()`); keep volumes modest. See `references/accessibility-child-safety.md`.
- **Pure-Dart purity:** audio is a *system*, not game logic. Keep `play`/`bgm` calls in the Flame/widget layer; the pure-Dart core (no `package:flutter`) only emits intents like "play tap". See `references/flutter-game-architecture.md`.
- All audio must be your own or properly licensed — same no-copyright rule as art.

### 7. Fonts
Place licensed `.ttf`/`.otf` in `assets/fonts/` and declare a family:
```yaml
  fonts:
    - family: GameFont
      fonts:
        - asset: assets/fonts/GameFont-Regular.ttf
        - asset: assets/fonts/GameFont-Bold.ttf
          weight: 700
```
```dart
const TextStyle(fontFamily: 'GameFont');
```
- Default to system fonts (no asset, respects Dynamic Type / accessibility) unless a custom face is needed.
- Ship only fonts you're licensed for (e.g. SIL OFL). Record the license per `checklists/asset-licensing.md`.

### 8. Dispose / clear caches
Flame caches images and audio globally. When tearing a game down (e.g. returning to a menu that rebuilds the game), free them to avoid leaks:
```dart
@override
void onRemove() {
  Flame.images.clearCache();
  Flame.assets.clearCache();
  FlameAudio.audioCache.clearCache();
  super.onRemove();
}
```
Stop background music explicitly (`FlameAudio.bgm.stop()`) on quit. See `references/performance-checklist.md` and `references/production-quality.md` (dispose discipline).

### 9. Verify
```bash
flutter pub get
flutter analyze            # analyzer-clean (quality-policy)
dart format --output=none --set-exit-if-changed .   # 2-space formatting
flutter run                # full restart; confirm every asset renders / plays
```
For pure-Dart core tests, asset loading is **not** under test (it needs the Flutter binding) — keep the core decoupled so `dart test` runs without assets. See `references/testing-and-release.md`.

---

## Done when
- Every runtime asset is declared in `pubspec.yaml` and loads on a clean `flutter run` (no `Unable to load asset` errors).
- UI art is vector (`CustomPainter`/SVG) or has correct density variants; Flame sprites preload in `onLoad` and draw from cache.
- Audio is preloaded, gated behind a user setting, OFF by default, and pauses on background.
- Fonts (if any) render and are license-recorded.
- `flutter analyze` is clean and `dart format` reports no changes.
- `checklists/asset-licensing.md` is filled in: every asset is self-authored placeholder, a platform icon, or user-owned/properly-licensed — **no copyrighted material**.

## Common pitfalls
- **Forgot to declare → runtime crash.** `Unable to load asset` means the path isn't in `pubspec.yaml` (or has a typo / wrong case). Declare it and full-restart.
- **YAML indentation.** `assets:` and `fonts:` must sit under `flutter:` with two-space indent; tabs or wrong nesting silently drop entries.
- **Directory entry doesn't recurse.** `assets/images/` excludes subfolders — list each one.
- **Flame path confusion.** Inside a `FlameGame`, `images.load('player.png')` is relative to `assets/images/`; passing the full `assets/images/player.png` fails.
- **Loading in build/render hot paths.** Never call `images.load` / `FlameAudio.play` from `update`/`render`/`build`; preload in `onLoad` and reuse from cache. See `references/performance-checklist.md`.
- **Relying on `2.0x/` variants for Flame sprites.** Flame ignores Flutter's resolution-variant resolution — author sprites at target size.
- **Autoplaying loud audio / no mute.** Fails the kids-safety gate. Default OFF, provide a toggle, pause on background.
- **Copyrighted "placeholder" art.** A famous character is not a placeholder. Author your own shapes or use platform icons.
- **Hot-reload didn't pick up a new asset.** The asset manifest is read at startup — do a full restart after editing `pubspec.yaml`.

## Cross-links
- `references/asset-pipeline.md` (source) · `references/accessibility-child-safety.md` (audio/no-copyright) · `references/performance-checklist.md` (atlas, caching) · `references/flutter-flame-patterns.md` (Flame load patterns) · `references/package-policy.md` (justifying `flutter_svg`/`flame_audio`/atlas loaders) · `references/production-quality.md` (dispose) · `checklists/asset-licensing.md` · workflow `workflows/add-level-data.md` (JSON in `assets/data/`) · `assets/flame_game_template.dart`, `assets/flutter_game_widget_template.dart`.
