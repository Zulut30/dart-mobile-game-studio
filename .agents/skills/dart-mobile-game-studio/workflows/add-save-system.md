# Workflow: Add a Save System

**Goal:** Persist player progress and settings durably and safely, with a versioned schema and migrations, while keeping the pure-Dart core free of any persistence-package import.

## When to use
- The game must remember anything across launches: unlocked levels, high scores, stars, last-played level, audio/haptics/colorblind settings, tutorial-seen flags.
- You are adding "Continue", a settings screen that sticks, per-level best times, or a collection/inventory.
- **Not** for transient in-run state (that lives in the core model and dies with the run) and **not** for cloud/account sync (kids builds are local-only — see kids note).

## Pick the storage tier (decide first)
Map the *shape* of what you persist to the smallest tool that fits. Do not reach for a database to store five booleans.

| You are persisting | Use | Package |
|---|---|---|
| A handful of scalars (bool/int/double/String/List&lt;String&gt;): settings, flags, last level, single high score | Key-value store | `shared_preferences` |
| One cohesive blob with nested structure (progress map, per-level records, save "slots") that you read/write whole | JSON file in app docs dir | `path_provider` + `dart:convert` (no extra dep) |
| Many queryable/related records, partial updates, sorting, growth over time (leaderboard with 1000s of rows, large inventory) | Embedded DB | `drift` *or* `isar`/`hive` (justify per package-policy) |

Default for these simple 2D games is **key-value for settings + a JSON blob for progress**. Only escalate to a DB when you actually need queries/partial writes over many rows — that is the bar in `references/package-policy` and `references/quality-policy`.

Cross-links: `references/flutter-game-architecture` (layering), `references/package-policy` (dependency bar), `references/accessibility-child-safety` (kids/PII), `checklists/*` (release gates).

## Prerequisites
- Pure-Dart core exists under `lib/src/` (or `package:<game>_core`) with **no `package:flutter` import** and **no persistence import**. Verify before starting:
  ```bash
  grep -rn "shared_preferences\|path_provider\|drift\|isar\|hive\|package:flutter" lib/src/  # core dir → expect no matches
  ```
- `dart test` is green; analyzer is clean (`dart analyze`).
- You know which fields survive a restart. Write them down before coding.

## The architectural rule (do not skip)
The core stays pure. Persistence is a boundary concern. Three layers:

1. **Domain (pure Dart, in core):** plain value types — e.g. `GameProgress`, `GameSettings` — immutable, `==`/`hashCode`, `copyWith`. No `toJson`/`fromJson` here if you want the core to know *nothing* about serialization; or allow plain `Map<String,Object?>` round-trip methods that import only `dart:convert` (still Flutter-free). Either is fine; pick one and be consistent.
2. **DTO + mapper (adapter):** the serialization-aware shape (`schemaVersion`, JSON keys, DB columns) plus pure functions `domainToDto` / `dtoToDomain`. This is where versioning lives.
3. **Repository (adapter, imports the package):** an abstract interface defined near the core consumers, with a concrete impl that touches `shared_preferences` / file IO / the DB. The core depends on the **interface only**.

```dart
// lib/src/save/save_repository.dart  — interface (no package import)
abstract interface class SaveRepository {
  Future<GameState> load();          // returns defaults if nothing stored
  Future<void> save(GameState state);
  Future<void> reset();              // wipe (for "delete data" / tests)
}
```

The Flutter/UI layer constructs the concrete repository once and injects it (constructor, `Provider`, `get_it`, etc.). The core never sees the implementation.

---

## STEPS

### 1. Add only the deps you chose
```bash
flutter pub add shared_preferences       # scalars
flutter pub add path_provider            # JSON-file blob
# DB ONLY if the table above said so, e.g.:
# flutter pub add drift drift_flutter && flutter pub add --dev drift_dev build_runner
```
Run `dart pub get`. Justify any DB dep in your handoff per `references/package-policy`.

### 2. Define the schema constant and the versioned DTO
Put `schemaVersion` at the top level of every persisted payload. Bump it whenever the serialized shape changes.

```dart
// lib/src/save/save_dto.dart
import 'dart:convert';

const int kSaveSchemaVersion = 2; // bump on every shape change

class SaveDto {
  const SaveDto({
    required this.schemaVersion,
    required this.highScore,
    required this.lastLevel,
    required this.unlockedLevels,
  });

  final int schemaVersion;
  final int highScore;
  final int lastLevel;
  final List<int> unlockedLevels;

  Map<String, Object?> toJson() => {
    'schemaVersion': schemaVersion,
    'highScore': highScore,
    'lastLevel': lastLevel,
    'unlockedLevels': unlockedLevels,
  };

  static SaveDto fromJson(Map<String, Object?> json) => SaveDto(
    schemaVersion: (json['schemaVersion'] as num?)?.toInt() ?? 1,
    highScore: (json['highScore'] as num?)?.toInt() ?? 0,
    lastLevel: (json['lastLevel'] as num?)?.toInt() ?? 0,
    unlockedLevels:
        (json['unlockedLevels'] as List?)?.cast<num>().map((n) => n.toInt()).toList() ??
        const <int>[],
  );

  String encode() => jsonEncode(toJson());
  static SaveDto decode(String s) => fromJson(jsonDecode(s) as Map<String, Object?>);
}
```
Rules: never `as int` directly on decoded JSON (numbers come back as `num`/`double`); always provide a default; never let a missing/extra key throw.

