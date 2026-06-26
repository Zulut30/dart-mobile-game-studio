# Codegen & boilerplate

When to let a code generator write the boilerplate, when to hand-write it, and exactly how to wire
each generator for a simple 2D mobile game. Codegen is a **dependency and a build step** — it earns
its place only when it removes enough hand-written, error-prone boilerplate to justify the
`build_runner` cost. Per `package-policy` (official → mature community → none), prefer the smallest
toolchain that does the job; a coloring book or sliding puzzle often needs **zero** code generators.

Everything generated for the pure-Dart core (`lib/models/` + `lib/systems/`) stays
import-clean of `package:flutter`/`package:flame` — `freezed` and `json_serializable` output is plain
Dart and runs under `dart test` on the VM. Format with `dart format` (2-space), keep it
analyzer-clean.

## Decide: does codegen earn its weight?

| Concern | Hand-write when… | Generate when… | Tool |
|---|---|---|---|
| Immutable value model (`==`/`hashCode`/`copyWith`) | A handful of small models | Many value types, deep `copyWith`, nullable-clear correctness matters | `freezed` (or `equatable` for `==` only, no codegen) |
| Sealed state machine (unions) | 4–6 states you can write by hand (see `dart-patterns-idioms.md`) | Many variants × shared fields, want generated `copyWith`/`map`/`when` | `freezed` (sealed) |
| Level / save JSON (`fromJson`/`toJson`) | One or two DTOs; you control the shape | Several DTOs, nested objects, enums, field renames | `json_serializable` |
| Routing | 2–4 flat screens | Deeply nested routes you want generated, typed route args | `go_router` (no codegen) → `auto_route` only if nested codegen pays off |
| Localized strings | Single-language game | Any user-facing text you may translate (Kids stores span many locales) | `gen-l10n` (Flutter tool, **not** build_runner) |

Default posture for this skill: **no codegen for a 1–3 screen game.** Reach for `freezed` only once
hand-written value/union boilerplate becomes a maintenance tax; reach for `json_serializable` once
you have more than a couple of DTOs; prefer `go_router` (zero codegen) for routing and only adopt
`auto_route` when nested-route generation genuinely earns its build step. Every generator added is one
more thing that must stay green in CI.

```dart
// DON'T — pull in build_runner + freezed + json_serializable to model a 2-field Level.
// Three dev_deps and a codegen step to avoid ~15 lines you can read and test directly.
// DO — hand-write the small core (see dart-patterns-idioms.md), add codegen when it stops scaling.
```

## build_runner: the shared build step

`build_runner` (published by the Dart team, `tools.dart.dev`) runs every source-generating builder —
`freezed`, `json_serializable`, `auto_route_generator` all plug into it. It is a **dev dependency**;
it ships no runtime code.

```yaml
# pubspec.yaml
dev_dependencies:
  build_runner: ^2.4.0   # check pub.dev for the current 2.x
```

```bash
# One-shot build (CI, or after editing an annotated class):
dart run build_runner build --delete-conflicting-outputs

# Watch mode — rebuilds on every save while you iterate:
dart run build_runner watch --delete-conflicting-outputs
```

- **`--delete-conflicting-outputs`** lets the build overwrite stale generated files instead of
  aborting on a conflict (a renamed class leaves an orphaned `*.g.dart`). Without it, the second build
  after a rename fails. It is the standard flag the `freezed`/`json_serializable` docs tell you to run;
  use it by default.
- For a **Flutter** package the equivalent is `dart run build_runner build` (or
  `flutter pub run build_runner build` on older SDKs); `dart run` is the current form.
- Add `.dart_tool/` to `.gitignore` (build cache). That is separate from the generated `*.g.dart` /
  `*.freezed.dart` files — see the commit policy below.
- Generated files are **derived, never hand-edited.** If you need to change output, change the source
  annotation and rebuild. A `// GENERATED CODE - DO NOT MODIFY BY HAND` header marks them.

### Generated-file policy: pick ONE, project-wide

The Dart team leaves this to each project; **decide once and enforce it** so a clean checkout always
has a consistent answer.

| Policy | Do this | Trade-off |
|---|---|---|
| **(A) Commit generated files** | Commit `*.g.dart`, `*.freezed.dart`, `*.gr.dart`. Add a CI **drift check**: run the build, then `git diff --exit-code` — fail if output changed. | Clean checkout builds with no codegen step; diffs are noisier; must keep generated files in review. |
| **(B) Build in CI** | `.gitignore` the generated files; run `dart run build_runner build --delete-conflicting-outputs` as the first CI/build step (and document it in the README). | Smaller, quieter repo; but a fresh checkout doesn't compile until you generate, and IDEs show errors until the first build. |

