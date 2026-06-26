# Workflow: Add a level system (JSON data + loader + progression)

**Goal:** Add data-driven levels (JSON), a pure-Dart loader with versioning/migration, validation, a level-select screen with unlock progression, and persisted progress — to a Flutter/Flame mobile game.

## When to use
- The game has more than one playable level/board/puzzle and you want them authored as **data, not code**.
- You need a level-select grid, "complete a level to unlock the next", and saved stars/best scores that survive app restart.
- Use this for any genre in this skill (coloring, sliding/jigsaw, light platformer, drag-and-drop, memory, lite runner, tap-reaction). Levels stay genre-agnostic via the shared schema.

**Don't use when** there is a single endless mode with no discrete levels (skip levels; persist only high score). For a brand-new game, scaffold the genre first (see the relevant `templates/*.md`) and add the level system once the core loop works.

## Prerequisites
- A working core loop with a **pure-Dart model** under `lib/models/` + `lib/systems/` (no `package:flutter` / `package:flame` imports there). See `references/flutter-game-architecture.md`.
- A state machine reaching `win` (level complete) — the unlock hook fires there.
- `flutter`, `dart`, and (if used) `python3` on PATH. Verify with `scripts/verify-flutter-project.sh`.
- Read first: `references/asset-pipeline.md` (asset declaration + loading), `assets/level-schema-template.json` (the schema), `references/dart/dart-api-design.md` (fromJson conventions).

## Doctrine for this feature
- **Levels are data, not Dart.** One JSON file per level under `assets/levels/`. No level geometry hardcoded in `.dart`.
- **Loader + model are pure Dart.** Parsing, validation, migration, and progression rules live under `lib/models/` and `lib/systems/` and are unit-tested with `dart test` — no Flutter import. The bundle/`rootBundle` call is the *only* Flutter-touching part and stays in a thin adapter.
- **Version everything.** Every level carries `schemaVersion`; the loader migrates old versions forward before constructing the model. Save data carries its own `schemaVersion` too.
- **Validate before you ship.** `scripts/validate-levels.py` gates every JSON file in CI.
- **Kids-safe persistence.** `shared_preferences` (or a JSON file via `path_provider`) only — no accounts, no network, no analytics. See `references/accessibility-child-safety.md`.

---

## STEPS

### 1. Author the level JSON files
Copy `assets/level-schema-template.json` as your reference and create one file per level under `assets/levels/`, zero-padded and ordered:

```text
assets/levels/
├─ level_001.json
├─ level_002.json
└─ level_003.json
```