### 3. Write the migration function (pure, total, tested)
A single function takes whatever was on disk (any old version) and returns a current-version `SaveDto`. Migrations are **forward-only and additive**; never reorder or repurpose an existing key.

```dart
// lib/src/save/save_migration.dart
SaveDto migrateToCurrent(Map<String, Object?> raw) {
  var version = (raw['schemaVersion'] as num?)?.toInt() ?? 1;

  // v1 -> v2: added `unlockedLevels`; default to [lastLevel].
  if (version == 1) {
    final last = (raw['lastLevel'] as num?)?.toInt() ?? 0;
    raw = {...raw, 'unlockedLevels': [for (var i = 0; i <= last; i++) i]};
    version = 2;
  }
  // future: if (version == 2) { ... version = 3; }

  return SaveDto.fromJson({...raw, 'schemaVersion': kSaveSchemaVersion});
}
```
Decode path always routes through `migrateToCurrent` before `fromJson`. If `schemaVersion` on disk is **newer** than this build (user downgraded), don't crash — load defaults or the safe subset and log; never throw into the UI.

### 4a. Implement the repository — key-value (settings + small scalars)
Use the modern **`SharedPreferencesAsync`** API (no in-memory cache, isolate-safe). Available since `shared_preferences` 2.3.0.

```dart
// lib/src/save/prefs_save_repository.dart
import 'package:shared_preferences/shared_preferences.dart';
import 'save_repository.dart';

class PrefsSaveRepository implements SaveRepository {
  PrefsSaveRepository(this._prefs);
  final SharedPreferencesAsync _prefs;

  static const _kHighScore = 'highScore';
  static const _kSchema = 'schemaVersion';

  @override
  Future<GameState> load() async {
    final score = await _prefs.getInt(_kHighScore) ?? 0;
    // ...read other scalars, run any scalar migration on _kSchema...
    return GameState(highScore: score /* , ... */);
  }

  @override
  Future<void> save(GameState s) async {
    await _prefs.setInt(_kSchema, kSaveSchemaVersion);
    await _prefs.setInt(_kHighScore, s.highScore);
  }

  @override
  Future<void> reset() => _prefs.clear(); // or remove specific keys
}
```
Verified API surface (`SharedPreferencesAsync`): `getBool/getInt/getDouble/getString/getStringList`, `setBool/setInt/setDouble/setString/setStringList`, `remove`, `clear`, `getKeys`. There is no synchronous getter — every read is awaited. Construct once: `final prefs = SharedPreferencesAsync();`.

> If you need synchronous reads in `build()` (e.g. read a setting without `FutureBuilder`), use `SharedPreferencesWithCache.create(cacheOptions: SharedPreferencesWithCacheOptions(allowList: {'highScore', 'schemaVersion'}))` → returns a `Future<SharedPreferencesWithCache>` whose `getInt(key) → int?` is synchronous after init. Prefer the async variant unless you measure a need.
>
> Do **not** add new code on the legacy `SharedPreferences.getInstance()` path — it is the old API; new save systems use `SharedPreferencesAsync`.

### 4b. Implement the repository — JSON blob (progress)
One file, written whole, in the app documents directory.

```dart
// lib/src/save/file_save_repository.dart
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'save_dto.dart';
import 'save_migration.dart';
import 'save_repository.dart';

class FileSaveRepository implements SaveRepository {
  Future<File> get _file async {
    final dir = await getApplicationDocumentsDirectory(); // persists until uninstall
    return File('${dir.path}/save.json');
  }

  @override
  Future<GameState> load() async {
    try {
      final f = await _file;
      if (!await f.exists()) return const GameState.initial();
      final raw = jsonDecode(await f.readAsString()) as Map<String, Object?>;
      final dto = migrateToCurrent(raw);
      return dtoToDomain(dto);
    } catch (_) {
      return const GameState.initial(); // corrupt/partial file → safe defaults
    }
  }

  @override
  Future<void> save(GameState s) async {
    final f = await _file;
    final tmp = File('${f.path}.tmp');
    await tmp.writeAsString(domainToDto(s).encode(), flush: true); // write temp...
    await tmp.rename(f.path);                                       // ...atomic swap
  }

  @override
  Future<void> reset() async {
    final f = await _file;
    if (await f.exists()) await f.delete();
  }
}
```
The temp-write-then-rename keeps the save atomic: a crash mid-write never leaves a half-written `save.json`. `flush: true` forces the bytes to disk before the rename.

