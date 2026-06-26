# Workflow: Set up a new Flutter game project

**Goal:** Scaffold a clean, analyzer-strict Flutter project (iOS + Android) with the studio's
folder layout, lint config, and a verified first run — no premature dependencies.

## When to use
- First step of ANY new game in this skill, before scaffolding a genre template.
- Run this once per project. After it's green, hand off to the matching
  `references/game-templates` brief and the relevant `workflows/*` (e.g. `add-flame.md`,
  `pure-dart-core.md`).

## When NOT to use
- The repo already has a `pubspec.yaml` at root — you're past setup; skip to the template/feature
  workflow instead.
- You only need a pure-Dart algorithm package (no UI) — use a plain `dart create` package, not
  `flutter create`.

## Prerequisites
- Flutter SDK on PATH. Verify the toolchain first; do not assume it's installed:
  ```bash
  flutter --version
  flutter doctor
  ```
  `flutter doctor` must show the Android toolchain and (on macOS) Xcode as ✓ for the platforms you
  target. If a platform is ✗, fix it before continuing — `flutter create` will still emit folders,
  but builds for that platform will fail.
- Decide three values up front (they're hard to change later cleanly):
  - **org** — reverse-DNS, e.g. `com.studioname`. Becomes the Android applicationId prefix and iOS
    bundle id prefix. Default if omitted is `com.example` (never ship that).
  - **project name** — a valid Dart package name: lowercase, `snake_case`, no leading digit,
    not a Dart reserved word, e.g. `dot_dash_runner`. This is the directory and pubspec `name`.
  - **target platforms** — for this skill, `ios,android`. (Add `,web` only if explicitly asked;
    each extra platform is a maintenance surface.)

---

## Steps

### 1. Create the project (org, name, platforms)
Run from the directory that should contain the new project folder:

```bash
flutter create \
  --org com.studioname \
  --project-name dot_dash_runner \
  --platforms ios,android \
  --description "A small offline 2D mobile game." \
  dot_dash_runner
```

Flag notes (verified against the Flutter `create` command):
- `--org` defaults to `com.example`; always pass your own reverse-DNS org.
- `--project-name` must be a valid Dart package name; if omitted, Flutter derives it from the
  directory name, so pass it explicitly to avoid surprises.
- `--platforms` — pass the platforms you want as a comma list. Limiting to `ios,android` keeps the
  tree free of `web/`, `macos/`, `windows/`, `linux/` you'd otherwise have to maintain or delete.
- `--description` lands in `pubspec.yaml`.
- Optional `-e` / `--empty` gives a minimal `main.dart` (no demo counter, no comments). Prefer it
  for game projects — you'll replace `main.dart` immediately anyway. (`--empty` implies
  `--template=app`.)
- Do NOT pass extra packages here. `flutter create` only scaffolds; deps come later, per-feature,
  via `flutter pub add` (see step 6 and `references/package-policy`).

Then enter the project for all remaining steps:

```bash
cd dot_dash_runner
```

> All `flutter` commands below assume the project root is the working directory.

### 2. Drop in the studio `analysis_options.yaml`
Replace the generated `analysis_options.yaml` with the skill asset so the analyzer is strict from
commit #1. The include path is `package:flutter_lints/flutter.yaml` (the package's published entry
point — not `recommended.yaml`). Author it as:

```yaml
# analysis_options.yaml — studio strictness baseline (2-space indent, YAML is whitespace-sensitive)
include: package:flutter_lints/flutter.yaml

analyzer:
  language:
    strict-casts: true
    strict-inference: true
    strict-raw-types: true
  errors:
    # Treat these as build-breakers, not warnings.
    invalid_annotation_target: ignore   # noise from json_serializable, if ever used
    missing_required_param: error
    missing_return: error
  exclude:
    - build/**
    - "**/*.g.dart"
    - "**/*.freezed.dart"

linter:
  rules:
    - prefer_const_constructors
    - prefer_const_constructors_in_immutables
    - prefer_const_declarations
    - prefer_final_locals
    - prefer_final_fields
    - always_declare_return_types
    - avoid_print            # use a logger / debugPrint in game loops
    - cancel_subscriptions
    - close_sinks
    - unawaited_futures
    - use_super_parameters
```

