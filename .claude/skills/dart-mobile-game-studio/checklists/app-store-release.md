# App Store (iOS) release checklist

A tick-list a reviewer or agent runs before submitting a Flutter/Dart game to Apple's App
Store. **iOS / iPadOS only** — the Google Play side lives in its own checklist. Derived from
`references/testing-and-release.md` (§"Building release artifacts", §"Dual-store privacy &
compliance forms", §"Kids / Families program checklist", §"Release checklist") and the kids-safety
doctrine; see those for the *why*. Each box is verifiable from a file, one command, or an App Store
Connect screen. Commands and key names are confirmed against the Flutter iOS deploy doc and Apple's
privacy-manifest doc — do not invent variants.

> Needs macOS + Xcode + a paid Apple Developer account. **No approval guarantee** — this is a
> pre-flight, not a promise. Verify against the current App Store Review Guidelines and (if targeting
> children) the Kids Category rules before submitting.

## Pre-flight gates (must be green first)

- [ ] `dart format --output=none --set-exit-if-changed .` clean and `flutter analyze` reports zero issues.
- [ ] `dart test` and `flutter test` all green (run them; quote real pass/fail counts — no claimed-but-unrun results).
- [ ] `flutter build ipa` was actually run on this machine and succeeded (see artifact box below) — not assumed.

## Identity, version & build number

- [ ] **Bundle Identifier** set to a real reverse-DNS id, **off `com.example.*`**, and matches the Explicit App ID registered on the Apple Developer account (`ios/Runner.xcworkspace` → Runner → General).
- [ ] An app record exists in App Store Connect bound to that same Bundle ID.
- [ ] `version:` in `pubspec.yaml` is `name+build` (e.g. `1.2.0+7`) → iOS `CFBundleShortVersionString` (name) and `CFBundleVersion` (build).
- [ ] **Build number bumped** since the last upload for this version — App Store rejects a re-used `CFBundleVersion`. Bump via `pubspec.yaml` or `flutter build ipa --build-number=<n>`.
- [ ] iOS Deployment Target set deliberately (Flutter floor is iOS 13) — not left at an Xcode default you didn't choose.

## Signing & provisioning

- [ ] Xcode **Signing & Capabilities**: a valid **Team** is selected and signing is configured (automatic signing on, or an explicit distribution profile for manual signing).
- [ ] Distribution certificate + App Store provisioning profile are valid and **not expired**.
- [ ] No signing secrets in git — keychains, `*.p12`, App Store Connect API keys (`AuthKey_*.p8`) are ignored/out of the repo.

## Capabilities & permissions (keep minimal)

- [ ] Only the **capabilities/entitlements the game actually uses** are enabled in Signing & Capabilities — strip every unused one (Push, iCloud, Game Center, etc.).
- [ ] `Info.plist` declares a `NS*UsageDescription` string for **every** sensitive resource accessed (and none for resources you don't use). A privacy-first offline game should need essentially none.
- [ ] No background modes, URL schemes, or associated domains left in from a template that the game doesn't use.

## Export compliance (encryption)

- [ ] `ITSAppUsesNonExemptEncryption` is set in `Info.plist` so App Store Connect stops prompting on every upload. Use `<false/>` only if the app uses **just** exempt encryption (HTTPS/TLS, OS-standard crypto) — true for a typical offline game.
- [ ] If anything non-exempt is used, set it `<true/>` and complete the export-compliance documentation instead — answer honestly.

## App Privacy (nutrition label) & privacy manifest

- [ ] **App Privacy** completed in App Store Connect (→ App Privacy). For an offline game with no tracking/analytics/accounts the truthful answer is **"Data Not Collected"**.
- [ ] The label **matches the code and the Play Data-safety form** — no SDK quietly collects data the label omits.
- [ ] `ios/Runner/PrivacyInfo.xcprivacy` privacy manifest is present and accurate: data types collected, tracking flag, and **`NSPrivacyAccessedAPITypes`** with a declared reason for **every** required-reason API the app (or a plugin) touches.
- [ ] No advertising-identifier access: the app does **not** read IDFA / use `ATTrackingManager` (and no plugin pulls it in transitively — check the merged manifest/Pods).

## Age rating & Kids Category (only if applicable)

- [ ] Age-rating questionnaire in App Store Connect answered **honestly** — a kids game lands in the lowest band only if content genuinely warrants it.
- [ ] If opting into the **Kids Category**: an age band is selected (5 & under / 6–8 / 9–11).
- [ ] Kids rules satisfied: **no third-party analytics or ads**, no behavioral/contextual tracking, no external links out of the app without a **verified parental gate**, no accounts or personal-data collection, offline-first.
- [ ] Accessibility holds up under review: `Semantics(label:/value:/...)` on every interactive control; large text and reduced-motion respected.

## Screenshots & store assets

- [ ] App icon: **1024×1024** master, **no alpha channel**, no transparency, no rounded corners pre-baked (`Assets.xcassets`); placeholder icon replaced.
- [ ] Launch image/storyboard replaced (no Flutter placeholder).
- [ ] Screenshots prepared for the **required device sizes** (6.7"/6.9" iPhone and 12.9"/13" iPad at minimum) showing real gameplay, not mockups or placeholder UI.

## Build, upload & TestFlight

- [ ] `flutter build ipa` produced the artifact at `build/ios/ipa/*.ipa` (archive at `build/ios/archive/*.xcarchive`).
- [ ] Uploaded via **Transporter** or `xcrun altool --upload-app --type ios -f build/ios/ipa/*.ipa --apiKey <id> --apiIssuer <id>` (or Xcode Organizer → Validate → Distribute).
- [ ] Validation passed (Validate App in Xcode, or altool, reports no errors).
- [ ] Build appears in **TestFlight** and was smoke-tested via **Internal Testing** on a real device **before** submitting for review.

## No placeholders / final read

- [ ] No `// TODO`, lorem-ipsum, "MyApp", or template strings in user-facing UI, display name, or store metadata.
- [ ] No debug logging, `print(...)`, or `kDebugMode`-only scaffolding reachable in the release build; built `--release`, not debug/profile.
- [ ] No copyrighted or non-owned assets shipped (art, fonts, audio) — placeholder vector shapes / SF-equivalent / user-owned only.
- [ ] Manual QA pass done on a real device: full loop to win/(lose), rotation, background→foreground (no `dt` spike), VoiceOver navigable, cold-relaunch persistence intact.

**Never assert guaranteed App Store / COPPA / Kids approval.** Hand off this completed checklist plus a
risk list, and recommend re-verifying against the current App Store Review Guidelines and Kids Category
requirements at submission time.