### 4c. Implement the repository — embedded DB (many records only)
Only if the tier table sent you here. Define tables in the adapter layer, generate code with `build_runner`, keep the DB class out of the core, and map rows ↔ domain value types in the repository. Treat **schema migrations as the DB's `MigrationStrategy`/`onUpgrade`** keyed off the package's `schemaVersion` (Drift `migration:`/`onUpgrade`; Hive/Isar manual on open). Same principle: bump version, migrate forward, never reinterpret an existing column. Full table/codegen setup lives in `references/codegen-and-boilerplate` and the relevant `references/dart/*`.

### 5. Wire it at the Flutter boundary (and only there)
```dart
// lib/main.dart (or a bootstrap fn) — the ONLY place the impl is named
final SaveRepository repo = FileSaveRepository();   // or PrefsSaveRepository(SharedPreferencesAsync())
final state = await repo.load();
runApp(MyGame(repo: repo, initialState: state));
```
Save on the right moments, not every frame: on level complete, on settings change, and on app lifecycle pause. Hook lifecycle with `AppLifecycleListener(onPause: () => repo.save(currentState))` (or `didChangeAppLifecycleState` → `AppLifecycleState.paused`) so progress survives a backgrounded/killed app. Debounce rapid saves; never block the game loop on `await save()`.

### 6. Tests (pure-Dart first — they need no Flutter)
Put DTO/migration tests in the core `test/` so they run under `dart test`.
```dart
// test/save_migration_test.dart
import 'package:test/test.dart';
test('v1 save migrates to current with unlockedLevels derived', () {
  final v1 = {'schemaVersion': 1, 'highScore': 30, 'lastLevel': 2};
  final dto = migrateToCurrent(v1);
  expect(dto.schemaVersion, kSaveSchemaVersion);
  expect(dto.unlockedLevels, [0, 1, 2]);
});
test('round-trips losslessly', () {
  final dto = SaveDto(schemaVersion: kSaveSchemaVersion, highScore: 9, lastLevel: 1, unlockedLevels: const [0, 1]);
  expect(SaveDto.decode(dto.encode()).toJson(), dto.toJson());
});
test('corrupt/empty map yields safe defaults, never throws', () {
  expect(() => migrateToCurrent(<String, Object?>{}), returnsNormally);
});
```
Then run the repo:
```bash
dart test                 # core: DTO + migration + mapper (fast, no Flutter)
flutter test              # widget/integration: SharedPreferences.setMockInitialValues({...}) or a temp dir for files
dart analyze              # must be clean
dart format --set-exit-if-changed .   # 2-space, enforced
```
For widget tests against prefs, seed with `SharedPreferences.setMockInitialValues({...})` (works for the mock backend) or inject a fake `SaveRepository`. For file tests, point at a temp directory and assert load-after-save.

## Done when
- Core dir still has **zero** persistence/Flutter imports (`grep` from prerequisites is clean).
- `schemaVersion` is written on every save and `migrateToCurrent` handles every prior version plus empty/corrupt input without throwing.
- Save is atomic (temp+rename for files) and triggered on level-complete / settings-change / app-pause — not per frame.
- `dart test`, `flutter test`, `dart analyze`, `dart format` all pass, and you ran them (report real output).
- Reset/"delete my data" path exists and works (kids requirement + test hygiene).

## Common pitfalls
- **Core contamination.** Importing `shared_preferences`/`dart:io` into `lib/src/` core. Keep it behind the `SaveRepository` interface.
- **`as int` on decoded JSON.** JSON numbers decode as `num`/`double`; cast via `(x as num).toInt()` and always default. Same for `as List` → `.cast<...>()`.
- **No version field.** Without `schemaVersion` you can't migrate; the first shape change corrupts every existing player's save.
- **Repurposing an old key/column.** Migrations must be additive and forward-only. Add new keys; never change the meaning of an existing one.
- **Non-atomic writes.** Writing directly over `save.json` risks a half-written file on crash. Temp-write + `rename` + `flush: true`.
- **Saving every frame / blocking the loop.** Debounce; fire-and-forget the await; save on meaningful events and lifecycle pause.
- **Crashing on a downgrade.** A future-versioned file (user rolled back) must degrade gracefully, not throw.
- **Building on the legacy prefs API.** New work uses `SharedPreferencesAsync` (or `SharedPreferencesWithCache`), not `SharedPreferences.getInstance()`.

## Kids-safety notes (Apple Kids + Google Play Families)
- **Local-only.** No cloud sync, no accounts, no network for save data. Everything stays in app docs / prefs on-device.
- **No PII.** Never persist names, emails, birthdays, device identifiers, precise location, or free-text the child typed that could identify them. Store gameplay scalars only (scores, levels, settings). If you must store a display name, keep it on-device and never transmit it.
- **No analytics smuggled into saves.** Don't log play timestamps/behavior for off-device use.
- **Deletable.** Provide a clear "reset progress"/"delete data" action (behind a parental gate if it's destructive) backed by `repo.reset()`.
- Cross-check against `references/accessibility-child-safety` and the kids checklist in `checklists/*` before handoff; provide a risk list, not a store-approval guarantee.