`flutter_lints` is already a `dev_dependency` in the generated `pubspec.yaml`, so the
`include:` resolves with no extra install. If `flutter pub get` later complains it's missing, add it
with `flutter pub add dev:flutter_lints`.

> Cross-link: keep this in lockstep with `references/quality-policy` (analyzer must be 0 issues) and
> `checklists/*` quality gates.

### 3. Create the studio folder layout
Pure-Dart core stays import-clean of Flutter; UI/game/systems are separated (skill doctrine).

```bash
mkdir -p lib/models lib/systems lib/game lib/widgets assets/images assets/audio test
```

Intended responsibilities:
- `lib/models/` — **pure Dart** domain model + state machine. NO `package:flutter` import here.
  Unit-tested with `dart test`. (See `references/flutter-game-architecture`.)
- `lib/systems/` — pure-Dart game systems (spawning, scoring, collision math, RNG-driven logic).
  Take an injected `Random` for determinism (`assets/seeded_random.dart` pattern).
- `lib/game/` — Flame `FlameGame`/components OR the hybrid `GameWidget` glue. Bridges model ⇄ render.
- `lib/widgets/` — Flutter screens, HUD, menus, buttons. Presentation only.
- `assets/` — images/audio/levels. Levels ship as JSON data files, not Dart code.
- `test/` — `dart test`-style unit tests for `models`/`systems`; `flutter_test` widget tests for
  `widgets`.

Add a one-line README in each lib subfolder so the boundary is explicit and greppable:

```bash
printf 'Pure Dart only — no package:flutter import. Domain model + state machine.\n' > lib/models/README.md
printf 'Pure Dart game systems. Inject a seeded Random for determinism.\n'           > lib/systems/README.md
printf 'Flame / GameWidget glue. Bridges the pure model to rendering.\n'             > lib/game/README.md
printf 'Flutter presentation only — screens, HUD, menus.\n'                          > lib/widgets/README.md
```

### 4. Wire `pubspec.yaml` basics
Open `pubspec.yaml` and set the project-level basics. Keep `dependencies` minimal — only
`flutter` (and `cupertino_icons`, which Flutter adds). Do NOT add Flame or anything else yet.

- Confirm `name`, `description`, and `environment.sdk` (a modern null-safe constraint, e.g.
  `sdk: ^3.5.0`) match your toolchain (`flutter --version` shows the bundled Dart SDK).
- Declare the asset folders so they bundle into the app:

```yaml
flutter:
  uses-material-design: true
  assets:
    - assets/images/
    - assets/audio/
```

> Trailing slash registers the whole folder. A folder with no files at build time will error, so
> either keep a placeholder file in each declared folder or comment the line out until you add
> assets. See `references/asset-pipeline` for naming, resolution variants, and `pubspec` rules.

### 5. Add a `.gitignore` and initialize VCS
`flutter create` already writes a Flutter-aware `.gitignore` (ignores `build/`, `.dart_tool/`,
`.flutter-plugins*`, IDE files, etc.). Verify it exists and contains at least these, and append any
that are missing:

```
# Flutter / Dart
/build/
.dart_tool/
.flutter-plugins
.flutter-plugins-dependencies
.packages
pubspec.lock        # apps: commit it; reusable packages: ignore it — pick one and be consistent

# IDE / OS
.idea/
.vscode/
*.iml
.DS_Store
```

> For a shippable game app, COMMIT `pubspec.lock` (reproducible builds) — remove it from the ignore
> list. Only ignore it for a reusable library package. Then:

```bash
git init
git add -A
git commit -m "Scaffold Flutter game project (ios,android)"
```

