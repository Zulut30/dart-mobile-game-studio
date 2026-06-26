# Monetization checklist

A tick-list a reviewer or agent runs before shipping any ads or in-app purchases in a
Dart/Flutter mobile game. It enforces `references/flutter-games-toolkit.md` §4 (ads/IAP/analytics
out of kids builds), `references/testing-and-release.md` (privacy forms, Kids/Families, release),
and the skill's `monetization-policy` / `package-policy` — it does not re-explain them; read those
for the *why*. Check each box or note why it doesn't apply. Any fail → fix before handoff.

## Audience gate (decide this first)
- [ ] Target audience is declared **before** any SDK is added: a build aimed at children
      (iOS Kids Category band 5-&-under / 6-8 / 9-11, or Play **target audience = children** /
      Designed for Families) ships **no ads and no tracking** — stop here, the rest of this file
      does not apply.
- [ ] A mixed-audience build that includes children still treats the child path as a kids build:
      no ads, no advertising id, no tracking for any user the app knows or should treat as a child.
- [ ] Kids build proves the ban: `flutter pub deps --style=compact` has **no** `google_mobile_ads`,
      `in_app_purchase`, `firebase_*`, `appsflyer`/`segment`/`mixpanel`/`sentry` (the §4.1 CI grep
      is clean on the transitive tree).
- [ ] Kids build has **no advertising identifier**: iOS does not link `AdSupport.framework`, never
      calls `ASIdentifierManager`, and ships no `NSUserTrackingUsageDescription`; Android removes
      `com.google.android.gms.permission.AD_ID` via `tools:node="remove"` in the merged manifest.

## Package & policy justification
- [ ] Every monetization package is the **official** one and justified per `package-policy`
      (official → mature community → none): ads via `google_mobile_ads`, purchases via
      `in_app_purchase` — no third-party attribution/mediation SDK added without a written reason.
- [ ] Each ads/IAP plugin and its native config (AdMob app id, StoreKit/Play Billing setup) is
      pinned to a version compatible with the current Flutter/Dart SDK; `flutter analyze` is clean.

## Test IDs in dev (never ship live IDs in debug)
- [ ] Ads use Google's **test ad unit IDs** in debug/profile, never your live unit id: banner test
      id `ca-app-pub-3940256099942544/6300978111` (Android) / `.../2934735716` (iOS), and the
      platform-specific interstitial/rewarded test ids — switched by build flavor or `kReleaseMode`,
      not hard-coded live ids guarded by a comment.
- [ ] Test devices are registered so live-id requests can't fire in test:
      `MobileAds.instance.updateRequestConfiguration(RequestConfiguration(testDeviceIds: [...]))`;
      emulators/simulators are auto-registered — confirmed no real impressions logged in dev.
- [ ] IAP is exercised against **sandbox/test** accounts (App Store sandbox tester, Play
      license-test account) — no real charges during development or QA.

## Consent & transparency before any ad request
- [ ] **iOS ATT:** if the app (or its ad SDK) accesses the IDFA, `NSUserTrackingUsageDescription`
      is set and `ATTrackingManager.requestTrackingAuthorization` is shown **before** that access;
      a denied/undetermined status means no IDFA use and non-personalized ads only.
- [ ] **EU/UK consent (UMP):** `ConsentInformation.instance.requestConsentInfoUpdate(...)` runs on
      every launch, then `ConsentForm.loadAndShowConsentFormIfRequired(...)`; ads are requested only
      after `canRequestAds()` is true. ATT and the UMP form are two separate prompts on iOS.
- [ ] A privacy options entry point is provided where required
      (`getPrivacyOptionsRequirementStatus()` → `showPrivacyOptionsForm()`) so users can change
      their consent choice later.
- [ ] First-launch ordering is correct: consent/ATT resolved **before** `MobileAds.instance`
      initialization triggers the first ad load — no ad request races ahead of consent.

## Full-screen ads pause the game & are frequency-capped
- [ ] Interstitial/rewarded ads are shown only at natural breaks (level end, between runs), **never**
      mid-gameplay or over an active timer; no surprise full-screen ad on launch.
