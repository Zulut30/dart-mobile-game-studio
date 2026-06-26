# Workflow: Add Ads (13+ titles only — `google_mobile_ads`)

**Goal:** Integrate ads in a **general-audience (13+)** game correctly: consent/ATT, non-personalized
fallback, the right format, and zero kids exposure.

**When to use:** the [`add-monetization`](add-monetization.md) gate chose ads for a **confirmed 13+**
audience.

**When NOT to use:** **any** title with children in the audience. Stop — ads are forbidden for
kids/Families (Apple Kids Category, Google Play Families). There is no compliant kids-ads path here.

**Prerequisites**
- [`references/monetization-policy`](../references/monetization-policy.md) §Ads, and
  [`checklists/monetization`](../checklists/monetization.md).
- AdMob account + ad unit ids. Package: `google_mobile_ads` (justify per
  [`package-policy`](../references/package-policy.md)).

> **Gate recap:** confirm 13+ in writing before adding the SDK. The mere presence of
> `google_mobile_ads` or the `AD_ID` permission in a kids build is a policy violation — dart-doctor
> flags it (`--only kids-safety`).

---

## STEP 1 — Re-confirm audience, then add the SDK

```bash
scripts/dart-doctor.py . --only kids-safety   # must be intentionally 13+ before this step
flutter pub add google_mobile_ads
```

Set the AdMob app id in `AndroidManifest.xml` (`<meta-data com.google.android.gms.ads.APPLICATION_ID>`)
and iOS `Info.plist` (`GADApplicationIdentifier`). Initialize once: `MobileAds.instance.initialize()`.

**Done when:** 13+ is confirmed in the handoff and the SDK initializes once at startup.

---

## STEP 2 — Consent & ATT (before any ad loads)

- **iOS App Tracking Transparency:** request authorization (`AppTrackingTransparency`) **before** any
  tracking/personalized ad; if denied, serve **non-personalized** ads only — never block the game.
- **EU/UK consent:** use a CMP (e.g. the UMP SDK) to gather GDPR consent; respect the result.
- Build a **non-personalized fallback** that works when consent/ATT is denied — the game must remain
  fully playable either way.

**Done when:** ATT + CMP run before the first ad, and a denied result yields working non-personalized ads.

---

## STEP 3 — Pick the format & placement (non-intrusive)

| Format | Use | Rule |
| --- | --- | --- |
| **Banner** | a fixed strip outside the play area | never overlap controls or the playfield |
| **Interstitial** | at a natural break (level end), not mid-action | bounded frequency; never on a tap target |
| **Rewarded** | opt-in for a bonus (extra life, coins) | clearly labeled, always skippable to decline |

Load ads off the gameplay path (not in `update()`/`build()`); preload, then show at the boundary.
Rewarded is the most user-respecting; avoid interstitials that interrupt a run.

**Done when:** the format suits the moment, ads never cover controls, and loading is off the hot path.

---

## STEP 4 — Keep the core pure; isolate the SDK

Ads live in a `lib/data/ad_service.dart` behind a plain interface (`showRewarded()` → `Future<bool>`);
the pure core and UI call the interface, never the SDK directly. This keeps `models/`/`systems/`
VM-testable and lets you stub ads in tests.

**Done when:** no `package:google_mobile_ads` import under `models/`/`systems/`; the UI depends on the interface.

---

## STEP 5 — Verify

```bash
scripts/dart-doctor.py . --only kids-safety        # confirms this is a deliberate 13+ build
```

Walk [`checklists/monetization`](../checklists/monetization.md): ATT/CMP present, non-personalized
fallback works, frequency capped, no ads near accidental taps, test ad unit ids swapped for real ones,
age rating updated to reflect ads.

**Done when:** the checklist passes and ads degrade gracefully without consent.

---

## Master "done when"
1. 13+ confirmed; SDK initialized once (Step 1).
2. ATT + CMP gate the first ad; non-personalized fallback works (Step 2).
3. Format/placement non-intrusive; loading off the hot path (Step 3).
4. SDK isolated at the edge; core stays pure (Step 4).
5. Monetization checklist + dart-doctor kids-safety pass; age rating updated (Step 5).

## Handoff
Report: the **13+ audience confirmation**, formats + placements, consent/ATT handling, where the ad
service lives, checklist results, and risks (privacy, age-rating, store policy). **No approval
guarantee.**

## Common pitfalls
- **Ads in a kids/mixed build** — forbidden; this whole workflow is 13+ only.
- **Personalized ads without consent/ATT** — a privacy violation; default to non-personalized on denial.
- **Interstitials mid-action / over controls** — accidental taps, rejections, bad UX.
- **Shipping test ad unit ids** (or real ids in debug) — swap deliberately for release.
- **Ad SDK in the core** — breaks VM tests; isolate behind an interface.

## See also
- [`references/monetization-policy`](../references/monetization-policy.md) §Ads, [`checklists/monetization`](../checklists/monetization.md).
- [`add-in-app-purchases`](add-in-app-purchases.md) — often a calmer alternative ("remove ads").
- [`add-monetization`](add-monetization.md) — the audience gate that routes here.
