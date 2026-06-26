# Accessibility & child safety

Two requirements, not extras: make the game usable by everyone, and make it safe and private for
children on **both** stores (Apple Kids Category **and** Google Play Families / Designed for
Families). Build these in from the start — retrofitting accessibility and stripping trackers later
is far more work.

Key structural fact for Flame games: **the Flame canvas is a single opaque `RenderObject`.**
Screen readers (TalkBack / VoiceOver) cannot see `Component`s you draw on it. Accessibility lives
in the **Flutter widget tree** — wrap the `GameWidget`, and put menus / HUD / buttons in
`overlayBuilderMap` overlays or a surrounding `Stack` so they carry real `Semantics`. Pure
Flutter-widget games (CustomPainter + gestures) get semantics by wrapping the painted regions.
Either way, **keep the game state in the pure-Dart core** and drive the semantics layer from it.

---

## Part 1 — Accessibility (Flutter APIs)

### Semantics: label / value / button / hidden
Every interactive element needs a `Semantics` annotation. Use `label` for what it is, `value` for
its current state, and the role flags (`button`, `checked`, `enabled`) for how it behaves.

```dart
import 'package:flutter/material.dart';

// A memory/matching card rendered as a Flutter widget.
Semantics(
  label: 'Card',
  value: card.isFaceUp ? card.symbolName : 'face down',
  button: true,
  enabled: !card.isMatched,
  onTap: onFlip, // exposes a screen-reader "activate" action
  child: ExcludeSemantics(
    // The painted art beneath is decorative; its semantics come from above.
    child: CustomPaint(painter: CardPainter(card)),
  ),
);
```

- `label` — stable identity ("Card", "Red crayon", "Tile 3").
- `value` — current state that changes ("face down", "selected", "filled").
- `button: true` — announces it as actionable; pair with `onTap` so screen-reader users can
  activate it without the visual gesture.
- `enabled: false` — announces "dimmed/disabled"; do not just gray it out visually.
- `hidden: true` (or `ExcludeSemantics`) — removes purely decorative nodes from the tree.

### MergeSemantics / ExcludeSemantics
- **`MergeSemantics`** — collapse a cluster of child nodes into one focusable announcement, so a
  screen reader reads "Level 3, 2 of 5 stars" as a single stop instead of four.
- **`ExcludeSemantics`** — drop decorative descendants (background art, particle layers, score
  digits already summarized by a parent label) so they do not clutter the focus order.

```dart
MergeSemantics(
  child: Row(
    children: [
      const Icon(Icons.star, semanticLabel: 'star'),
      Text('Level $level'),
      Text('$earned of $total'),
    ],
  ),
);
```

For a Flame game, expose the live HUD (score, lives, timer) as an overlay built from the core
state, and wrap it so TalkBack/VoiceOver can read it — the canvas-drawn version is invisible to AT.

### Announcing state changes (live regions)
When something changes off-focus — a match is made, the level is won, the timer hits zero — push an
explicit announcement. Drive this from the **pure-Dart core's** state transitions so it works in
both rendering modes.

```dart
import 'package:flutter/semantics.dart';

SemanticsService.announce(
  'Match found! 3 pairs left.',
  Directionality.of(context),
  assertiveness: Assertiveness.polite, // .assertive interrupts; use sparingly
);
```

Exact signature (verified on the **stable** channel):
`SemanticsService.announce(String message, TextDirection textDirection, {Assertiveness assertiveness = Assertiveness.polite}) → Future<void>`.
Note: on Flutter `main`/future stable, `SemanticsService.announce` is being **deprecated** in favor
of a `Semantics(liveRegion: true)` widget (and `SemanticsProperties`-driven announcements) — prefer
the `liveRegion` approach for new code and treat `announce` as the stable-channel fallback.
Alternatively, mark a small status widget with `Semantics(liveRegion: true, label: status)` and
update its label; AT re-reads it on change.

### Text scaling — `MediaQuery.textScaler`
Use `TextScaler` (the modern replacement for the deprecated `textScaleFactor`). Read it with the
attribute-specific accessor so widgets only rebuild when it changes:

```dart
final TextScaler scaler = MediaQuery.textScalerOf(context);
```

- Let normal Flutter `Text` scale automatically — **never** hard-code unscalable pixel font sizes
  for readable UI text.
