# Workflow: Add Audio (SFX + BGM)

**Goal:** Add preloaded sound effects, a looping background-music track, and a conservative,
persisted mute toggle that respects the device silent switch and the app lifecycle.

## When to use
- The game needs feedback sounds (tap, match, win/lose) and/or a music loop.
- Works for **Flame** games (use `flame_audio`) and **Flutter-widget / hybrid `GameWidget`**
  games (use `audioplayers` directly). `flame_audio` is a thin wrapper over `audioplayers`, so
  the configuration concepts below are identical.

## When NOT to use
- A silent game (puzzle/coloring with no sound need) — skip; do not add audio deps "just in case".
- You only need haptics — that is not audio; use `HapticFeedback` from `package:flutter/services`.

## Prerequisites
- Per `package-policy`: add exactly one of `flame_audio` (Flame) **or** `audioplayers` (widgets).
  Do not add both. `flame_audio` already brings `audioplayers` transitively.
- Short, royalty-free, **kid-appropriate** audio you own/licensed (see `asset-pipeline` and
  `accessibility-child-safety`): prefer `.mp3`/`.ogg`/`.wav`, mono, short, normalized, gentle.
- A pure-Dart settings model that can persist a `muted` flag (see `flutter-game-architecture`).
  Audio playback is a *side effect* — it lives in a thin service, never in the pure-Dart game core.

---

## STEPS

### 1. Add the dependency
```bash
# Flame games:
flutter pub add flame_audio
# OR widget/hybrid games (no Flame audio wrapper):
flutter pub add audioplayers
```
Justify the choice in your handoff per `package-policy`. Run `dart pub get` and `flutter analyze`.

### 2. Place assets and declare them
Flame expects audio under `assets/audio/` and references paths **relative to that folder**.
Plain `audioplayers` `AssetSource` references paths relative to `assets/`.

```
assets/
  audio/
    sfx/tap.mp3
    sfx/win.mp3
    bgm/loop.mp3
```
In `pubspec.yaml`:
```yaml
flutter:
  assets:
    - assets/audio/sfx/
    - assets/audio/bgm/
```
Keep file names lowercase, no spaces (see `asset-pipeline`). Run `flutter pub get` after editing.

### 3. Choose the audio session category (CRITICAL for kids — respect the silent switch)
By **default audioplayers uses a `playback` session**, which keeps playing even when the iOS
hardware mute switch is on. For a kids' game that is wrong. Set the iOS category to **`ambient`**:
it is *silenced by the Ring/Silent switch and by screen lock*, and *mixes* with other apps
(does not interrupt their audio). Set this **once at startup, before any playback**.

```dart
// audio_session.dart — call once from main() before runApp / before first play.
import 'package:audioplayers/audioplayers.dart';

Future<void> configureAudioSession() async {
  await AudioPlayer.global.setAudioContext(
    AudioContextConfig(
      // Mix with other audio instead of grabbing exclusive focus.
      focus: AudioContextConfigFocus.mixWithOthers,
      route: AudioContextConfigRoute.system,
    ).build(
      // Per-platform overrides take precedence over the generic config.
      ios: const AudioContextIOS(
        category: AVAudioSessionCategory.ambient, // obeys the silent switch
        options: {AVAudioSessionOptions.mixWithOthers},
      ),
      android: const AudioContextAndroid(
        isSpeakerphoneOn: false,
        stayAwake: false,
        contentType: AndroidContentType.sonification,
        usageType: AndroidUsageType.game,
        audioFocus: AndroidAudioFocus.gainTransientMayDuck,
      ),
    ),
  );
}
```
Notes:
- `AVAudioSessionCategory.ambient` is the only category that is *both* silenced by the mute
  switch *and* non-interrupting. Do **not** use `playback` for a casual kids' game.
- iOS cannot set the context per-player; `AudioPlayer.global.setAudioContext` (or any
  `player.setAudioContext`) applies the iOS context **globally**. Set it once.
- API note: older audioplayers used a single `respectSilence: true` flag on
  `AudioContextConfig`. On current versions prefer the explicit per-platform `AudioContextIOS`
  `category` shown above. Verify against your locked version with `dart pub deps`.

### 4. Build the audio service (the only place that touches the audio plugin)

