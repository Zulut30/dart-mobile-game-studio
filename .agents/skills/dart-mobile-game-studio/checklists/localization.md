# Localization checklist

A tick-list a reviewer/agent runs over a game's **localization** (`pubspec.yaml`, `l10n.yaml`,
`lib/l10n/*.arb`, the render layer that consumes `AppLocalizations`). Enforces the policies in
`references/codegen-and-boilerplate.md` (§"Localization: gen-l10n"), `references/ui-and-animations.md`
(§"Responsive layout", text expansion), `references/dart/flutter-widgets-mastery.md` (`textScaler`,
Semantics), and the kids-safety doctrine (Apple Kids + Google Play Families ship across many
locales); it does not re-explain them. Each box is verifiable by reading code, `grep`, or one
command — fail any → fix before handoff. Mark a box N/A only with a reason (e.g. "single-locale MVP,
infra still wired"). APIs below are verified against the official Flutter i18n guide and the
`dart-lang/i18n` `intl` docs: `flutter: generate: true`, `l10n.yaml`, `AppLocalizations`
(`.delegate`/`.localizationsDelegates`/`.supportedLocales`), the four `Global*Localizations.delegate`s,
ICU `plural`/`select` in ARB, `@key` metadata (`description`/`placeholders`/`type`/`format`/`example`),
`NumberFormat`/`DateFormat` (locale-aware), `Directionality`, `EdgeInsetsDirectional`,
`AlignmentDirectional`, and `MediaQuery.textScalerOf`.

## gen-l10n wiring (intl + ARB, NOT build_runner)
- [ ] `pubspec.yaml` declares `flutter_localizations: { sdk: flutter }` and `intl`, and sets
      `flutter: generate: true` (turns on gen-l10n) — verified by reading the file.
- [ ] An `l10n.yaml` exists at the project root with `arb-dir` (e.g. `lib/l10n`),
      `template-arb-file` (e.g. `app_en.arb`), and `output-localization-file` (e.g.
      `app_localizations.dart`); the generated class name is left default `AppLocalizations` or set via
      `output-class`.
- [ ] Localization is **not** wired through `build_runner` — there is no localization builder in
      `build.yaml`; `flutter gen-l10n` (or a plain `flutter run`/`build`) regenerates `AppLocalizations`.
- [ ] The generated `app_localizations.dart` (under `.dart_tool/` by default) is **not** hand-edited
      and its commit status matches the repo's codegen policy (gen-l10n is effectively always rebuilt
      in CI; do not treat it like a checked-in `*.g.dart`).
- [ ] `MaterialApp`/`CupertinoApp` passes `localizationsDelegates: AppLocalizations.localizationsDelegates`
      and `supportedLocales: AppLocalizations.supportedLocales` — so the four delegates
      (`AppLocalizations.delegate` + `GlobalMaterialLocalizations`/`GlobalWidgetsLocalizations`/
      `GlobalCupertinoLocalizations`) are all installed and built-in widgets localize too.
- [ ] `required-resource-attributes` is on (default) or every message carries `@key` metadata, so a
      missing placeholder/description fails generation rather than shipping silently.
- [ ] `flutter gen-l10n` runs clean (no warnings) and `untranslated-messages-file` (if configured)
      shows no gaps for the locales claimed as shipped.

## No hardcoded user-facing strings
- [ ] No user-visible string literal sits in a widget: `grep -rnE "Text\(\s*['\"]" lib/` (and
      `SnackBar`/`AlertDialog`/`Tooltip`/`semanticLabel`/`AppBar(title:`) returns only `AppLocalizations`
      calls or documented exceptions — never a bare `Text('Score')`.
- [ ] App/window title is localized via `onGenerateTitle: (context) => AppLocalizations.of(context)!.appTitle`,
      not a constant `title:` string.
- [ ] The **pure model never holds display text**: `grep -rnE "['\"][A-Za-z].* [A-Za-z]" lib/models lib/systems`
      surfaces no sentence-like UI copy — the core emits values/enums/ids; the render layer maps them to
      `AppLocalizations` (model stays Flutter-free).
