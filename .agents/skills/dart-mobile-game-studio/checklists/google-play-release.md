# Google Play release checklist

A tick-list a reviewer/agent runs to ship a Flutter/Dart mobile game to Google Play. It enforces
the policies in `references/testing-and-release.md` (build artifacts, versioning, signing, Data
safety, IARC, Families) and `references/flutter-games-toolkit.md` §4 (permissions, AD_ID, offline
posture); it does not re-explain them. Check each box or note why it doesn't apply. **Run the
artifact + analysis gates locally and quote real output** — only claim a build passed if you saw
it. Apple side is a separate list; this one is Play-only.

> Target API floor below assumes the Aug 31 2025 requirement: **new apps and updates target
> Android 15 (API 35)**; TV/Wear/Automotive may stay at API 34. Re-confirm the current floor in
> Play Console before submission — Google raises it yearly.

## Pre-build hygiene (gates before any artifact)
- [ ] `dart format --set-exit-if-changed .` produces no diff (2-space); `dart analyze` / `flutter analyze` report **zero** issues.
- [ ] `dart test` (pure core) and `flutter test` (renderer) are all green; output quoted in the handoff.
- [ ] Pure model in `lib/game_internals/` imports neither `package:flutter` nor `package:flame`; seeded `Random` injected so runs are deterministic.
- [ ] No debug logging sink ships off-device (console-only `logging`; no Crashlytics/Sentry/analytics listener); no placeholder text or copyrighted assets.

## App identity & version
- [ ] `applicationId` in `android/app/build.gradle(.kts)` is set off `com.example.*` and is the final, permanent package name.
- [ ] `pubspec.yaml` `version: x.y.z+N` set; `+N` maps to `versionCode` and `x.y.z` to `versionName`.
- [ ] **`versionCode` strictly increases** vs the highest code ever uploaded to *any* track — Play rejects a re-used or lower code (bump `+N` on every upload, even re-uploads of the same `versionName`).
- [ ] Adaptive launcher icon + splash generated for Android (`flutter_launcher_icons` / `flutter_native_splash` or hand-set `mipmap-*`); 512×512 Play Store icon (32-bit PNG with alpha) prepared.
- [ ] `minSdkVersion` and `targetSdkVersion` set; `targetSdkVersion` meets the current Play floor (**API 35** for standard apps as of this writing — re-confirm).

## Permissions (minimal; offline-first)
- [ ] Merged manifest reviewed: build the AAB, then inspect `app/build/outputs/.../AndroidManifest.xml` (or `bundletool dump manifest`) — declared permissions match *only* what the game actually uses.
- [ ] **No `android.permission.INTERNET`** for a fully offline game — if a transitive plugin adds it, remove with `<uses-permission android:name="android.permission.INTERNET" tools:node="remove"/>` (and add `xmlns:tools` to `<manifest>`); verify gameplay in airplane mode.
- [ ] **No advertising-identifier permission for a kids/Families build:** explicitly strip the auto-merged AD_ID permission — `<uses-permission android:name="com.google.android.gms.permission.AD_ID" tools:node="remove"/>` — and confirm it is absent from the merged manifest.
- [ ] If the app *does* target Android 13+ and legitimately uses an advertising ID, the AD_ID permission is **declared** (required since the API-33 change) and the use is disclosed — but a kids game should have neither ads nor this permission.
- [ ] No location / camera / microphone / contacts / storage permission present unless a feature genuinely needs it and it is justified in the handoff.

## Signing & secrets
- [ ] Upload keystore generated (`keytool -genkey -v -keystore upload-keystore.jks -alias upload ...`) and referenced via `android/key.properties`; release build is configured to sign with it (not the debug key).
- [ ] **Play App Signing enrolled** — Google holds the app signing key; you upload with the upload key. The app signing key is never on your machine or in CI.
- [ ] Keystore, `key.properties`, and any service-account JSON are **git-ignored and not committed** (verify with `git ls-files | grep -Ei 'keystore|key.properties|.jks|.p12|.json'` returning nothing sensitive); CI reads them from encrypted secrets, not the repo.
- [ ] Upload keystore backed up securely off-repo — losing it means requesting an upload-key reset from Google.

## Build the App Bundle (AAB)
- [ ] `flutter build appbundle --release` succeeds; artifact at `build/app/outputs/bundle/release/app-release.aab` (build command + result quoted in handoff).
- [ ] AAB (not APK) is the upload artifact — Play requires `.aab` for new apps; APKs are for sideload/test only.
- [ ] Release build is not the debug build: no debug banner, no `kDebugMode`-gated test hooks reachable, R8/shrinking behaves (smoke-test the release artifact on a device, not just debug).
- [ ] (Optional) `bundletool build-apks --connected-device` install from the AAB verifies the bundle actually produces a runnable APK set on a real device/ABI.

## Store listing & content declarations (Play Console → App content)
- [ ] **Data safety form** completed and consistent with the code and the Apple Privacy Nutrition Label: an offline, no-tracking game declares **no data collected, no data shared, no advertising ID**.
- [ ] **IARC content-rating questionnaire** completed honestly; resulting regional ratings reviewed (a no-objectionable-content game lands in the lowest brackets).
- [ ] **Target audience & content**: age groups set truthfully; if children are included, the app enters Families requirements (next section).
- [ ] App access (login-free game = "All functionality available without restrictions"), Ads declaration (**"No ads"** for a kids game), and Government-apps/News/COVID declarations answered as applicable.
- [ ] Privacy policy URL provided if required (target audience includes children, or any data collected).
- [ ] Store assets ready: title, short + full description, feature graphic (1024×500), phone screenshots (and tablet screenshots if `<supports-screens>` / large-screen support is claimed).

## Designed for Families (only if target audience includes children)
- [ ] Opted into the **Designed for Families** program and completed the Families policy declarations.
- [ ] No ads/analytics/tracking SDKs anywhere (`google_mobile_ads`, `firebase_*`, attribution SDKs absent from the transitive tree); AD_ID permission absent (verified above).
- [ ] No accounts, sign-in, or personal data; no external links (web/store/social) without a verified parental gate; no manipulative purchase nudges.
- [ ] Any IAP (prefer none) sits behind a real parental gate and never interrupts gameplay; ad/SDK posture is Families-approved (ideally none).
- [ ] Accessibility line satisfied: `Semantics(label:/value:/...)` on every interactive control, large text respected, reduced-motion respected (see `checklists/accessibility.md`).

## Release tracks (promote gradually)
- [ ] Uploaded to **Internal testing** first; installed from the Play link on a real device and the core loop played start → win/lose → restart.
- [ ] Promoted to **Closed testing** (alpha) with real testers; pre-launch report (Play's automated device crawl) reviewed for crashes, ANRs, accessibility, and permission flags.
- [ ] Promoted to **Open testing** if a wider beta is wanted; staged rollout percentage chosen for **Production**.
- [ ] Each track promotion re-confirms versionCode increased and the Data safety / content rating / Families declarations still match the binary.

## Final honesty gate
- [ ] Handoff states exactly which commands ran with real output (format/analyze/test/`flutter build appbundle`) and which did not (e.g. no toolchain / no device) — no claimed-but-unrun steps.
- [ ] A risk list accompanies this checklist. **No approval guarantee:** Google Play reviews the final binary and its declared data practices against the current Play, Families, and Data-safety policies — verify against those, not this file.