#### 4a. Flame variant — `flame_audio`
```dart
import 'package:flame/game.dart';
import 'package:flame_audio/flame_audio.dart';

class GameAudio {
  GameAudio({this.muted = false}); // conservative default below (see step 5)

  bool muted;

  // Preload everything once so first playback has no disk-load hitch.
  Future<void> preload() async {
    await FlameAudio.audioCache.loadAll([
      'sfx/tap.mp3',
      'sfx/win.mp3',
      'bgm/loop.mp3',
    ]);
  }

  void playSfx(String name) {
    if (muted) return;
    FlameAudio.play(name, volume: 0.6); // short reused clip
  }

  void startBgm() {
    if (muted) return;
    // FlameAudio.bgm auto-pauses/resumes with app lifecycle (see step 6).
    FlameAudio.bgm.play('bgm/loop.mp3', volume: 0.35);
  }

  Future<void> stopBgm() => FlameAudio.bgm.stop();

  // Call from FlameGame.onRemove() / when leaving the game.
  Future<void> dispose() async {
    await FlameAudio.bgm.stop();
    FlameAudio.audioCache.clearAll();
  }
}
```
For rapid-fire identical SFX (e.g. a runner pickup) use an `AudioPool` instead of `FlameAudio.play`
to avoid allocating a player per shot:
```dart
late final AudioPool tapPool;
// in onLoad:
tapPool = await FlameAudio.createPool('sfx/tap.mp3', minPlayers: 2, maxPlayers: 4);
// to fire (returns a StopFunction):
final stop = await tapPool.start(volume: 0.6);
// in onRemove: await tapPool.dispose();
```

#### 4b. Widget / hybrid variant — `audioplayers`
Use **one reusable player per long-lived stream** (the BGM) and a small set of pooled players for
SFX. Creating a fresh `AudioPlayer()` per tap leaks native resources — reuse and `dispose()`.
```dart
import 'package:audioplayers/audioplayers.dart';

class GameAudio {
  GameAudio({this.muted = false});

  bool muted;

  final AudioPlayer _bgm = AudioPlayer()..setPlayerMode(PlayerMode.mediaPlayer);
  // Round-robin pool for low-latency, overlapping SFX.
  final List<AudioPlayer> _sfx = List.generate(
    4,
    (_) => AudioPlayer()..setPlayerMode(PlayerMode.lowLatency),
  );
  int _next = 0;

  final AudioCache _cache = AudioCache(prefix: 'assets/audio/');

  Future<void> preload() async {
    await _cache.loadAll(['sfx/tap.mp3', 'sfx/win.mp3', 'bgm/loop.mp3']);
    await _bgm.setReleaseMode(ReleaseMode.loop);
    await _bgm.setSource(AssetSource('audio/bgm/loop.mp3'));
    await _bgm.setVolume(0.35);
  }

  Future<void> playSfx(String assetPath) async {
    if (muted) return;
    final p = _sfx[_next];
    _next = (_next + 1) % _sfx.length;
    await p.stop(); // reset if still playing
    await p.setVolume(0.6);
    await p.play(AssetSource(assetPath)); // e.g. 'audio/sfx/tap.mp3'
  }

  Future<void> startBgm() async {
    if (muted) return;
    await _bgm.resume(); // source already set in preload()
  }

  Future<void> stopBgm() => _bgm.stop();

  Future<void> dispose() async {
    await _bgm.dispose();
    for (final p in _sfx) {
      await p.dispose();
    }
    _cache.clearAll();
  }
}
```

### 5. Mute toggle — conservative default, persisted
- **Default music OFF, SFX ON** is the conservative kid-friendly default (music auto-playing into a
  silent room is jarring; an unexpected loop can disturb). At minimum, never auto-start BGM without
  a visible control. If you ship a single `muted` flag, **default it so nothing loud surprises the
  child**, and surface a clearly labeled toggle on the first screen.
- Persist the flag in your settings model (e.g. `shared_preferences`) so the choice survives
  restarts; read it before `startBgm()`.
- Wire the toggle so flipping it immediately stops BGM (and gates SFX):
```dart
void setMuted(bool value, GameAudio audio) {
  audio.muted = value;
  if (value) {
    audio.stopBgm();
  } else {
    audio.startBgm();
  }
  settings.muted = value; // persist via your settings model
}
```
- Accessibility (`accessibility-child-safety`): give the toggle a `Semantics` label
  ("Sound", value "On"/"Off") and a touch target ≥ 48dp. Honor the system mute switch (step 3) so a
  child/parent flipping the hardware switch silences the game even if the in-app toggle is on.