- [ ] Enum/sealed states (win/lose, difficulty, level names) are localized at the edge via a
      `switch` over the value, not by `toString()`-ing the enum or storing a label string in data.
- [ ] Level JSON / save data store **stable ids**, not human text; any name shown to the player is
      resolved through an ARB key, so adding a locale needs no data-file edit.
- [ ] Truly non-translatable literals (debug `log`, asset paths, route names, analytics-free keys)
      are the only string literals left — each is clearly not user-facing.

## ARB hygiene & parity
- [ ] Every ARB key in the template (`app_en.arb`) exists in **every** shipped locale file
      (`app_es.arb`, `app_ar.arb`, …) — no missing translations falling back silently to English.
- [ ] No locale file has **extra** keys absent from the template (stale/renamed strings) — keys are
      identical sets across all ARBs.
- [ ] Every parameterized/`plural`/`select` message has `@key` metadata with a `description` and a
      `placeholders` block declaring each placeholder's `type` (`String`/`int`/`num`/`DateTime`); a
      one-word `description` that fails to disambiguate for a translator is fixed.
- [ ] Placeholders carry an `example` where the value's shape matters (so translators see real
      context, not just a name).
- [ ] Literal `{`/`}` braces and apostrophe-heavy locales are handled: `use-escaping: true` is set and
      literals are single-quoted (`'{'`), or the strings provably contain no stray braces.
- [ ] No string concatenation builds a sentence from fragments in Dart (`loc.you + ' ' + loc.won`):
      whole sentences live in one ARB message with placeholders, so word order can change per language.

## Pluralization (ICU plural, not `if (n == 1)`)
- [ ] Every count-dependent string uses ICU `plural` in the ARB
      (`{count, plural, =0{…} =1{…} other{{count} …}}`) with a `num`/`int` placeholder — there is **no**
      hand-rolled `count == 1 ? singular : plural` ternary in Dart.
- [ ] Each `plural` message provides the **required** `other` branch (and `=0`/`=1` where the copy
      differs); translators can add `few`/`many`/`two`/`zero` per their language without a code change.
- [ ] `select` (not a Dart `switch` on a translated label) handles gendered/categorical variants, with
      an `other` fallback.
- [ ] The count fed to a plural is the raw `num`/`int` from the model, not a pre-formatted string — so
      the ICU selector and the displayed number both localize.

## Locale-aware number / date / time formatting
- [ ] No `'$number'`/`number.toString()`/`'${(p*100).round()}%'`/`'$m:$s'` for a user-facing number:
      formatting goes through `intl` (`NumberFormat`/`DateFormat`) or an ARB placeholder `format`
      (`compact`, `decimalPattern`, `percentPattern`, `currency`/`simpleCurrency`, `yMd`, `jm`) so
      grouping separators, decimal marks, percent and time formats follow the locale.
- [ ] Formatters are **locale-aware, not default-locale**: either the ARB `format` key (which uses the
      active locale) is used, or any direct `intl` formatter is built with the current locale
      (`NumberFormat.decimalPattern(Localizations.localeOf(context).toString())` /
      `DateFormat.yMd(locale)`) — never a bare `NumberFormat()` that silently uses `Intl.defaultLocale`.
- [ ] If `intl` `DateFormat` is used directly (outside ARB) for non-`en` locales,
      `initializeDateFormatting(locale)` is awaited once at startup before the first format call.
- [ ] Score/timer/currency formatters are built **once** (cached field), not re-created per frame in
      `build`/`update` (allocation + per-frame cost — consistent with `performance-checklist.md`).
- [ ] Durations and clocks shown to the player use a locale-aware format (12/24-hour from `jm`/`Hm`),
      not a hand-built `HH:MM` assumed-Western string.

## RTL support (Arabic / Hebrew / Persian)
- [ ] At least one RTL locale is in `supportedLocales` (or the app is verified under
      `Directionality(textDirection: TextDirection.rtl, …)` / device RTL) — UI is exercised mirrored,
      not assumed.
