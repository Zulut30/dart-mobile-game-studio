# Release policy (App Store + Google Play)

One Flutter codebase ships to **two** stores with different rules, signing, and review. This policy
is what `release-engineer` follows to make a finished game submission-ready and avoid rejections.
It produces a plan + checklist; the actual upload/submit is done by the user. **No approval guarantee.**

## Shared (both stores)
- **Versioning.** `pubspec.yaml` `version: 1.2.0+34` → marketing `1.2.0` + build `34`. The build
  number must **increase** every upload (Android `versionCode`, iOS build). Never reuse one.
- **App identity.** Stable bundle id / application id (reverse-DNS), display name, supported
  orientations and device families (phone + tablet/iPad), min SDK / deployment target.
- **Icons & splash.** Complete adaptive icon set (no alpha / baked rounding on iOS); a launch/splash
  matching the first frame. Generate with `flutter_launcher_icons` / `flutter_native_splash`, or by
  hand; original art only (coordinate with `art-director`).
- **Permissions = only what you use.** iOS `Info.plist` usage strings for any sensitive API; Android
  `AndroidManifest.xml` permissions minimal. **Offline kids game → no `INTERNET` permission.**
- **Privacy.** Fill **App Store App Privacy** (nutrition label) and **Google Play Data safety** form
  to match what the app and its SDKs actually collect — "no data collected" only if true. iOS
  privacy manifest where required. Coordinate with `security-auditor` / `legal-compliance`.
- **Age rating.** Apple age rating questionnaire and **IARC** (Play) content rating; for a child
  title meet **Apple Kids Category** and **Google Play Families / Designed for Families** rules.
- **Store listing.** Title, subtitle/short description, full description, keywords, screenshots for
  the required device sizes (no debug/placeholder UI), feature graphic (Play), privacy-policy URL
  (required for Families and any data handling). No misleading metadata.
- **Build clean.** `flutter analyze` clean, tests green, `flutter build` in **release** mode, crash-
  free on real devices. Strip debug logging.

## Android (Google Play)
- **Build:** `flutter build appbundle` (AAB is required for Play); `flutter build apk
  --split-per-abi` for sideload/testing.
- **Signing:** an upload keystore; configure `android/key.properties` + `signingConfigs` in
  `build.gradle`; enable **Play App Signing**. Never commit the keystore or its passwords.
- **Manifest:** `applicationId`, `versionCode`/`versionName` from Flutter, `minSdkVersion` per target,
  permissions minimal, `usesCleartextTraffic=false` for offline.
- **Track flow:** internal testing → closed testing → open/production. Data safety form, content
  rating (IARC), target API level compliance, Families program if a kids title.

## iOS / iPadOS (App Store)
- **Build:** `flutter build ipa` (needs macOS + Xcode). Archive & validate in Xcode/Transporter.
- **Signing:** Apple Developer account, distribution certificate + App Store provisioning profile;
  automatic or manual signing; correct bundle id and capabilities/entitlements (only what's used).
- **Export compliance:** set `ITSAppUsesNonExemptEncryption` (usually `false` for a simple offline
  game) so you aren't asked every upload.
- **Flow:** upload → **TestFlight** (internal/external) → App Store review → release. App Privacy
  answers + privacy manifest; Kids Category rules if a child title.

## Common rejection traps (check actively)
- Crashes/bugs on launch or broken features; placeholder text/art shipped.
- Privacy label/Data-safety mismatch; missing privacy-policy URL; permission with no/weak rationale.
- Kids app with ads, tracking, analytics, AdvertisingId, external links, or unguarded purchases.
- Sign-in-with-Apple missing when another third-party login is offered (Apple 4.8); IAP not using
  StoreKit/Play Billing; broken **Restore Purchases**.
- Non-incrementing build number; Android not shipping an AAB; wrong age rating.

## Pre-submission checklist (per store)
- [ ] Version/build bumped (build number increased).
- [ ] Icons + splash complete; original art; correct sizes.
- [ ] Permissions minimal + justified; offline kids build has no INTERNET.
- [ ] Privacy (App Privacy / Data safety) accurate; privacy-policy URL where required.
- [ ] Age rating / IARC set; Kids/Families rules met if applicable.
- [ ] Signing configured (keystore / distribution cert); secrets not committed.
- [ ] `flutter build appbundle` / `flutter build ipa` succeeds in release; tested on a real device.
- [ ] Screenshots/metadata ready; no placeholders.
- [ ] Monetization (if any) verified per `monetization-policy.md`.
- [ ] Tests green; `flutter analyze` clean — and you actually ran them.

Deliver this as a plan + filled checklist + risk list. **Never** assert the app is "approved" or
"compliant" — only Apple/Google and (for legal) counsel decide that.