Recommendation for this skill: **(A) commit + drift-check.** A small game benefits from a
checkout that compiles immediately (and from `dart test` of the pure core needing no generate step),
and the drift check (`build` then `git diff --exit-code`) catches a stale commit just as reliably.
Whichever you pick, do not mix — half-committed generated files are the worst of both.

```yaml
# .gitignore — Policy (A): cache only, generated files ARE committed
.dart_tool/
# Policy (B) would additionally ignore:
# **/*.g.dart
# **/*.freezed.dart
# **/*.gr.dart
```

## freezed — immutable data classes & sealed unions

`freezed` generates `==`/`hashCode`, `toString`, `copyWith` (including deep/nested copy), and — for
sealed types — the union plumbing, from a single factory declaration. It removes exactly the
hand-written boilerplate that `dart-patterns-idioms.md` shows by hand; adopt it when that boilerplate
stops being a few small classes. **Freezed 3.x** aligns with Dart 3 class modifiers: you write a real
`abstract class` (single variant) or `sealed class` (union) with `with _$Name`, and switch over the
union with native pattern matching — no more `.when`/`.map` required.

```yaml
# pubspec.yaml
dependencies:
  freezed_annotation: ^3.0.0
dev_dependencies:
  build_runner: ^2.4.0
  freezed: ^3.0.0
  json_serializable: ^6.8.0   # only if a freezed class also needs fromJson/toJson
```

### Immutable data class

```dart
// lib/models/player.dart  — pure Dart; no flutter/flame import
import 'package:freezed_annotation/freezed_annotation.dart';

part 'player.freezed.dart';

@freezed
abstract class Player with _$Player {
  const factory Player({
    required int lives,
    required int score,
    PowerUp? powerUp, // nullable: null means "no active power-up"
  }) = _Player;
}
```

Generates value `==`/`hashCode` (so two equal `Player`s drive a rebuild and dedup in a `Set`),
`copyWith`, and `toString`. `copyWith` here correctly distinguishes "clear" from "unchanged" via
freezed's sentinel — the exact trap the hand-written `copyWith` in `dart-patterns-idioms.md` has to
guard manually:

```dart
final hurt = player.copyWith(lives: player.lives - 1);
final cleared = player.copyWith(powerUp: null); // actually clears it (freezed handles the sentinel)
```

### Sealed union — a game state machine

This is freezed's best fit for a game: one `sealed class` whose factories are the states, an
exhaustive `switch` the analyzer enforces, and generated `copyWith` per variant.

```dart
// lib/models/game_state.dart  — pure Dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'game_state.freezed.dart';

@freezed
sealed class GameState with _$GameState {
  const factory GameState.menu() = Menu;
  const factory GameState.playing({required int score}) = Playing;
  const factory GameState.paused({required int score}) = Paused;
  const factory GameState.won({required int score}) = Won;
  const factory GameState.lost() = Lost;
}

// Exhaustive switch — add a 6th factory and this fails to compile (analyzer-enforced).
String banner(GameState s) => switch (s) {
      Menu() => 'Tap to start',
      Playing(:final score) => 'Score $score',
      Paused(:final score) => 'Paused — $score',
      Won(:final score) => 'You win — $score!',
      Lost() => 'Try again',
    };
```

- Keep the **reducer pure** (`dart-patterns-idioms.md`): freezed gives you the state *types* and
  `copyWith`; you still write `reduce(state, event)` by hand so transitions stay testable on the VM.
- For JSON on a union, add `part 'x.g.dart';` and a `fromJson` factory (next section); freezed
  discriminates variants by a `runtimeType` key unless you set `@Freezed(unionKey: ...)`.

```dart
// DON'T — hand-maintain ==/hashCode/copyWith/toString across a dozen growing value types.
// DO — once it's a dozen, let freezed generate them from the factory and keep your eyes on rules.
```

## json_serializable — level & save DTOs

`json_serializable` (Dart team, `google.dev` publisher) generates `_$XFromJson`/`_$XToJson` from a
`@JsonSerializable()` class, so you don't hand-roll map parsing for every DTO. Pair it with the
**`schemaVersion` + migration** discipline from `dart-patterns-idioms.md`: the generator handles the
*field mapping*; you still own *version migration* and defensive defaults, because the generated
`fromJson` will throw on a genuinely malformed payload.

```yaml
# pubspec.yaml
dependencies:
  json_annotation: ^4.9.0
dev_dependencies:
  build_runner: ^2.4.0
  json_serializable: ^6.8.0
```

