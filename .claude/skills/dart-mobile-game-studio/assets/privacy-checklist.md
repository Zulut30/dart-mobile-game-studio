# Privacy checklist — <GAME NAME>

Data handling for a Flutter game shipping to **App Store and Google Play**. The skill's default is
**collect nothing**; this checklist verifies that's actually true and that disclosures match the
code. Not legal advice and **not** a guarantee of approval — route material/uncertain items to
`legal-compliance` and counsel.

## Audience first
- [ ] Audience decided: **kids** (Apple Kids Category / child-directed / Google Play Families,
      under-13 COPPA / GDPR-K) vs **general (13+)**. Mixed audience inherits the kids bar for children.
- [ ] If unsure → treated as a **kids build** (strictest posture).

## Collect nothing (the default)
- [ ] No personal data collected (name, email, location, contacts, photos, device IDs, precise IP).
- [ ] Only **local** progress/settings stored on-device; nothing leaves the device.
- [ ] Offline-first: no network calls in the play path; Android manifest declares **no `INTERNET`**
      permission if truly offline.
- [ ] No third-party SDKs that collect data (no Firebase Analytics, no Crashlytics that transmits, no
      ad/attribution SDKs in a kids build).

## No tracking / ads (kids) — gated (general)
- [ ] **Kids:** no ads, no analytics, no AdvertisingId (IDFA/GAID), no ATT prompt, no behavioral targeting.
- [ ] Android: `com.google.android.gms.permission.AD_ID` **not** requested for a child-directed app.
- [ ] **General (13+):** any ads/IAP follow `monetization-policy.md`; iOS ATT requested before tracking;
      EU consent (CMP) where required; non-personalized fallback works.

## Permissions
- [ ] Only permissions actually used; each has a clear rationale.
- [ ] iOS `Info.plist` usage strings present for any sensitive API (camera/mic/photos/location) — and
      none for APIs you don't use.
- [ ] Android `AndroidManifest.xml` permissions minimal; no broad/legacy permissions.

## Store disclosures (must match the code)
- [ ] **Apple App Privacy** ("nutrition label") filled — "Data Not Collected" only if true; iOS
      **privacy manifest** (`PrivacyInfo.xcprivacy`) where required; required-reason APIs declared.
- [ ] **Google Play Data safety** form filled to match actual behavior.
- [ ] **Privacy policy URL** present where required (Families program, any data handling).
- [ ] Age rating / IARC answers consistent with content and data use.

## Verification
- [ ] `grep`/audit for ad/analytics/tracking SDK imports, `http://`, external `launchUrl`, secrets — none in the kids flow.
- [ ] `scripts/dart-doctor.py` privacy/kids-safety checks pass.
- [ ] `security-auditor` + `legal-compliance` reviewed; **risks listed, no approval guarantee**.
