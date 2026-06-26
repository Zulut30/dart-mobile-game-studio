# Package selection policy

Dependencies are liabilities. Every pub.dev package is code you don't control, a supply-chain and
maintenance risk, app-size cost, and a potential blocker on iOS/iPadOS/Android. This policy is the
gate: an agent must apply it **before** adding any dependency and **document** the decision.

## The decision order (stop at the first that fits)
1. **Standard Flutter / Dart SDK API.** If the task is solved cleanly with the framework
   (`CustomPainter`, `AnimationController`, `Draggable`, `shared_preferences`-free file I/O via
   `dart:io`, `dart:math`, `Tween`, `Navigator`/`go_router`-free `Navigator 1.0`), **add nothing.**
   Most simple-game needs (drawing, gestures, animation, layout, JSON) need no extra package.
2. **Official Flutter/Dart packages** (flutter.dev / `flutter/packages`, `dart-lang/*`,
   `flutter/core-packages`). Prefer these for anything first-party: `go_router`, `shared_preferences`,
   `path_provider`, `flutter_localizations`/`intl`, `google_mobile_ads`, `in_app_purchase`,
   `games_services` (community-maintained but standard), `flutter_lints`.
3. **The game layer: Flame** (`flame-engine/*`) when the architecture decision calls for an engine
   (see `flutter-flame-patterns.md`): `flame`, `flame_audio`, `flame_forge2d`, `flame_test`.
4. **Mature community packages** — only when 1–3 don't cover it. "Mature" = active maintenance,
   high pub points + popularity, null-safe, sound on iOS **and** Android, a real changelog, and not a
   thin wrapper you could write in 30 lines.
5. **Write it yourself** if it's small, central to gameplay, or the only candidates are unmaintained.

## Mandatory justification (record for every added dependency)
For each package the agent adds, write a short note (in the PR/handoff and ideally `pubspec.yaml`
comments):
- **Why** it's needed and which decision-order step justified it.
- **Official alternative?** name it and why it wasn't enough.
- **Maintenance risk** — last release, maintainer, open-issue health, pub points/popularity.
- **App-size impact** — does it pull native code / large transitive deps?
- **Platform fit** — confirmed working on **iOS, iPadOS, and Android** (and not relying on a
  desktop/web-only path). Note any platform setup (Info.plist keys, AndroidManifest permissions).
- **Kids impact** — does it collect data, show ads, or use AdvertisingId? If so it is **banned from a
  kids build** (see `monetization-policy.md`, `accessibility-child-safety.md`).

## Hard rules
- **No dependency without this policy applied.** A reviewer (`code-reviewer`/`code-auditor`) rejects
  any new `pubspec.yaml` entry lacking the justification.
- **Pin sensibly.** Use caret ranges (`^x.y.z`); commit `pubspec.lock` for apps; run
  `flutter pub outdated` periodically; never depend on `any`.
- **No `git:`/`path:` deps in shipping apps** unless unavoidable and documented.
- **Audit transitive bloat.** Prefer one package that does the job over three overlapping ones.
- **Codegen deps are dev-only.** `build_runner`, `json_serializable`, `freezed`, `auto_route` go
  under `dev_dependencies` (the generated `*.g.dart`/`*.freezed.dart` are committed or built in CI);
  see the codegen workflow.
- **Kids builds:** no ads/analytics/attribution/tracking SDKs, period. No `google_mobile_ads`, no
  Firebase Analytics, no Facebook/AppsFlyer/Adjust, no AdvertisingId access.

## Common, vetted choices (general-audience games)
| Need | First choice | Notes |
|---|---|---|
| Routing | `go_router` (official) | declarative; or Navigator 1.0 for tiny apps |
| Local settings/save | `shared_preferences` (official) / a `Codable`-style JSON file via `path_provider` | tiny scalars vs a save blob |
| State (shell) | SDK `ValueNotifier`/`ChangeNotifier`; then `provider`/`riverpod`/`flutter_bloc` | don't add one reflexively |
| Game engine | `flame` (+ `flame_forge2d`, `flame_audio`) | only when motion/physics needs it |
| Audio (no Flame) | `audioplayers` (official-adjacent) | mute toggle required |
| Ads (general only) | `google_mobile_ads` (official) | **never** in a kids build |
| IAP/subscriptions | `in_app_purchase` (official) | parental gate; StoreKit/Play Billing |
| Achievements/leaderboards | `games_services` | optional; off in the kids flow |
| Charts/stats | `fl_chart` | stats screens, not the game loop |
| SVG vector art | `flutter_svg` | or pure `CustomPainter` |
| E2E tests | `patrol` (dev) | native dialogs, permissions, lifecycle |

When a need isn't here, run the decision order and justify the pick. **Default to fewer deps.**