```dart
// lib/models/level_dto.dart  — pure Dart; data, not code (levels live as JSON assets)
import 'package:json_annotation/json_annotation.dart';

part 'level_dto.g.dart';

@JsonSerializable(explicitToJson: true)
class LevelDto {
  const LevelDto({
    required this.id,
    required this.par,
    this.schemaVersion = currentSchemaVersion,
  });

  static const currentSchemaVersion = 2;

  final String id;
  @JsonKey(defaultValue: 3) // tolerate a missing key instead of throwing
  final int par;
  final int schemaVersion;

  factory LevelDto.fromJson(Map<String, dynamic> json) => _$LevelDtoFromJson(json);
  Map<String, dynamic> toJson() => _$LevelDtoToJson(this);
}
```

- `@JsonKey(defaultValue:)` / `@JsonKey(name: 'snake_field')` cover most field-level needs;
  `@JsonSerializable(fieldRename: FieldRename.snake)` renames the whole class at once;
  `explicitToJson: true` is required when a field is itself a serializable object (nested DTOs).
- **Migration is yours, not the generator's.** Run a `_migrate(json)` pass *before*
  `LevelDto.fromJson` (the step-by-step forward migration in `dart-patterns-idioms.md`), so a shipped
  v1 save still loads in a v2 build. Generated `fromJson` only maps the *current* shape.
- Decode the bytes with `jsonDecode` from `dart:convert` and confirm `is Map<String, dynamic>` before
  handing them to `fromJson` — never `!` or blind-cast a save/level file.
- For a single tiny DTO, the hand-written `factory X.fromJson` (one `as num?`-guarded line) is still
  simpler than adding a generator. Switch to `json_serializable` when you have several DTOs or nesting.

## Routing: prefer go_router; auto_route only for nested codegen

| | `go_router` | `auto_route` |
|---|---|---|
| Publisher | Flutter team (`flutter.dev`) | community (well-maintained) |
| Codegen | **Optional** — works with plain `GoRouter`/`GoRoute`; typed routes via `go_router_builder` only if wanted | **Required** — `auto_route_generator` + `build_runner` |
| Best for | Flat or lightly-nested screens (menu → level select → game → settings) | Deeply nested route trees you want generated, typed route args out of the box |
| Cost | One runtime dep, no build step | Runtime dep + generator + a build step in CI |

Doctrine: **start with `go_router`, no codegen.** A simple game's navigation —
menu / level-select / game / settings / pause — is a handful of flat routes that need no generator.
Adopt `auto_route` only when nested-route generation and typed args genuinely pay for the extra build
step (rare at this scale).

### go_router (no codegen)

```dart
// lib/app/router.dart  — render layer (imports Flutter); not part of the pure core
import 'package:go_router/go_router.dart';

final router = GoRouter(
  routes: [
    GoRoute(path: '/', builder: (context, state) => const MainMenuScreen()),
    GoRoute(path: '/levels', builder: (context, state) => const LevelSelectScreen()),
    GoRoute(
      path: '/play/:levelId',
      builder: (context, state) => GameScreen(levelId: state.pathParameters['levelId']!),
    ),
    GoRoute(path: '/settings', builder: (context, state) => const SettingsScreen()),
  ],
  // Guards = redirect on app state (e.g. a parental gate before a sensitive screen).
  redirect: (context, state) => null,
);

// main.dart
MaterialApp.router(routerConfig: router);
```

### auto_route (codegen) — only when nested routing earns it

```dart
// lib/app/router.dart
import 'package:auto_route/auto_route.dart';

part 'router.gr.dart'; // generated by auto_route_generator via build_runner

@AutoRouterConfig()
class AppRouter extends RootStackRouter {
  @override
  List<AutoRoute> get routes => [
        AutoRoute(path: '/', page: MainMenuRoute.page),
        AutoRoute(
          path: '/play',
          page: GameShellRoute.page,
          children: [ // nested tree auto_route generates for you
            AutoRoute(path: 'board', page: BoardRoute.page),
            AutoRoute(path: 'hud', page: HudRoute.page),
          ],
        ),
      ];
}

// Each routable screen is annotated:
@RoutePage()
class MainMenuScreen extends StatelessWidget { /* ... */ }
```

```yaml
dependencies:
  auto_route: ^9.0.0
dev_dependencies:
  auto_route_generator: ^9.0.0
  build_runner: ^2.4.0
```

Guards in auto_route are an `AutoRouteGuard.onNavigation(resolver, router)` that calls
`resolver.next(true)` or redirects — the typed analog of go_router's `redirect`.