- [ ] Showing a full-screen ad **pauses the game loop** (`game.pauseEngine()` / `paused = true`,
      or the model's `pause()` transition) and mutes audio; gameplay and the `dt` clock do not
      advance while the ad is up.
- [ ] Resume after dismiss is clean: engine resumes (`resumeEngine()`), `dt` is clamped so no spike
      teleports objects, audio restores prior mute state, and game state is exactly where it paused.
- [ ] Ads are **frequency-capped** (e.g. minimum runs/levels or minutes between interstitials);
      the cap is enforced in code, not left to ad-server pacing alone — verified it can't show
      back-to-back.
- [ ] Ad lifecycle is leak-free: each `InterstitialAd`/`RewardedAd` is `dispose()`d in its
      `onAdDismissedFullScreenContent` / `onAdFailedToShowFullScreenContent` callback, and the next
      ad is preloaded only after the previous is released.

## In-app purchase: verify before grant, then complete
- [ ] Purchase updates are handled via the single `InAppPurchase.instance.purchaseStream`
      subscription set up **on every app launch** (so app-restart / interrupted purchases resolve).
- [ ] On `PurchaseStatus.purchased`/`restored` the receipt is **verified before** the entitlement is
      granted (server-side validation where feasible; at minimum the documented client verification)
      — content is never delivered on the raw stream event alone.
- [ ] After a verified grant, `InAppPurchase.instance.completePurchase(purchaseDetails)` is called
      for every detail where `pendingCompletePurchase` is true (Android refunds an uncompleted
      purchase after 3 days); `PurchaseStatus.error`/`canceled` are handled without granting.
- [ ] Consumables are granted exactly once (idempotent against duplicate stream events); the product
      catalog is fetched with `queryProductDetails` and missing/`notFoundIDs` products are handled.

## Restore Purchases & entitlement persistence
- [ ] A user-visible **"Restore Purchases"** control exists (required by App Store for non-consumable
      / subscription content) and calls `InAppPurchase.instance.restorePurchases()`; restored items
      arrive on the same `purchaseStream` and re-grant their entitlements.
- [ ] Non-consumable / subscription **entitlements persist locally** (e.g. `shared_preferences`) and
      survive a cold relaunch and reinstall-then-restore — the paywall does not reappear for an
      already-entitled user.
- [ ] Entitlement state is restored at startup before the store/paywall UI decides what to show, so a
      paid user is never shown a buy prompt for content they own.

## Store privacy answers match the SDKs actually shipped
- [ ] Apple **Privacy Nutrition Label** and `PrivacyInfo.xcprivacy` declare exactly the data the
      shipped ad/IAP SDKs collect (an ads build is **not** "Data Not Collected"); required-reason API
      uses are declared.
- [ ] Google Play **Data safety** form agrees with the Apple label and the code: advertising-id use,
      data shared with the ad network, and any analytics are declared truthfully — Play audits this.
- [ ] If ads were **removed** to make a kids build, the privacy declarations, manifest permissions,
      and `Info.plist`/`PrivacyInfo.xcprivacy` were updated to match (no stale ad-id or tracking
      declaration left behind).

## No dark patterns; playable with ads off
- [ ] **No dark patterns:** no disguised/mis-tapped ads, no forced-watch to start core play, no
      countdown/loss-of-progress pressure to buy, no buy prompt interrupting gameplay; the decline /
      close affordance is clear and equal-weight to the buy/watch one.
- [ ] Any purchase a child could reach sits behind a real **parental gate** (an age-appropriate
      challenge a young child can't pass — e.g. arithmetic/date, not "tap to buy") and never a
      timer/lives/loot mechanic that pressures spend.
- [ ] The **game is fully playable with ads off and nothing purchased**: rewarded ads grant only
      optional convenience (never gate progression or completion); an ad failing to load or being
      declined never blocks play. Verified by playing the core loop start → win with ads disabled.
- [ ] No ad or purchase flow makes a network call or shows a prompt in **kids/offline-first** mode;
      airplane-mode launch reaches gameplay with no ad/IAP error surfaced to a child.
