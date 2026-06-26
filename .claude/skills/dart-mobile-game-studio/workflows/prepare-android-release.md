# Workflow: Prepare an Android Release (Google Play)

**Goal:** Take a finished Flutter game to a **submittable** Google Play build — application id,
version, icons, a signed **App Bundle** (`flutter build appbundle`), Play Console metadata, and the
Data safety + Families answers — with the rejection traps checked.

**When to use:** the game is feature-complete, tested, and passed the perf audit; preparing the first
release or an update.

**When NOT to use:** mid-development; or iOS (use [`prepare-ios-release`](prepare-ios-release.md)).

**Prerequisites**
- [`references/release-policy`](../references/release-policy.md) (§Shared, §Android) and
  [`checklists/google-play-release`](../checklists/google-play-release.md) — the binding rules.
- Gate it: `scripts/flutter-preflight.sh --require flutter,android --git-clean`.
- A Google Play Console account and an app record.

> **No approval guarantee.** This makes the build *submittable* and reduces rejection/policy risk — it
> does **not** promise Play review passes. Output a checklist + a risk list. The **Families** program
> rules ([`accessibility-child-safety`](../references/accessibility-child-safety.md)) are binding for a
> kids/mixed audience.

---

## STEP 1 — Preflight & application id

```bash
scripts/flutter-preflight.sh --require flutter,android --git-clean
```

Set the application id (reverse-DNS, **immutable** once published) and label:
- `android/app/build.gradle` → `applicationId "com.example.mygame"` (and `namespace`).
- `android/app/src/main/AndroidManifest.xml` → `android:label` (the launcher name).

**Done when:** preflight passes and `applicationId` matches the Play Console record.

---

## STEP 2 — Version & SDK levels

`pubspec.yaml` `version: 1.0.0+1` maps to `versionName 1.0.0` and `versionCode 1`. **Every upload
needs a higher `versionCode`.** Set SDK levels in `android/app/build.gradle`:

```gradle
defaultConfig {
    minSdkVersion flutter.minSdkVersion   // raise only if a plugin requires it
    targetSdkVersion flutter.targetSdkVersion  // must meet Play's current target-API requirement
}
```

Play enforces a **minimum `targetSdkVersion`** for new uploads — an out-of-date target is rejected at
upload. Bump it to the required API level.

**Done when:** versionName + a fresh versionCode are set and `targetSdkVersion` meets Play's current requirement.

---

## STEP 3 — App icon (adaptive)

Provide an **adaptive icon** (foreground + background layers) in
`android/app/src/main/res/mipmap-*/` and `mipmap-anydpi-v26/ic_launcher.xml`, plus a 512×512 hi-res
icon for the store listing. Generate from one master (e.g. `flutter_launcher_icons`) so every density
bucket is filled.

**Done when:** adaptive icon renders correctly across launchers and all density buckets exist.

---

## STEP 4 — Permissions & manifest hygiene (kids-critical)

- **Minimal permissions.** Remove anything unused. If the game is offline, **do not** declare
  `android.permission.INTERNET`.
- **Advertising ID.** For a child-directed / Families app, do **not** request
  `com.google.android.gms.permission.AD_ID`; declare its removal if a transitive library adds it.
- No exported components without need; no debuggable flag in release.

**Done when:** the manifest lists only permissions the game uses, with no `AD_ID` in a kids build.

---

## STEP 5 — Release signing (upload key)

Create an upload keystore and wire it so release builds are signed (never ship the debug key):

```bash
keytool -genkey -v -keystore ~/upload-keystore.jks -keyalg RSA -keysize 2048 \
  -validity 10000 -alias upload
```

Reference it via `android/key.properties` (git-ignored) and `signingConfigs { release { … } }` in
`android/app/build.gradle`; enable **Play App Signing** in the Console (Google manages the app signing
key; you hold the upload key). Keep the keystore + passwords backed up — losing the upload key blocks
updates.

**Done when:** `flutter build appbundle --release` produces a bundle signed with the upload key (not debug).

---

## STEP 6 — Build the App Bundle (.aab)

```bash
scripts/pub-get-if-changed.sh
flutter build appbundle --release 2>&1 | tee /tmp/android-build.log
# on failure, shrink the log (Gradle dumps thousands of lines):
scripts/triage-log.py /tmp/android-build.log
```

Ship the **App Bundle** (`build/app/outputs/bundle/release/app-release.aab`), not an APK — Play
requires `.aab` for new apps and serves per-device-optimized splits.

**Done when:** a signed `.aab` is produced with no build errors.

---

## STEP 7 — Play Console: upload & metadata

Create a release on a track (internal → closed → production) and upload the `.aab`. Then complete:
- **Data safety** form — must match actual behavior. For a kids build with no collection: "no data
  collected/shared"; declare any SDK that does.
- **Target audience & content / Families** — set the age groups; a child-targeted app must follow the
  **Designed for Families** requirements (approved ads SDKs only, no AD_ID, privacy policy).
- **Content rating** (IARC questionnaire), store listing (title, short/full description, screenshots,
  feature graphic), and a **privacy policy URL** (required for Families / any data handling).

**Done when:** the bundle is uploaded and Data safety + audience + content rating + listing are complete and truthful.

---

## STEP 8 — Internal test, then roll out

Use an **internal testing** track to run the actual uploaded bundle on real devices before promoting.
Then roll out to production (staged rollout recommended).

**Done when:** the internal-track build runs clean and the release is submitted/rolled out.

---

## Master "done when"
1. Preflight green; `applicationId` matches Play and is final (Steps 1–2).
2. `targetSdkVersion` meets Play's requirement; fresh versionCode (Step 2).
3. Adaptive icon complete; permissions minimal, no `AD_ID` in a kids build (Steps 3–4).
4. Release-signed `.aab` builds (Steps 5–6).
5. Data safety + Families + content rating truthful; uploaded; internal test passes (Steps 7–8).

## Handoff
Report: applicationId, versionName+versionCode, targetSdk, what was configured, **commands run + real
output** (`flutter build appbundle`), the [`checklists/google-play-release`](../checklists/google-play-release.md)
results, and a **risk list** (Data safety answers, Families items, key-management). **No approval
guarantee.** The upload/rollout is a human action in the Play Console.

## Common pitfalls
- **Reusing a versionCode** — every upload needs a higher one; Play rejects duplicates at upload.
- **Stale `targetSdkVersion`** — below Play's current minimum is rejected at upload.
- **Shipping an APK** — new apps require an `.aab`.
- **`AD_ID` permission in a kids build** — violates Families policy; remove it (and any transitive add).
- **Data safety ≠ behavior** — mismatches are a policy strike; declare exactly what the code does.
- **Losing the upload keystore** — you can't update the app; back it up immediately.

## See also
- [`references/release-policy`](../references/release-policy.md), [`checklists/google-play-release`](../checklists/google-play-release.md).
- [`prepare-ios-release`](prepare-ios-release.md) — the App Store counterpart.
- [`references/accessibility-child-safety`](../references/accessibility-child-safety.md) — Families program rules.
