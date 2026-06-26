# Workflow: Add Monetization (the audience gate first)

**Goal:** Decide **whether and how** a game may earn money — and route to the right implementation —
without ever crossing the kids-safety line. This is the umbrella workflow; ads and IAP have their own.

**When to use:** the user asks to monetize, or you're scoping a business model before release.

**When NOT to use:** a kids/Families title with any ads/tracking intent — the answer there is **no**
(see Step 1); don't proceed to ads.

**Prerequisites**
- [`references/monetization-policy`](../references/monetization-policy.md) — the binding rules
  (audience gate, allowed mechanisms, forbidden patterns). This operationalizes it.
- [`checklists/monetization`](../checklists/monetization.md) — the pre-ship gate.

> **Doctrine:** the audience decides everything. A child-directed or mixed-audience-with-children
> title gets **no ads, no tracking, no AdvertisingId, no behavioral targeting** — full stop. Premium
> (paid up-front) or genuinely no monetization are the kid-safe options. No dark patterns, ever.

---

## STEP 1 — Audience gate (decide before anything)

Answer one question, honestly: **is any part of the audience children?**

| Audience | Allowed | Forbidden |
| --- | --- | --- |
| **Kids / Families** (Apple Kids Category, Google Play Families, COPPA/GDPR-K) | premium up-front; optional **parental-gated** non-consumable IAP (no targeting) | ads, analytics/tracking, AdvertisingId (IDFA/GAID), behavioral targeting, external purchase links |
| **General (13+)** | ads, IAP, subscriptions — with consent/ATT | dark patterns, deceptive pricing, undisclosed tracking |
| **Mixed (has children)** | inherits the **kids** rules for everyone (you can't reliably separate) | same as kids |

If children are in scope → **stop**. Premium or no-monetization only; skip ads entirely. Document the
decision in the handoff.

**Done when:** the audience is written down and the allowed mechanism set is fixed.

---

## STEP 2 — Choose the model (13+ only past here)

- **Premium (paid up-front)** — simplest, kid-safe, no SDK. Set the price tier in the store; done.
- **In-app purchases** — consumables (coins), non-consumables (unlock), subscriptions. →
  [`add-in-app-purchases`](add-in-app-purchases.md).
- **Ads** — banner/interstitial/rewarded, **13+ only**. → [`add-ads`](add-ads.md).
- **Hybrid** — IAP + a "remove ads" purchase. Allowed for 13+; keep it non-manipulative.

Pick the least intrusive model that fits. Prefer premium/IAP over ads for a calmer UX and easier
privacy posture.

**Done when:** the model is chosen with a one-line justification and routed to the right sub-workflow.

---

## STEP 3 — Keep the core pure

Monetization is an **edge concern** — it lives in `lib/data/`/a service, never in `lib/models/` or
`lib/systems/`. The pure-Dart game core must stay free of ad/billing imports so it still `dart test`s
on the VM. The store/ad SDK is injected behind a plain interface the UI calls.

**Done when:** no `package:google_mobile_ads`/`in_app_purchase` import appears under `models/`/`systems/`.

---

## STEP 4 — Verify against the gate

```bash
scripts/dart-doctor.py . --only kids-safety        # flags ad/analytics/AD_ID in a kids build
```

Walk [`checklists/monetization`](../checklists/monetization.md): consent/ATT where needed, no dark
patterns, prices clear, restore-purchases present (IAP), parental gate on any kids-facing purchase.

**Done when:** dart-doctor kids-safety is clean for the chosen audience and the monetization checklist passes.

---

## Master "done when"
1. Audience gated; kids → no ads/tracking, mechanism set fixed (Step 1).
2. Model chosen and justified; routed to ads/IAP sub-workflow (Step 2).
3. Monetization code is edge-only; core stays pure & VM-testable (Step 3).
4. dart-doctor kids-safety clean; monetization checklist passes (Step 4).

## Handoff
Report: the **audience decision** and why, the model chosen, where the code lives (edge service),
dart-doctor + checklist results, and a risk list (consent, store-policy, age-rating). **No
store-approval guarantee.**

## Common pitfalls
- **Monetizing a kids title with ads** — the most common policy violation; the gate forbids it.
- **"Mixed audience" loophole** — if children can use it, kids rules apply to everyone.
- **Billing logic in the core** — breaks VM tests and the layer seam; keep it at the edge.
- **Dark patterns** — fake timers, disguised ads, confusing buy buttons → rejection and harm.

## See also
- [`references/monetization-policy`](../references/monetization-policy.md), [`checklists/monetization`](../checklists/monetization.md).
- [`add-ads`](add-ads.md), [`add-in-app-purchases`](add-in-app-purchases.md) — the 13+ implementations.
- [`references/accessibility-child-safety`](../references/accessibility-child-safety.md) — the kids line.