- [ ] Layout uses **directional** insets/alignment everywhere chrome has sides: `EdgeInsetsDirectional`
      (`start`/`end`), `AlignmentDirectional`, `TextAlign.start`/`.end`, `PositionedDirectional` —
      `grep -rnE "EdgeInsets\.only\(.*(left|right)|Alignment\.centerLeft|TextAlign\.(left|right)" lib/`
      surfaces no hard left/right in flowing UI (intentional, art-anchored exceptions noted).
- [ ] Directional icons (back/forward/next arrows, chevrons) mirror in RTL — they use the
      auto-mirroring built-ins (`Icons.arrow_back`/`Icons.chevron_right`, `automaticallyImplyLeading`),
      or wrap a custom glyph so it flips with `Directionality.of(context)`.
- [ ] Embedded LTR runs inside RTL text (scores, level numbers, latin proper nouns) render correctly —
      values come from locale-aware formatters / placeholders, not glued raw into the sentence.
- [ ] **Gameplay geometry that is semantically directional vs. physical is distinguished**: the game
      board/canvas/`CustomPainter` and Flame world keep their own coordinate space (not mirrored by
      Directionality), while reading-order chrome (HUD rows, menus, dialog button order) does follow
      RTL — verified by eye in an RTL locale.
- [ ] No raw bytes/`Bidi`-unsafe concatenation reverses punctuation; mixed-direction labels are built
      from ARB messages, letting the engine apply the Unicode bidi algorithm.

## Text expansion in layouts (translations are longer)
- [ ] Buttons, chips, HUD labels, and dialog titles are sized from **content/constraints**, not fixed
      widths — a string ~30–40% longer (German/French/Finnish) does not overflow
      ("yellow-and-black stripes"); verified by reading a long-locale ARB or a pseudo-locale run.
- [ ] Long labels degrade gracefully (`maxLines` + `TextOverflow.ellipsis`, `Flexible`/`Expanded`,
      `FittedBox`, or wrapping) rather than clipping or pushing siblings off-screen.
- [ ] Text honors `MediaQuery.textScalerOf(context)` (not a locked font size) **and** the longer
      translation simultaneously — the worst case (largest Dynamic Type × longest locale) still fits or
      scrolls, checked on a small phone.
- [ ] No layout assumes a string's pixel width (no `SizedBox(width:)` sized to fit one language's
      label); width comes from the laid-out text or a fraction of the parent.
- [ ] A pseudo-localization or longest-shipped-locale pass was run over every screen (menu, HUD, pause,
      win/lose, settings, dialogs) with no overflow or truncated meaning.

## Accessible labels are localized too
- [ ] Every `Semantics(label:/value:/hint:)`, `semanticLabel:`, and `tooltip:` string is an
      `AppLocalizations` value — `grep -rnE "(semanticLabel|tooltip|label):\s*['\"]" lib/` shows no
      hardcoded a11y copy (the screen-reader text is as translated as the visible text).
- [ ] Painted/`GestureDetector`-only controls (per `flutter-ui-quality.md`) get a **localized**
      `Semantics.label`/`value`; no silent or English-only painted button.
- [ ] `liveRegion` announcements (win/lose, score milestone) speak a localized string.
- [ ] Number/date content exposed to VoiceOver/TalkBack is the locale-aware formatted value (or an
      explicit spoken-friendly `Semantics.value`), not a raw `toString()` that the reader mispronounces.
- [ ] Image/icon `semanticLabel`s and any `MergeSemantics` composite labels are localized; decorative
      art stays `ExcludeSemantics` (no untranslated noise).

## Format & analyzer gate
- [ ] ARB files are valid JSON and `flutter gen-l10n` produces no errors/warnings; the build that
      includes gen-l10n succeeds.
- [ ] `dart format --output=none --set-exit-if-changed lib/` is clean and
      `dart analyze --fatal-infos --fatal-warnings` is zero on the render-layer code that consumes
      `AppLocalizations` (the generated file is excluded from lint, not from build).