### 6. Lifecycle — stop/pause on background, resume on foreground
Never let BGM keep playing while the app is backgrounded.
- **Flame:** `FlameAudio.bgm.play(...)` registers an `AppLifecycleListener` that auto-pauses on
  background and resumes on foreground — prefer it over a raw looping player for music. Still call
  `FlameAudio.bgm.stop()` in `onRemove`.
- **Widgets/audioplayers:** observe lifecycle yourself and pause/resume the BGM player:
```dart
class _GameState extends State<GameScreen> with WidgetsBindingObserver {
  late final GameAudio audio;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      audio.stopBgm();
    } else if (state == AppLifecycleState.resumed) {
      audio.startBgm(); // no-op if muted
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    audio.dispose(); // releases native players
    super.dispose();
  }
}
```

### 7. Keep the pure-Dart core clean
The game model **emits events** ("matched", "won") via callbacks/streams; the UI layer maps those to
`audio.playSfx(...)`. Do **not** `import 'package:flame_audio/...'` or `audioplayers` inside
`lib/.../*_game_logic.dart`. This keeps the core testable with `dart test` and the audio mockable
(see `testing-and-release`).

### 8. Verify
```bash
flutter analyze            # analyzer-clean, no audio import in pure-Dart core
dart format .              # 2-space
dart test                  # core logic unaffected by audio
flutter run                # manual: tap SFX fires; toggle mutes; silent switch silences;
                           # backgrounding pauses BGM; foregrounding resumes
```

---

## Done when
- Assets preload once (`loadAll`) — no first-play hitch.
- One BGM player loops at low volume; SFX overlap without per-shot player leaks.
- Mute toggle is visible, labeled, persisted, and conservatively defaulted; flipping it
  immediately stops BGM and gates SFX.
- iOS session category is `ambient` → the hardware silent switch and screen-lock silence the game.
- Backgrounding pauses/stops BGM; foregrounding resumes (respecting the mute flag).
- All players `dispose()` on teardown; no `flame_audio`/`audioplayers` import leaks into the
  pure-Dart core; `flutter analyze` and `dart test` are clean.

## Common pitfalls
- **Silent switch ignored:** leaving the default `playback`/non-ambient iOS category — kids' game
  keeps blaring with the mute switch on. Always set `AVAudioSessionCategory.ambient` (step 3).
- **Player leak:** `await AudioPlayer().play(...)` per tap creates and abandons a native player each
  time. Reuse a small pool (audioplayers) or `AudioPool`/`FlameAudio.play` (Flame).
- **No preload:** calling `play` cold loads from disk on the UI path → audible stutter. `loadAll`
  in `onLoad`/`preload`.
- **BGM survives backgrounding:** raw `ReleaseMode.loop` player without a lifecycle observer keeps
  playing in the background. Use `FlameAudio.bgm` or wire `didChangeAppLifecycleState` (step 6).
- **Both audio deps:** adding `audioplayers` *and* `flame_audio` — `flame_audio` already includes
  `audioplayers`. Pick one (`package-policy`).
- **Audio in the core:** importing the audio plugin into pure-Dart logic breaks `dart test` (no
  Flutter binding) and couples rules to side effects.
- **Loud defaults:** auto-starting BGM at full volume on first launch. Default conservatively, keep
  volumes low (BGM ~0.3–0.4, SFX ~0.6), gentle sounds only (`accessibility-child-safety`).
- **Version drift:** audioplayers' context API changed across majors (`respectSilence` →
  per-platform `AudioContextIOS`). Confirm the exact field names against your locked version with
  `dart pub deps` before trusting any snippet.

## Cross-links
- `references/flutter-flame-patterns` (Flame game structure, `onLoad`/`onRemove`)
- `references/flutter-game-architecture` (settings model, event callbacks, UI/logic separation)
- `references/asset-pipeline` (audio formats, naming, licensing)
- `references/accessibility-child-safety` (gentle sound, labeled controls, kids-safety)
- `references/package-policy` (one audio dependency, justification)
- `references/testing-and-release` (mockable audio service, `dart test`)
- `checklists/*` (pre-release: mute works, silent switch respected, no background audio)
