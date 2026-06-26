# Workflow: Add In-App Purchases (`in_app_purchase`)

**Goal:** Integrate store purchases correctly: products defined in both stores, a buy flow,
**restore** (required), purchase verification, and — for any kids-facing purchase — a **parental
gate**.

**When to use:** the [`add-monetization`](add-monetization.md) gate chose IAP (consumables,
non-consumables, or subscriptions).

**When NOT to use:** to gate core accessibility/safety behind payment, or to add manipulative pricing.
Kids titles may offer **only** parental-gated, non-targeted purchases — re-check the gate.

**Prerequisites**
- [`references/monetization-policy`](../references/monetization-policy.md) §IAP and
  [`checklists/monetization`](../checklists/monetization.md).
- Package: `in_app_purchase` (official). Products configured in App Store Connect **and** Play Console.

> **Doctrine:** sell only through the platform billing API (no external purchase links — an App Review
> reject and, in a kids app, a hard policy line). **Restore purchases** is mandatory for
> non-consumables/subscriptions. No dark patterns. Server-side verification is recommended; if you
> can't, say so in the handoff (don't pretend a client check is secure).

---

## STEP 1 — Define products in both stores

- **App Store Connect:** create the in-app purchases / subscriptions; note the product ids.
- **Play Console:** create the matching in-app products / subscriptions with the **same ids**.
- Types: **consumable** (coins, spent), **non-consumable** (permanent unlock, "remove ads"),
  **subscription** (recurring). Pick the simplest that fits.

**Done when:** every product exists in both stores with identical ids and clear, honest pricing/descriptions.

---

## STEP 2 — Add the SDK and query products

```bash
flutter pub add in_app_purchase
```

On startup: check `InAppPurchase.instance.isAvailable()`, then `queryProductDetails({ids})`. Render
the real localized price from `ProductDetails.price` — never a hard-coded price string.

**Done when:** products load and the UI shows store-provided localized prices.

---

## STEP 3 — Buy flow + the purchase stream

Listen to `InAppPurchase.instance.purchaseStream` and handle **every** status: `pending`, `purchased`,
`restored`, `error`, `canceled`. On `purchased`/`restored`: verify (Step 5), deliver the entitlement,
then **`completePurchase`** (required — an uncompleted purchase is refunded/retried). Use
`buyConsumable` for consumables, `buyNonConsumable` otherwise.

```dart
sub = InAppPurchase.instance.purchaseStream.listen((purchases) {
  for (final p in purchases) {
    switch (p.status) {
      case PurchaseStatus.purchased:
      case PurchaseStatus.restored:
        // verify → grant entitlement → then:
        if (p.pendingCompletePurchase) InAppPurchase.instance.completePurchase(p);
      case PurchaseStatus.error: /* surface a friendly message */
      case PurchaseStatus.pending: /* show a spinner; don't grant yet */
      case PurchaseStatus.canceled: /* no-op */
    }
  }
});
```

**Done when:** all five statuses are handled and every grant is followed by `completePurchase`.

---

## STEP 4 — Restore purchases (mandatory)

Add a visible **Restore Purchases** action that calls `InAppPurchase.instance.restorePurchases()`;
entitlements arrive via the same stream as `restored`. Both stores require this for
non-consumables/subscriptions — missing it is a guaranteed reject.

**Done when:** a Restore button re-grants non-consumables/subscriptions on a fresh install.

---

## STEP 5 — Verify the purchase (and be honest about it)

Validate `purchaseDetails.verificationData` (the receipt/token) **server-side** against Apple/Google
where you can — a purely client-side check is spoofable. If the game is offline-only with no backend,
do the best local check and **document the limitation** in the handoff; don't claim it's secure.

**Done when:** purchases are verified server-side, or the client-only limitation is documented.

---

## STEP 6 — Parental gate (kids-facing purchases)

If a purchase is reachable in a child-facing flow, put it behind a **parental gate** (e.g. a
math/hold challenge an adult passes) before the buy sheet — required by Apple Kids Category and Google
Play Families. Keep the core pure: billing lives in `lib/data/purchase_service.dart` behind an
interface; `models/`/`systems/` never import `in_app_purchase`.

**Done when:** every kids-facing purchase is gated, and no billing import leaks into the core.

---

## STEP 7 — Verify

```bash
scripts/dart-doctor.py . --only kids-safety
```

Walk [`checklists/monetization`](../checklists/monetization.md): restore works, all stream statuses
handled, `completePurchase` always called, prices store-provided, no external purchase links, parental
gate on kids purchases, sandbox-tested on both stores.

**Done when:** the checklist passes and a sandbox purchase + restore round-trips on iOS and Android.

---

## Master "done when"
1. Matching products in both stores with honest pricing (Step 1).
2. Products load; localized prices shown (Step 2).
3. All purchase-stream statuses handled; `completePurchase` always called (Step 3).
4. Restore Purchases works (Step 4).
5. Verification done server-side, or its absence documented (Step 5).
6. Kids-facing purchases gated; core stays pure (Step 6); checklist passes (Step 7).

## Handoff
Report: products + types, the buy/restore flow, **verification approach (and any limitation)**, the
parental-gate placement, where the purchase service lives, checklist results, and risks. **No
store-approval guarantee.**

## Common pitfalls
- **No Restore Purchases** — a guaranteed reject for non-consumables/subscriptions.
- **Not calling `completePurchase`** — the store refunds/retries the transaction.
- **Hard-coded prices** — show the store's localized `ProductDetails.price`.
- **External purchase links** — banned by both stores (and a kids hard line).
- **Claiming client-side verification is secure** — it isn't; verify server-side or disclose the gap.
- **Ungated kids purchases** — violates Kids Category / Families; add a parental gate.

## See also
- [`references/monetization-policy`](../references/monetization-policy.md) §IAP, [`checklists/monetization`](../checklists/monetization.md).
- [`add-monetization`](add-monetization.md) — the audience gate; [`add-ads`](add-ads.md) — the 13+ ad path.
- [`references/accessibility-child-safety`](../references/accessibility-child-safety.md) — parental-gate requirements.
