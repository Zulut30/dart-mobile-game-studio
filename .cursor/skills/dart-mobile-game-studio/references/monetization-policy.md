# Monetization policy

How to add ads, in-app purchases, and subscriptions to a Flutter game **safely** — and when not to.
Monetization is the area most likely to get a game rejected or fined, especially for children.
This policy gates it by audience first; mechanics second. No revenue guarantee, no legal advice.

## Step 0 — audience gate (decide before any monetization)
- **Kids build** (Apple Kids Category / primarily-child-directed / Google Play Families, under-13
  COPPA / GDPR-K): **NO third-party ads, NO ad SDKs, NO analytics/attribution, NO AdvertisingId
  (IDFA/GAID), NO behavioral targeting.** Allowed (with care): **non-targeted house promotion** of
  your own apps behind a parental gate, and **parent-gated IAP** that follows the families rules.
  The skill's default kids posture is **no monetization in the child-facing flow** — premium content
  unlocked by a one-time parent-gated purchase at most.
- **General build (13+)**: ads + IAP + subscriptions are allowed with consent, an **age gate**, a
  **parental gate** on purchases where minors may play, accurate store privacy disclosures, and ATT
  on iOS (see below). This is where `google_mobile_ads` + `in_app_purchase` live.

If unsure of audience → treat as a kids build → no ads/tracking.

## Ads (general builds only) — `google_mobile_ads`
- Use the **official `google_mobile_ads`** plugin (AdMob). Configure the app IDs in
  `Info.plist` (`GADApplicationIdentifier`) and `AndroidManifest.xml` (`APPLICATION_ID`); use **test
  ad unit IDs** during development, never your live IDs.
- **iOS App Tracking Transparency:** if any ad/SDK tracks, you must request ATT
  (`AppTrackingTransparency`) **before** tracking, and only personalize ads with consent; otherwise
  request non-personalized ads. EU users need a CMP/consent (UMP SDK).
- Formats and where they fit a game:
  - **Banner** — a small persistent ad; keep it off the gameplay surface (menus/results only).
  - **Interstitial** — full-screen at natural breaks (level end), never mid-action, never on every
    transition (frequency-cap it).
  - **Rewarded** — opt-in, gives a reward (extra life, hint, soft currency). The fairest format:
    the player chooses to watch. Grant the reward only on the SDK's `onUserEarnedReward`.
  - **Rewarded interstitial / app-open** — sparingly; respect Play/App Store placement rules.
- Load ahead of time, dispose ad objects, handle failure/no-fill gracefully (the game must play with
  ads off), and **pause the game** while a full-screen ad shows.

## In-app purchases & subscriptions — `in_app_purchase`
- Use the **official `in_app_purchase`** plugin (StoreKit on iOS, Google Play Billing on Android).
  Configure products in **App Store Connect** and **Google Play Console**; product IDs match.
- Product types: **consumable** (soft/hard currency, hints), **non-consumable** (premium unlock,
  remove-ads), **subscriptions** (battle pass / VIP). Map each to the right store product type.
- **Verify and deliver:** listen to `purchaseStream`; on a `purchased`/`restored` status, verify
  (server-side receipt validation for anything valuable), grant entitlement, then call
  `completePurchase`. Persist entitlements locally (and on a backend if you have one) so they survive
  reinstalls. Provide a **Restore Purchases** action (required for non-consumables/subscriptions).
- **Remove-ads** is a non-consumable that flips an entitlement consumed by the ad layer.
- **Currencies:** soft currency earned by play; hard currency bought/earned. Never make the game
  unwinnable without paying; no pay-to-progress walls in a kids title.

## Forbidden / high-risk (any audience)
- Loot boxes / gacha without odds disclosure; pay-to-win pressure; fake urgency, fake "free", or
  disguised buttons (dark patterns) — store-rejection and legal risk.
- Ads or purchase prompts that interrupt active gameplay, or that a child can trigger without a
  parental gate.
- Collecting personal data for ad targeting from anyone you can't lawfully target.
- Shipping live ad unit / product IDs untested, or claiming revenue/approval is guaranteed.

## Checklist before shipping monetization
- [ ] Audience gate decided; kids build has **no** ads/tracking.
- [ ] Test IDs in dev; live IDs only in release; products created in both stores.
- [ ] iOS ATT + EU consent handled; non-personalized fallback works.
- [ ] Full-screen ads pause the game; banners off the play surface; frequency-capped.
- [ ] IAP verified before granting; entitlements persisted; **Restore Purchases** present.
- [ ] Store **privacy** answers (App Privacy + Play Data safety) match the SDKs actually used.
- [ ] No dark patterns; purchases behind a parental gate where minors may play.
- [ ] The game is fully playable with ads disabled / purchases declined.

Route the privacy-disclosure and store-rules sign-off to `legal-compliance` and `security-auditor`;
release wiring to `release-engineer`. **No guarantees** — verify against current store policies.
