# Add Localization And Game Copy

Use for localized menus, HUD text, tutorials, accessibility copy, store-facing in-app policy text,
and any new language. Flutter's built-in `gen_l10n` is the default; add a package only when the app
has a demonstrated requirement it cannot meet.

## Preconditions

- Read the Mini-GDD target age, supported locales, and reading-level constraints.
- Map every string to a real screen/state. Do not invent UI while translating it.
- Read `references/accessibility-child-safety.md` and `references/ui-and-animations.md`.
- Use `narrative-writer` for voice/copy and `qa-tester` for locale, semantics, and overflow checks.

## Architecture Contract

- The pure-Dart game core emits typed states/events/keys, never localized display strings.
- The Flutter layer maps those values to generated `AppLocalizations` getters.
- ARB keys are stable `lowerCamelCase`; do not use an English sentence as an identifier.
- No concatenated sentences. Use typed placeholders, ICU plural, and ICU select.
- Every interactive control gets localized `Semantics` label/value/hint alongside visible copy.
- Missing translations are a build/test finding, not a silent fallback hidden until release.

## 1. Enable Flutter Generation

Use Flutter's SDK localization package and the SDK-pinned `intl` version:

```yaml
dependencies:
  flutter_localizations:
    sdk: flutter
  intl: any

flutter:
  generate: true
```

Add `l10n.yaml` at the app root:

```yaml
arb-dir: lib/l10n
template-arb-file: app_en.arb
output-localization-file: app_localizations.dart
synthetic-package: false
nullable-getter: false
untranslated-messages-file: build/untranslated_messages.json
```

Modern Flutter generates localization source inside the app, not through the removed synthetic
`package:flutter_gen`. The output above is `lib/l10n/app_localizations.dart`. Keep generated output
out of hand-edited source unless the project deliberately checks generated files in; follow the
repository's existing generation policy.

## 2. Create The Template ARB

`lib/l10n/app_en.arb`:

```json
{
  "@@locale": "en",
  "playButtonLabel": "Play",
  "@playButtonLabel": {
    "description": "Primary action on the main menu"
  },
  "scoreValue": "Score: {score}",
  "@scoreValue": {
    "description": "Current score in the HUD",
    "placeholders": {
      "score": { "type": "int" }
    }
  },
  "remainingMoves": "{count, plural, =0{No moves left} =1{1 move left} other{{count} moves left}}",
  "@remainingMoves": {
    "description": "Moves remaining in the current level",
    "placeholders": {
      "count": { "type": "int" }
    }
  }
}
```

Rules:

- Add `@key.description` for every user-facing key.
- Declare placeholder type and meaning; use `int`, `double`, `String`, or `DateTime` intentionally.
- Use plural/select grammar instead of branching on English word order in Dart.
- Keep encouragement warm and non-shaming. Avoid urgency, FOMO, purchase pressure, and text that a
  young player must read to understand the core interaction.
- Keep asset names, debug labels, analytics identifiers, and internal enum names out of ARB copy.

## 3. Wire MaterialApp

```dart
import 'l10n/app_localizations.dart';

MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  home: const GameScreen(),
)
```

At the widget edge:

```dart
final strings = AppLocalizations.of(context);

Semantics(
  button: true,
  label: strings.playButtonLabel,
  child: Text(strings.playButtonLabel),
)
```

Do not pass `BuildContext` or `AppLocalizations` into models/systems. For domain values, use an
exhaustive UI mapping:

```dart
String phaseLabel(AppLocalizations strings, GamePhase phase) => switch (phase) {
  GamePhase.menu => strings.mainMenuTitle,
  GamePhase.playing => strings.gameInProgress,
  GamePhase.paused => strings.gamePaused,
  GamePhase.won => strings.levelComplete,
  GamePhase.lost => strings.tryAgain,
};
```

## 4. Layout And Game UX

- Test long translations, not only English. Buttons may wrap or expand; they must not clip the HUD
  or cover the playfield.
- Test text scale 1.0 and 2.0, phone/tablet, portrait/landscape, and RTL when an RTL locale ships.
- Keep icon-only controls understandable through localized Semantics and tooltips.
- Localize pause, resume, retry, settings, mute, loading, empty, error, win, and no-fail feedback.
- Never draw essential localized text directly into a Flame canvas. Use Flutter overlays/HUD where
  text scaling, directionality, and Semantics work correctly.

## 5. Generate And Test

Run only when Flutter is available:

```bash
flutter gen-l10n
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test
```

Add widget tests that:

- pump at least the template locale and one non-English locale;
- find critical labels through generated strings or Semantics;
- render at 200% text scale without exceptions/overflow;
- verify all declared supported locales load;
- verify each state/event maps exhaustively to copy;
- inspect `build/untranslated_messages.json` and fail release when required translations are absent.

Golden tests may cover representative long/RTL layouts, but assertions on behavior and Semantics
remain primary because text rendering varies by platform and font.

## Definition Of Done

- [ ] `gen_l10n` is configured with one canonical template ARB.
- [ ] All user-facing strings and Semantics copy come from generated localizations.
- [ ] The pure-Dart core contains no display copy or Flutter localization imports.
- [ ] Placeholders, plurals, and selects are typed and documented.
- [ ] Long text, 200% scaling, orientation, and every supported locale are tested.
- [ ] Missing required translations are visible in CI/release evidence.
- [ ] Commands actually run are reported with real output; unavailable toolchains are marked unverified.