Minimum valid level (genre-agnostic; trim/extend per the schema's `entities`, `goal`, `tuning`):

```json
{
  "schemaVersion": 1,
  "id": "level_001",
  "name": "First Steps",
  "template": "drag-and-drop-puzzle",
  "difficulty": 1,
  "seed": 1001,
  "size": { "width": 100, "height": 100 },
  "entities": [
    { "id": "slot_a", "kind": "slot", "position": { "x": 0.2, "y": 0.5 }, "matchGroup": "a" },
    { "id": "piece_a", "kind": "piece", "position": { "x": 0.8, "y": 0.5 }, "matchGroup": "a", "shape": "circle", "color": "#FF4081" }
  ],
  "goal": { "type": "placeAll" }
}
```

Rules (enforced by the schema + validator):
- `schemaVersion` (int ≥ 1), `id` (stable, matches filename stem), `size.width/height` (> 0), and `entities` (array) are **required**.
- Coordinates are **normalized 0..1** relative to `size` unless an entity sets `"absolute": true`.
- Colors are `#RRGGBB` or `#AARRGGBB`. Put gameplay constants in `tuning`, not in code.
- Keep a stable `id` per level: progress is keyed on `id`, so renaming a file orphans its saved progress.

You need a manifest so the app knows the level order without scanning the bundle at runtime. Create `assets/levels/manifest.json`:

```json
{ "schemaVersion": 1, "levels": ["level_001", "level_002", "level_003"] }
```

### 2. Declare the assets in `pubspec.yaml`
Exactly 2-space indent; directory entries **must** end with `/` (see `references/asset-pipeline.md`):

```yaml
flutter:
  assets:
    - assets/levels/
```

If `shared_preferences` isn't already a dependency, add it (justified per `references/package-policy.md` — first-party Flutter Favorite, offline, no tracking):

```bash
flutter pub add shared_preferences
flutter pub get
```

### 3. Define the pure-Dart level model + `fromJson` + migration
Create `lib/models/level.dart` — **no Flutter/Flame imports.** `fromJson` migrates old `schemaVersion`s forward, then parses. Validate defensively and throw a typed error on bad data.

```dart
// lib/models/level.dart — PURE DART (no package:flutter / package:flame)
const int kCurrentLevelSchema = 1;

class LevelFormatException implements Exception {
  LevelFormatException(this.message);
  final String message;
  @override
  String toString() => 'LevelFormatException: $message';
}

class Vec2 {
  const Vec2(this.x, this.y);
  final double x, y;
}

class LevelEntity {
  const LevelEntity({
    required this.id,
    required this.kind,
    this.position,
    this.shape,
    this.color,
    this.matchGroup,
  });

  final String id;
  final String kind;
  final Vec2? position;
  final String? shape;
  final String? color;
  final String? matchGroup;

  factory LevelEntity.fromJson(Map<String, dynamic> j) {
    final pos = j['position'] as Map<String, dynamic>?;
    return LevelEntity(
      id: _str(j, 'id'),
      kind: _str(j, 'kind'),
      position: pos == null
          ? null
          : Vec2(_num(pos, 'x').toDouble(), _num(pos, 'y').toDouble()),
      shape: j['shape'] as String?,
      color: j['color'] as String?,
      matchGroup: j['matchGroup'] as String?,
    );
  }
}

class Level {
  const Level({
    required this.schemaVersion,
    required this.id,
    required this.size,
    required this.entities,
    this.name,
    this.difficulty = 1,
    this.seed,
  });

  final int schemaVersion;
  final String id;
  final Vec2 size; // (width, height)
  final List<LevelEntity> entities;
  final String? name;
  final int difficulty;
  final int? seed;

  /// Parse a decoded JSON map into a [Level], migrating older schema versions
  /// forward first. Throws [LevelFormatException] on malformed data.
  factory Level.fromJson(Map<String, dynamic> raw) {
    final migrated = _migrate(raw);
    final size = migrated['size'] as Map<String, dynamic>?;
    if (size == null) throw LevelFormatException('missing "size"');
    final width = _num(size, 'width').toDouble();
    final height = _num(size, 'height').toDouble();
    if (width <= 0 || height <= 0) {
      throw LevelFormatException('size.width/height must be > 0');
    }
    final ents = (migrated['entities'] as List?) ?? const [];
    return Level(
      schemaVersion: migrated['schemaVersion'] as int,
      id: _str(migrated, 'id'),
      name: migrated['name'] as String?,
      difficulty: (migrated['difficulty'] as int?) ?? 1,
      seed: migrated['seed'] as int?,
      size: Vec2(width, height),
      entities: ents
          .map((e) => LevelEntity.fromJson(e as Map<String, dynamic>))
          .toList(growable: false),
    );
  }

  /// Pure migration: bump old level JSON to [kCurrentLevelSchema].
  /// Add a `case` per breaking schema bump; each step is small and tested.
  static Map<String, dynamic> _migrate(Map<String, dynamic> raw) {
    final out = Map<String, dynamic>.from(raw);
    var v = (out['schemaVersion'] as int?) ?? 1;
    if (v > kCurrentLevelSchema) {
      throw LevelFormatException(
        'level schemaVersion $v is newer than supported '
        '$kCurrentLevelSchema — upgrade the app',
      );
    }
    while (v < kCurrentLevelSchema) {
      switch (v) {
        // Example for the day you bump to schema 2:
        // case 1:
        //   out['tuning'] ??= <String, dynamic>{};
        //   v = 2;
        //   break;
        default:
          throw LevelFormatException('no migration from schemaVersion $v');
      }
      // ignore: dead_code
      out['schemaVersion'] = v;
    }
    out['schemaVersion'] = kCurrentLevelSchema;
    return out;
  }
}

String _str(Map<String, dynamic> j, String k) {
  final v = j[k];
  if (v is! String || v.isEmpty) {
    throw LevelFormatException('field "$k" must be a non-empty string');
  }
  return v;
}

num _num(Map<String, dynamic> j, String k) {
  final v = j[k];
  if (v is! num) throw LevelFormatException('field "$k" must be a number');
  return v;
}
```

> Keep the loader (which touches `rootBundle`) out of this file — `Level.fromJson` takes an already-decoded `Map`, so it stays pure and `dart test`-able with no Flutter dependency.

### 4. Add the bundle loader adapter (the only Flutter-touching part)
Create `lib/systems/level_loader.dart`. It reads the manifest + each level file via `rootBundle` and hands decoded maps to the pure model. `rootBundle` wants the **full** asset path.

```dart
// lib/systems/level_loader.dart — thin adapter; the only place rootBundle appears
import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle, AssetBundle;
import '../models/level.dart';

class LevelLoader {
  const LevelLoader({this.bundle});
  final AssetBundle? bundle; // inject a fake in widget tests; defaults to rootBundle

  Future<List<String>> loadManifest() async {
    final raw = await _load('assets/levels/manifest.json');
    final json = jsonDecode(raw) as Map<String, dynamic>;
    return (json['levels'] as List).cast<String>();
  }

  Future<Level> loadLevel(String id) async {
    final raw = await _load('assets/levels/$id.json');
    return Level.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  }

  Future<String> _load(String path) =>
      (bundle ?? rootBundle).loadString(path);
}
```

Reference (official): load JSON with `rootBundle.loadString('assets/...')` — Flutter docs, *Loading assets* / *assets-and-images*.

### 5. Add the progress model + persistence (versioned, kids-safe)
Split it: a **pure-Dart** progress model (testable) and a **thin** repository that does the `shared_preferences` I/O.

```dart
// lib/models/level_progress.dart — PURE DART
const int kCurrentSaveSchema = 1;

class LevelProgress {
  const LevelProgress({this.completed = const {}, this.stars = const {}});

  final Set<String> completed;        // level ids cleared at least once
  final Map<String, int> stars;       // id -> best stars (0..3)

  bool isCompleted(String id) => completed.contains(id);
  int starsFor(String id) => stars[id] ?? 0;

  /// First level is always unlocked; level N unlocks when N-1 is completed.
  bool isUnlocked(String id, List<String> order) {
    final i = order.indexOf(id);
    if (i <= 0) return true;
    return completed.contains(order[i - 1]);
  }

  LevelProgress recordWin(String id, {int starsEarned = 0}) {
    final best = starsEarned > starsFor(id) ? starsEarned : starsFor(id);
    return LevelProgress(
      completed: {...completed, id},
      stars: {...stars, id: best},
    );
  }

  Map<String, dynamic> toJson() => {
        'schemaVersion': kCurrentSaveSchema,
        'completed': completed.toList()..sort(),
        'stars': stars,
      };

  factory LevelProgress.fromJson(Map<String, dynamic> raw) {
    final v = (raw['schemaVersion'] as int?) ?? 1;
    if (v > kCurrentSaveSchema) return const LevelProgress(); // newer save: start clean, don't crash
    final stars = <String, int>{};
    (raw['stars'] as Map?)?.forEach((k, val) => stars['$k'] = (val as num).toInt());
    return LevelProgress(
      completed: ((raw['completed'] as List?) ?? const []).map((e) => '$e').toSet(),
      stars: stars,
    );
  }
}
```

```dart
// lib/systems/progress_repository.dart — thin persistence adapter
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/level_progress.dart';

class ProgressRepository {
  static const _key = 'level_progress_v1';

  Future<LevelProgress> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) return const LevelProgress();
    try {
      return LevelProgress.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return const LevelProgress(); // corrupt save: recover, never crash
    }
  }

  Future<void> save(LevelProgress p) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(p.toJson()));
  }
}
```

Reference (official): `SharedPreferences.getInstance()` + `setString`/`getString` — Flutter docs (`shared_preferences`). No personal data is stored; keys are local-only.

### 6. Wire the unlock hook into the state machine
On the `win` transition, call `recordWin` and persist. Keep it in your state-management adapter (Notifier/Bloc) — not in the pure model:

```dart
Future<void> onLevelComplete(String id, int starsEarned) async {
  progress = progress.recordWin(id, starsEarned: starsEarned);
  await repo.save(progress);   // ProgressRepository
  // then transition: playing -> win -> (menu / next level)
}
```

### 7. Build the level-select screen
A `widgets/` screen that loads the manifest + progress, then renders a grid. Locked levels are non-tappable and labeled for VoiceOver/TalkBack (`references/accessibility-child-safety.md`, `checklists/accessibility.md`):

```dart
// lib/widgets/level_select_screen.dart (sketch)
final order = await loader.loadManifest();
final progress = await repo.load();
// For each id in order:
final unlocked = progress.isUnlocked(id, order);
Semantics(
  button: unlocked,
  label: unlocked
      ? 'Level ${order.indexOf(id) + 1}, ${progress.starsFor(id)} of 3 stars'
      : 'Level ${order.indexOf(id) + 1}, locked',
  child: LevelTile(
    enabled: unlocked,
    stars: progress.starsFor(id),
    onTap: unlocked ? () => openLevel(id) : null,
  ),
);
```
- Provide a 44x44 logical-px minimum tap target; show a lock icon **and** the locked semantics label (don't rely on color alone).
- Respect Dynamic Type / large fonts and Reduce Motion on any unlock animation.

### 8. Validate the level data
Run the validator over every JSON file (reads only; works with or without the `jsonschema` pip package):

```bash
scripts/validate-levels.py assets/levels/
```
Expected on success: `All N level file(s) valid.` (exit 0). It checks the schema invariants — required fields, `size > 0`, hex colors, known `shape`/`goal.type`/`template` enums. Note: `manifest.json` is genre-data, not a level; point the validator at the level files (it scans `*.json` in the folder, so keep the manifest valid against the schema **or** move levels into a subfolder you validate explicitly, e.g. `scripts/validate-levels.py assets/levels/level_*.json`).

### 9. Write the tests (`dart test`, no device)
Cover the pure core under `test/`:
- `Level.fromJson` parses a known-good level; **throws `LevelFormatException`** on missing `size`, `size.width <= 0`, empty `id`, non-number coordinate.
- **Migration**: a level at an older `schemaVersion` migrates to `kCurrentLevelSchema`; a level with `schemaVersion > kCurrentLevelSchema` throws.
- `LevelProgress.isUnlocked`: level 1 always unlocked; level N locked until N-1 completed.
- `recordWin` is idempotent and keeps the **best** star count (winning again with fewer stars doesn't lower it).
- `LevelProgress` round-trips through `toJson`/`fromJson`; `fromJson` on corrupt/newer data returns an empty progress instead of throwing.
- (Optional, `flutter_test`) `LevelLoader` with an injected fake `AssetBundle` loads the manifest and a level.

```bash
dart test            # pure model + systems
flutter test         # if you added the widget-test for the loader/screen
```

### 10. Format, analyze, validate — the quality gate
```bash
dart format .                    # 2-space, no changes expected
dart analyze                     # zero issues
scripts/validate-levels.py assets/levels/level_*.json
dart test
```
See `checklists/dart-code-quality.md` and `checklists/game-architecture.md`.

---

## Done when
- [ ] Each level is a JSON file under `assets/levels/`, declared in `pubspec.yaml`, with a `manifest.json` defining order.
- [ ] `Level.fromJson` (pure Dart) parses + migrates by `schemaVersion` and throws a typed error on bad data; the only `rootBundle` call lives in `LevelLoader`.
- [ ] Progress is persisted via `shared_preferences`, versioned (`schemaVersion`), and recovers gracefully from corrupt/newer saves.
- [ ] Level-select shows locked/unlocked + stars with correct Semantics; level N unlocks on N-1 completion.
- [ ] `scripts/validate-levels.py` passes; `dart format`, `dart analyze`, and `dart test` are clean.

## Common pitfalls
- **Hardcoding levels in Dart.** If geometry/tuning lives in `.dart`, it's not a level system — move it to JSON.
- **Leaking Flutter into the core.** `package:flutter` in `lib/models/` breaks `dart test` and the purity rule. Keep `rootBundle` in the adapter only; pass decoded maps into `fromJson`.
- **Forgetting migration / a `default` throw.** A loader that ignores `schemaVersion` silently mis-parses old or future saves. Always migrate forward and reject `schemaVersion` newer than the app supports.
- **Keying progress on filename/index.** Rename or reorder and progress is lost. Key on the stable level `id`.
- **Unstable seed.** Omitting `seed` makes shuffles/spawns non-reproducible; tests and "retry same level" then drift. Inject the level's `seed` into your `Random` (see `assets/seeded_random.dart`).
- **Crashing on corrupt save.** Always wrap deserialize in try/catch and fall back to empty progress — a kid's device must never hard-fail to a black screen.
- **Validator + manifest collision.** `validate-levels.py` scans every `*.json`; `manifest.json` isn't a level. Validate `level_*.json` explicitly, or keep the manifest schema-valid.
- **Color-only lock state.** Locked tiles need an icon + semantics label, not just a gray tint (`checklists/accessibility.md`).
- **New persistence dependency unjustified.** If you reach past `shared_preferences`/`path_provider`, justify it against `references/package-policy.md` first.

## Cross-links
- `references/flutter-game-architecture.md` — folder layout, pure-core rule, persistence pattern.
- `references/asset-pipeline.md` — asset declaration + `rootBundle` vs Flame loaders.
- `references/accessibility-child-safety.md`, `checklists/accessibility.md` — kids-safe persistence + semantics.
- `references/package-policy.md` — justifying `shared_preferences`/`path_provider`.
- `assets/level-schema-template.json`, `scripts/validate-levels.py` — schema + validator.
- `assets/seeded_random.dart` — deterministic RNG from a level `seed`.
- `checklists/dart-code-quality.md`, `checklists/game-architecture.md`, `checklists/testing.md`.
