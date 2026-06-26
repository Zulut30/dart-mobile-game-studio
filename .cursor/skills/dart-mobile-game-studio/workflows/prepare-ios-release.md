# Workflow: Prepare an iOS / iPadOS Release (App Store)

**Goal:** Take a finished Flutter game to a **submittable** App Store build — identifiers, version,
icons, signing, a release archive (`flutter build ipa`), App Store Connect metadata, and the privacy
+ Kids answers — with the rejection traps checked.

**When to use:** the game is feature-complete, tested, and passed the perf audit; you're preparing the
first submission or an update.

**When NOT to use:** mid-development; or Android (use [`prepare-android-release`](prepare-android-release.md)).
Run both for a cross-platform ship.

**Prerequisites**
- [`references/release-policy`](../references/release-policy.md) (§Shared, §iOS) and
  [`checklists/app-store-release`](../checklists/app-store-release.md) — the binding rules; this
  operationalizes them.
- macOS + Xcode. Gate it: `scripts/flutter-preflight.sh --require flutter,xcode --git-clean`.
- A paid Apple Developer account and an App Store Connect app record.

> **No approval guarantee.** This makes the build *submittable* and reduces rejection risk — it does
> **not** promise App Review will pass. Output a checklist + a risk list, never "approved". Kids-title
> rules ([`accessibility-child-safety`](../references/accessibility-child-safety.md)) are binding, not optional.

---

## STEP 1 — Preflight & identifiers

```bash
scripts/flutter-preflight.sh --require flutter,xcode --git-clean
```

Set the bundle identifier and display name (reverse-DNS, matching the App Store Connect record):
- `ios/Runner.xcodeproj` → `PRODUCT_BUNDLE_IDENTIFIER` (e.g. `com.example.mygame`).
- `ios/Runner/Info.plist` → `CFBundleDisplayName` (the home-screen name).

**Done when:** preflight passes (Flutter+Xcode present, tree clean) and the bundle id matches App Store Connect.

---

## STEP 2 — Version & build number

`pubspec.yaml` drives both: `version: 1.0.0+1` → marketing version `1.0.0` (`CFBundleShortVersionString`)
and build `1` (`CFBundleVersion`). **Every upload needs a higher build number** for the same version.

```yaml
version: 1.0.0+1   # bump +1 → +2 for each TestFlight/App Store upload of 1.0.0
```

**Done when:** the marketing version and a not-yet-used build number are set.

---

## STEP 3 — App icon & launch screen

- App icon: a 1024×1024 (no alpha, no rounded corners) plus the device sizes in
  `ios/Runner/Assets.xcassets/AppIcon.appiconset/`. Generate the set from one master (e.g.
  `flutter_launcher_icons`) — every required slot filled or App Review flags missing icons.
- Launch screen: `ios/Runner/Base.lproj/LaunchScreen.storyboard` (a static brand frame, no
  spinners/text); it must not look broken on notch/Dynamic-Island devices.

**Done when:** all icon slots are filled and the launch screen renders correctly on a notch device.

---

## STEP 4 — Capabilities, orientation & Info.plist hygiene

- **Usage strings:** add an `NS…UsageDescription` for **every** sensitive API you use (camera, mic,
  photos, location) — and **none** for APIs you don't. A missing-or-spurious string is a classic reject.
- **Orientation:** `UISupportedInterfaceOrientations` matches what the game actually supports
  (iPhone) and `…~ipad` for iPad; lock it if the game is portrait-only.
- **Export compliance:** if the app uses no non-exempt encryption, set
  `ITSAppUsesNonExemptEncryption = false` in `Info.plist` to skip the per-upload prompt.
- **Kids title:** no third-party SDKs that collect data; no external links without a parental gate.

**Done when:** Info.plist has exactly the usage strings the code needs, correct orientations, and the encryption key.

---

## STEP 5 — Signing & provisioning

In Xcode (`open ios/Runner.xcworkspace`) → **Signing & Capabilities**: pick the Team; automatic
signing is simplest (Xcode manages the profile). For CI, use a manual distribution profile + an App
Store provisioning profile. The bundle id, Team, and profile must all agree, or the archive fails.

**Done when:** `Runner` signs for **Any iOS Device (arm64)** with a distribution Team and no signing errors.

---

## STEP 6 — Build the release archive

```bash
scripts/pub-get-if-changed.sh
flutter build ipa --release 2>&1 | tee /tmp/ios-build.log
# on failure, shrink the log:
scripts/triage-log.py /tmp/ios-build.log
```

`flutter build ipa` produces `build/ios/ipa/*.ipa` and an Xcode archive. (CocoaPods runs as part of
the build; a `pod` error → `cd ios && pod install`, see the triage hint.)

**Done when:** an `.ipa` is produced with no signing/build errors.

---

## STEP 7 — Upload & App Store Connect metadata

Upload with **Transporter** (or Xcode Organizer, or `xcrun altool`/`notarytool` in CI). Then in App
Store Connect fill:
- **App Privacy** ("nutrition label") — answer truthfully; "Data Not Collected" only if true. Add an
  iOS **privacy manifest** (`PrivacyInfo.xcprivacy`) declaring required-reason APIs where used.
- **Age rating** (IARC questionnaire) consistent with content; for a **Kids Category** app, pick the
  age band (5/6–8/9–11) and meet its rules (no behavioral ads, no external links without a gate).
- Screenshots (per device class), description, keywords, support URL, privacy policy URL (required for
  Kids / any data handling).

**Done when:** the build shows in App Store Connect and every required metadata/privacy field is complete and truthful.

---

## STEP 8 — TestFlight, then submit

Smoke-test the actual uploaded build via **TestFlight** on a real device before submitting for review.
Then submit for App Review.

**Done when:** the TestFlight build runs clean and the version is submitted.

---

## Master "done when"
1. Preflight green; bundle id matches App Store Connect (Steps 1–2).
2. Icons, launch screen, Info.plist usage strings/orientation/encryption correct (Steps 3–4).
3. Distribution signing works; `.ipa` archives (Steps 5–6).
4. Build uploaded; App Privacy + age rating + metadata truthful and complete (Step 7).
5. TestFlight smoke-test passes; submitted (Step 8).

## Handoff
Report: bundle id, version+build, what was configured, **commands run + real output**
(`flutter build ipa`), the [`checklists/app-store-release`](../checklists/app-store-release.md) results,
and a **risk list** (privacy answers, Kids-Category items, anything unverified). **No approval
guarantee.** The actual upload/submit is a human action in App Store Connect.

## Common pitfalls
- **Reusing a build number** — every upload of the same version needs a higher `+build`.
- **Spurious usage strings** — an `NS…UsageDescription` for an API you don't use invites a reject.
- **Privacy label ≠ code** — "Data Not Collected" while an SDK phones home is a hard reject (and worse for Kids).
- **Missing icon slots / alpha in the 1024** — App Review flags both.
- **Kids Category with third-party ads/analytics** — disallowed; strip them or change category/audience.

## See also
- [`references/release-policy`](../references/release-policy.md), [`checklists/app-store-release`](../checklists/app-store-release.md).
- [`prepare-android-release`](prepare-android-release.md) — the Play Store counterpart.
- [`references/accessibility-child-safety`](../references/accessibility-child-safety.md) — Kids Category rules.