- For text **painted on the Flame canvas** (e.g. Flame's `TextPaint`), scaling is not automatic.
  Read the scaler and apply it yourself so HUD/score text grows with the OS setting:
  ```dart
  final base = 18.0;
  final size = MediaQuery.textScalerOf(context).scale(base);
  ```
- If extreme scaling would break a fixed game board, **clamp** rather than ignore:
  ```dart
  final scaler = MediaQuery.textScalerOf(context)
      .clamp(minScaleFactor: 1.0, maxScaleFactor: 1.6);
  ```
  Clamp is a last resort for genuinely fixed layouts — prefer a layout that reflows. Verify at the
  largest accessibility sizes; nothing critical may truncate or overlap.
- Also honor `MediaQuery.boldTextOf(context)` for weight and `MediaQuery.highContrastOf(context)`
  for stronger color schemes.

### Reduce motion — `MediaQuery.disableAnimations`
Respect the OS "reduce motion" setting. Read it once and branch animation paths; gate this through
the core so both Flame and widget renderers obey it.

```dart
final bool reduceMotion = MediaQuery.disableAnimationsOf(context);
// Flutter side:
final duration = reduceMotion ? Duration.zero : const Duration(milliseconds: 300);
```

In a `FlameGame`, read it where you build the `GameWidget` and pass a flag into the game; in
`update(double dt)` swap large parallax / screen-shake / confetti for a quiet fade or an instant
state change. Never make motion the only feedback for an event.

### TalkBack (Android) + VoiceOver (iOS)
The same `Semantics` tree drives both. Test on each:
- **Logical focus order.** Default order follows the widget tree / reading direction; fix odd
  orders with `Semantics(sortKey: OrdinalSortKey(n))` rather than reordering visuals.
- **Everything reachable & operable.** Swipe through every control; confirm each announces a
  sensible label + value and that `onTap` actions fire.
- **No traps, no silent controls.** A focusable element with no label is a bug.
- **Flame caveat:** because the canvas is opaque, a screen-reader user navigates your **overlays**,
  not the drawn scene. Make sure the playable actions exist as accessible overlay controls, or the
  game is unplayable with AT on.

### Touch targets — 48 dp minimum
Material guidance is a **48×48 dp** minimum interactive area (≈ Apple's 44 pt). For young children,
go larger (56–72 dp) with generous spacing to prevent mis-taps. The *visual* art can be smaller
than the *hit* area — pad the gesture region:

```dart
GestureDetector(
  behavior: HitTestBehavior.opaque,
  onTap: onTap,
  child: const SizedBox(width: 56, height: 56, child: Center(child: Icon(Icons.brush))),
);
```

For Flame, size tappable `Component`s (or their hitboxes) to at least 48 logical px and keep
spacing between adjacent targets.

### Contrast & not-color-alone
- **Contrast.** Aim WCAG AA: **4.5:1** for normal text, **3:1** for large text and meaningful
  graphics/icons. Don't place pale text on busy art.
- **Never encode meaning in color alone** (critical for color-blind users and matching games).
  Pair every color with a **shape, icon, label, or pattern** — e.g. a red circle *and* a square
  blue tile, a "matched" checkmark in addition to a green tint.
- Offer a relaxed / **no-timer** option: timing-only challenges exclude players who need more time.
- Provide a **visual** equivalent for every essential audio cue (and a caption/label for any
  spoken instruction).

---

## Part 2 — Child safety & privacy (Apple Kids **and** Google Play Families)

Default to the strictest, simplest posture. The rules below satisfy the union of Apple's Kids
Category, Google Play's **Families / Designed for Families** program, and **COPPA / GDPR-K**.

### Hard rules (do all of these)
- **No tracking, no analytics, no ads.** No third-party SDKs that phone home; no behavioral or
  targeted advertising of any kind in the child experience.
- **No advertising identifiers — at all.** Do **not** read or transmit **IDFA** (iOS) or
  **GAID / Advertising ID** (Android), and don't pull in any SDK that does. Under Google Play's
  Families policy, apps targeting children **must not** transmit the Advertising ID or Android ID;
  prefer no ID, and never a persistent device identifier.
- **No accounts / no login** in the kids flow. No sign-in walls, no social login, no profiles.
- **No personal data collection.** No names, emails, location, contacts, photos, microphone, or
  device IDs. Store only **local** game progress/settings (e.g. `shared_preferences` or a local
  file) — on-device, not synced to a server.
- **No external links** out of the app — no `url_launcher` to arbitrary URLs, no in-app browser to
  the open web, no "rate us" / social-share deep links from the child-facing UI.
- **No dark patterns.** No fake urgency, nagging, manipulative IAP, loot-box pressure, or
  "tap to continue" that secretly triggers a purchase.
- **No IAP or purchase links in the child flow.** If monetization exists at all, it sits behind a
  parental gate (and review both stores' commerce rules first).
- **Minimal permissions.** Request nothing you don't strictly need. No camera/mic/location/contacts
  unless a core mechanic requires it *and* a parent enables it.

### Offline-first — and prove it on Android
Design the game to need no network. On **Android**, if the app is genuinely offline, **omit the
`INTERNET` permission entirely** so the OS cannot let it reach the network — a strong, auditable
"no data leaves the device" signal:

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<!-- Do NOT add: <uses-permission android:name="android.permission.INTERNET" /> -->
```

(Note: debug/profile builds inject `INTERNET` via the debug manifest for hot-reload — that's the
toolchain, not your release. Verify the **release** merged manifest.) On **iOS** there is no
equivalent permission to drop; enforce offline-by-design and add no networking code. Bundle all
assets and **level data as JSON** shipped in the app — no remote config, no CDN fetches.

### Parental gate
Gate anything that leaves the play space (settings that link out, any purchase, any external URL,
"more apps"). Use a challenge a young child can't pass by accident and that is **not** a
mini-game — both stores expect a real gate, e.g. a typed multi-digit answer or
spelled-out number entry, with no hint that a child could brute-force.

```dart
// Pure-Dart gate logic — unit-testable with `dart test`, no Flutter import.
class ParentalGate {
  ParentalGate(this._a, this._b);
  final int _a;
  final int _b;
  // "What is 7 x 8?" — typed digits, not tappable choices.
  bool verify(String input) => int.tryParse(input.trim()) == _a * _b;
}
```

Keep the gate's logic in the core; the widget layer only renders it and routes the sensitive action
on success. Re-gate each sensitive action — never leave the gate "unlocked" for the session.

### What the manifests / config should show
- **Android:** no `INTERNET`, no `ACCESS_*_LOCATION`, no `CAMERA`/`RECORD_AUDIO`/`READ_CONTACTS`
  unless a parent-enabled core feature needs it; no Advertising-ID metadata; complete the Play
  **Data safety** form as "no data collected / no data shared."
- **iOS:** no ad/tracking SDKs, so **no `NSUserTrackingUsageDescription`** / no ATT prompt;
  minimal `Info.plist` usage strings; an `App Privacy` ("nutrition label") declaration of
  **no data collected**.

---

## No guarantees
Following this reference helps you **avoid common violations**, but it **cannot guarantee** approval
in Apple's Kids Category or Google Play's Families program, nor legal compliance with COPPA/GDPR-K
or other laws. Store policies and laws change. Deliver a **checklist and a risk list**, recommend
the user review the **current** App Store Review Guidelines, Google Play Families policy, and
applicable law, and consult qualified legal counsel.

---

## Quick self-check
Accessibility:
- [ ] Every interactive control has a `Semantics` label/value and a role (`button`/`enabled`), and
      Flame controls are exposed as accessible **overlays**, not canvas-only.
- [ ] Decorative nodes use `ExcludeSemantics`/`hidden`; related clusters use `MergeSemantics`.
- [ ] State changes announced via `SemanticsService.announce` or a `liveRegion`.
- [ ] Honors `MediaQuery.textScalerOf` (incl. canvas/`TextPaint` text) and `disableAnimationsOf`.
- [ ] Verified with TalkBack **and** VoiceOver: focus order sane, everything reachable & operable.
- [ ] Touch targets ≥ 48 dp (larger for young kids) with generous spacing.
- [ ] Contrast meets WCAG AA; meaning never relies on color alone; a no-timer option exists.

Child safety & privacy:
- [ ] No tracking, ads, analytics, or advertising IDs (IDFA / GAID); no SDKs that phone home.
- [ ] No accounts/login; collects no personal data; stores only local progress/settings.
- [ ] No external links or IAP in the child flow; sensitive actions behind a real parental gate.
- [ ] Offline-first; Android **release** manifest has no `INTERNET` permission; minimal permissions.
- [ ] iOS App Privacy + Play Data-safety both declare "no data collected/shared."
- [ ] Checklist + risk list delivered; no approval/compliance guarantees made.