(Skip `git init` if the project lives inside an existing repo.)

### 6. Resolve dependencies (no new ones yet)
```bash
flutter pub get
```
This must succeed with zero errors before you run. Resist adding packages here — the genre template
and feature workflows pull in Flame or others deliberately, each justified per
`references/package-policy`.

### 7. First run + clean analyzer (verification)
Prove the scaffold is healthy before writing game code:

```bash
flutter analyze        # MUST report "No issues found!"
dart format --set-exit-if-changed .   # MUST exit 0 (already 2-space formatted)
flutter test           # the generated widget_test passes (or delete it if you used --empty)
```

Then launch on a device/simulator to confirm it builds for a real target:

```bash
flutter devices                 # find an iOS simulator and/or Android emulator id
flutter run -d <device-id>      # hot-reload session; press 'q' to quit
```

Report the REAL output of `flutter analyze` / `flutter test` / `flutter run`. If you can't run here
(no device, no toolchain), say so explicitly and hand over these exact commands — do not claim a
green run you didn't see (`references/quality-policy`, skill verification doctrine).

---

## Done when
- `flutter analyze` → **No issues found!** with the strict `analysis_options.yaml` in place.
- `dart format --set-exit-if-changed .` exits 0.
- `flutter test` passes (generated test, or none if `--empty`).
- `flutter run -d <ios|android>` builds and launches at least one target (or you've documented why
  it couldn't run here, with the commands to do so).
- Tree shows `lib/{models,systems,game,widgets}/`, `assets/`, `test/`; `pubspec.yaml` declares asset
  folders; `dependencies` contains only `flutter` (+ `cupertino_icons`).
- Bundle id / applicationId carry your real `--org`, not `com.example`.

## Common pitfalls
- **Shipping `com.example`** — forgot `--org`. Changing the bundle id after the fact means editing
  `android/app/build.gradle(.kts)`, the iOS `PRODUCT_BUNDLE_IDENTIFIER` in Xcode, and namespaces;
  far cheaper to pass `--org` at create time.
- **Invalid project name** — `MyGame`, `2048`, or `class` fail Dart package-name rules. Use
  `snake_case`, no leading digit, not a reserved word.
- **Wrong include path** — using `package:flutter_lints/recommended.yaml`. The published entry point
  is `package:flutter_lints/flutter.yaml`; the wrong path makes the analyzer silently skip the rules.
- **Empty asset folder build error** — declaring `assets/audio/` in `pubspec.yaml` while it has no
  files makes `flutter run` fail. Keep a placeholder or comment the line until populated.
- **`package:flutter` creeping into `lib/models/`** — breaks pure-Dart testability and the
  architecture boundary. Keep the model importable by plain `dart test`; grep for `package:flutter`
  under `lib/models` in CI.
- **Adding deps "to be safe"** — every package is a review/size/kids-safety liability. Add only when
  a workflow calls for it, with justification (`references/package-policy`).
- **Extra platform folders** — omitting `--platforms` (or passing `web,macos,...`) scaffolds desktop
  targets you'll never maintain. Stick to `ios,android` unless asked.
- **Skipping `flutter doctor`** — a ✗ Android/Xcode toolchain doesn't block `flutter create`, so the
  break surfaces only at first build. Check the toolchain first.

## Cross-links
- `references/flutter-game-architecture` — the model/systems/game/widgets separation in depth.
- `references/package-policy` — when a dependency is justified; how to record it.
- `references/quality-policy` + `checklists/*` — the analyzer/format/test gates this workflow seeds.
- `references/asset-pipeline` — asset folders, resolution variants, JSON levels.
- `references/accessibility-child-safety` — kids-safety baseline to honor from the start (offline,
  no tracking, minimal permissions) when picking org/platforms/deps.
- Next workflows: `workflows/add-flame.md` (if motion/physics), the genre brief in
  `references/game-templates`, and `assets/{flame_game_template,flutter_game_widget_template}.dart`.