## Localization: gen-l10n (Flutter tool, NOT build_runner)

User-facing strings should go through `intl` + ARB + `gen-l10n` so the game can ship in multiple
locales — relevant for Kids/Families catalogs that span markets. **This codegen does not use
`build_runner`**: the Flutter tool generates `AppLocalizations` automatically on build (or via
`flutter gen-l10n`). Keep it separate from the build_runner generators above.

```yaml
# pubspec.yaml
dependencies:
  flutter_localizations:
    sdk: flutter
  intl: any
flutter:
  generate: true   # turns on gen-l10n
```

```yaml
# l10n.yaml  (project root)
arb-dir: lib/l10n
template-arb-file: app_en.arb
output-localization-file: app_localizations.dart
# output-class: AppLocalizations   # default
```

```json
// lib/l10n/app_en.arb  (template)
{
  "scoreLabel": "Score: {points}",
  "@scoreLabel": { "placeholders": { "points": { "type": "int" } } },
  "matchedOfTotal": "{matched} of {total} matched"
}
```

```dart
// In a widget (render layer): generated, type-safe accessors.
import 'l10n/app_localizations.dart';
// ...
Text(AppLocalizations.of(context)!.scoreLabel(score));

// main.dart
MaterialApp.router(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  routerConfig: router,
);
```

- Build with `flutter run` / `flutter build` (gen-l10n runs automatically) or force it with
  `flutter gen-l10n`. **Do not** run `build_runner` for localization.
- The generated `AppLocalizations` lives under `.dart_tool/` by default (regenerated on build), so the
  commit-vs-CI policy above does not apply to it — it's effectively always built in CI.
- The *labels themselves* belong to the render layer, but the **values** they format ("3 of 12
  matched") come from the pure model as plain getters (`dart/flutter-widgets-mastery.md` / accessibility) — so
  the model stays Flutter-free and the localized string is assembled at the edge.

## Boilerplate-by-layer cheat sheet

| Layer | Boilerplate | Default | Generator (when it scales) |
|---|---|---|---|
| **Models / entities** (pure) | `==`/`hashCode`/`copyWith`/`toString` | hand-write small; `equatable` for `==` only | `freezed` |
| **Game state** (pure) | sealed union + per-variant `copyWith` | hand-write 4–6 states + pure `reduce` | `freezed` sealed (still hand-write `reduce`) |
| **DTOs** (level/save, pure) | `fromJson`/`toJson` | hand-write 1–2; always own `schemaVersion`+migration | `json_serializable` |
| **Repositories / services** | interface + impl | hand-write (small surface; inject deps) | none — codegen rarely pays here |
| **Providers / controllers** | notifier wiring | `ValueNotifier`/`ChangeNotifier` (see architecture) | `riverpod_generator` only if already on Riverpod |
| **Routes / screens** | route table | `go_router`, no codegen | `auto_route` only for nested codegen |
| **Settings** | typed prefs | hand-write over `shared_preferences` + a versioned JSON model | none |
| **Localization** | locale lookup | `intl` + ARB | `gen-l10n` (Flutter tool, not build_runner) |

Rule of thumb: generate the **mechanical, repetitive, correctness-sensitive** boilerplate (value
equality, JSON mapping, nested routes) once it appears at scale; hand-write the **logic** (reducers,
migrations, guards, repositories) always, because that is what `dart test` must cover and what no
generator gets right for you.

---

*Verified against the official packages and docs: `dart-lang`/Dart-team **build_runner**
(`dart run build_runner build|watch`, `--delete-conflicting-outputs`, dev-dependency, builder
plug-in model); **freezed** 3.x (`@freezed` `abstract`/`sealed class with _$Name`, factory
constructors, generated `copyWith`/`==`, `part '*.freezed.dart'`, native pattern matching);
**json_serializable**/`json_annotation` (`@JsonSerializable`, `_$XFromJson`/`_$XToJson`, `@JsonKey`,
`fieldRename`/`explicitToJson`, `part '*.g.dart'`); **auto_route** (`@AutoRouterConfig`,
`RootStackRouter`, `@RoutePage`, nested `children`, `AutoRouteGuard`, `part '*.gr.dart'`); **go_router**
(Flutter-team, codegen-optional `GoRouter`/`GoRoute`, `routerConfig`, `redirect` guards); and Flutter's
**gen-l10n** (`flutter: generate: true`, `l10n.yaml`, ARB, `AppLocalizations` — generated by the
Flutter tool, not build_runner). Consistent with this skill's `flutter-game-architecture.md`,
`dart-patterns-idioms.md`, and `package-policy`.*
