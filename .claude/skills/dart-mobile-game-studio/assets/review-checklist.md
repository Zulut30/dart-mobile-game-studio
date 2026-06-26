# Review checklist — <GAME NAME>

Run before handoff. Check each box or note why it doesn't apply. This is a quality gate, **not** a
guarantee of App Store / Google Play approval — produce risks, not promises. Run
`scripts/dart-doctor.py <project>` first; the `checklists/` directory has per-area deep lists.

## Architecture & code quality
- [ ] Game rules live in **pure Dart** (`lib/models/`, `lib/systems/`) with **no `package:flutter`
      import**, and are unit-tested with `dart test`.
- [ ] Clear UI / business / game-logic separation; widgets and Flame components are thin.
- [ ] Explicit state machine: menu → playing → paused → win/lose → menu (enum / sealed class).
- [ ] Mode (Flutter-widgets / Flame / hybrid) chosen and justified; not mixed in one screen.
- [ ] `dt` clamped; movement frame-rate independent; seeded `Random` injected (deterministic tests).
- [ ] `flutter analyze` clean, `dart format` applied; null-safe; `const` where possible; everything disposed.
- [ ] Small, single-purpose files; levels are JSON data (validated vs `level-schema-template.json`).
- [ ] Dependencies justified per `package-policy.md`; no stray deps.

## Accessibility
- [ ] `Semantics` (label/value/button) on every interactive control; decorative hidden.
- [ ] Playable without reading text and without relying on color alone.
- [ ] Honors text scaling (`MediaQuery.textScaler`) and reduce motion (`MediaQuery.disableAnimations`).
- [ ] TalkBack + VoiceOver can navigate and play; 48dp touch targets.

## Child safety & privacy (both stores)
- [ ] No third-party analytics, tracking, ads, or AdvertisingId (IDFA/GAID); no ATT prompt for kids.
- [ ] No external links / web views / accounts in a child-facing flow; offline-first.
- [ ] Collects no personal data; stores only local progress/settings.
- [ ] Minimal permissions (no Android `INTERNET` if offline; iOS usage strings only where used).
- [ ] Satisfies **Apple Kids Category** and **Google Play Families**; sensitive actions behind a parental gate.
- [ ] No dark patterns; any IAP behind a parental gate (general builds only — see `monetization-policy.md`).

## Performance
- [ ] Stable 60 fps on a mid/low device; no jank in transitions; no work in `build()`.
- [ ] Scoped rebuilds (no rebuild-the-world `setState`); `const` + `RepaintBoundary` on hot subtrees.
- [ ] Images right-sized; Flame component count bounded + pooling for spawners; no leaks.
- [ ] Verified with DevTools (timeline/memory), not assumed.

## Functionality / QA
- [ ] Core loop completes start→finish; win and (if any) lose paths work; no soft-locks.
- [ ] iPhone, iPad, and Android phone + tablet layouts correct; both orientations as designed; safe areas respected.
- [ ] Backgrounding mid-game preserves state; no `dt` spike; audio pauses/resumes.
- [ ] Restart/replay works; persistence survives relaunch.
- [ ] No debug `print`, placeholder copy, or TODO in the play path.

## Build & tests
- [ ] `dart analyze` / `flutter analyze` clean; `dart test` + `flutter test` pass — and you ran them.
- [ ] Release build succeeds (`flutter build appbundle` / `flutter build ipa`).
- [ ] If not built/tested here, that is stated explicitly with the commands to run.

## Handoff completeness
- [ ] Changed files listed with one-line purpose each.
- [ ] Commands run + real output (or explicit "not run here").
- [ ] Assumptions documented; open risks listed; next steps proposed. No compliance guarantees.
