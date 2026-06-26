# Mini Game Design Document — <GAME NAME>

> One page. The contract for the MVP. Fill every section; keep it lean. Everything below the
> cut-line is "later."

## 1. Concept
- **One-liner:** <what the game is in a sentence>
- **Genre / template:** <coloring-shapes | simple-platformer | drag-and-drop-puzzle | memory-cards | shape-matching | endless-runner-lite | tap-reaction | quiz | educational-kids | ui-heavy>
- **Audience & age:** <e.g. ages 4–8>
- **Platforms:** iOS · iPadOS · Android (one Flutter codebase) · Orientation: portrait / landscape / both
- **Implementation mode:** Flutter-widgets-only / Flame / hybrid (`GameWidget` + overlays)
  — and one line of *why* (see `references/flutter-game-architecture.md`).

## 2. Core loop
<The 1–3 step loop the player repeats. e.g. "Tap a region → it fills → repeat until done.">

## 3. Controls / core verb
- **Primary verb:** <tap | drag | swipe | move>
- **Inputs:** <gestures/buttons and what they do>

## 4. Win / lose / progression
- **Failure model:** no-fail / score-chase / win-lose with retries
- **Win condition:** <…>   **Lose condition (if any):** <…>
- **Progression:** <levels, difficulty ramp, unlocks — keep MVP small>

## 5. Art direction
- **Style:** bright, high-contrast placeholder vector art (no copyrighted assets) — `CustomPainter` / `flutter_svg`
- **Palette:** <6–8 friendly colors>   **Key shapes / entities:** <player, tiles, targets…>

## 6. Audio
- **SFX / music:** <optional, muteable; conservative default>

## 7. Accessibility
- `Semantics` (label/value/button) on all controls · text scaling · reduce motion (`MediaQuery.disableAnimations`)
- Playable without reading text and without relying on color alone · 48dp touch targets · TalkBack + VoiceOver

## 8. Child safety & privacy (both stores)
- No tracking / analytics / ads / AdvertisingId / external links / accounts; offline-first; local progress only.
- Must satisfy **Apple Kids Category** AND **Google Play Families**. Sensitive actions behind a parental gate.

## 9. Architecture sketch
- **Pure Dart core (no `package:flutter`):** <key model types + state machine: menu → playing → paused → won/lost>
- **Systems:** <input, score, spawn, collision, audio, save — as needed>
- **State mgmt (shell):** <ValueNotifier / Provider / Riverpod / Bloc — justify if not the first>
- **Folders:** `lib/models/ lib/systems/ lib/game/ lib/widgets/ assets/ test/`
- **Dependencies (justified per `package-policy.md`):** <list or "Flutter SDK only">

## 10. Scope
- **In (MVP):** <smallest set that delivers the core loop end-to-end>
- **Cut-line (later):** <everything deferred>

## 11. Success criteria
- <Measurable, e.g. "Player completes one level start→finish at 60fps with TalkBack on.">

## 12. Assumptions & risks
- **Assumptions:** <documented defaults you applied>
- **Risks:** <open questions, store/compliance items — no guarantees>
