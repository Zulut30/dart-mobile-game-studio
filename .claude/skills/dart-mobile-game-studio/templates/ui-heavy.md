# Template: UI-heavy (menus / economy / progression)

A **design brief + architecture skeleton** for a game that is mostly screens and systems rather than
twitch play — idle/clicker, tycoon-lite, collection/gacha-style (no real-money loot), shop/upgrade
manager. Self-contained. Lean on [`references/production-quality.md`](../references/production-quality.md)
(navigation, state-at-scale, theming) and [`references/ui-and-animations.md`](../references/ui-and-animations.md).

**Mode:** Flutter-widgets-only, with **real navigation** (`go_router`) and a deliberate **state
management** choice — this genre lives or dies by UI architecture, not a render loop.

---

## Mini-GDD (filled example — adapt)

- **One-liner:** `<tap to earn; spend on upgrades that earn faster>`.
- **Audience & age:** ages 8+ (general) or kids with the kids bar; long, returning sessions.
- **Core loop:** earn resource → spend on upgrades → earn faster → unlock content → repeat.
- **Primary verb:** tap / select; lots of menu navigation.
- **Failure model:** **no-fail** progression; the "challenge" is optimization, not loss.
- **Win / progression:** upgrade tree, unlocks, prestige/reset (optional), achievements; offline earnings.
- **Art:** clean Material/Cupertino UI; iconography over illustration; readable numbers (formatting!).
- **Scope (in):** one resource, ~5 upgrades, save/load, one earn loop, a shop screen.
- **Cut-line (later):** prestige, achievements, multiple resources, themes, cloud save.

## Architecture skeleton (pure Dart, no Flutter import in the core)

```
lib/models/   economy_state.dart # immutable: resources, ownedUpgrades, lastSeen; copyWith, ==/hashCode
              upgrade.dart        # immutable def: id, baseCost, costGrowth, effect; (data, not code)
lib/systems/  economy.dart        # buy(state, upgradeId) / tick(state, dt) -> new state; pure
              offline_earnings.dart# earnings(now - lastSeen, rate); pure (inject the clock!)
              save_repository.dart # interface; JSON/prefs impl at the edge (lib/data/)
lib/app/      router.dart         # go_router: /menu /play /shop /settings
lib/widgets/  play_screen.dart shop_screen.dart upgrade_tile.dart resource_hud.dart
```

- **Economy is pure Dart, balance is data.** Upgrade costs/effects live in JSON/const tables, not
  hard-coded in widgets — so a `balance-economist` can tune them and `dart test` can verify curves.
- **Real navigation** — `go_router` routes (not `setState`-toggled screens) so back/deep-links/transitions work.
- **Scoped rebuilds** — drive each HUD number from the smallest listenable slice (`ValueListenableBuilder`/
  `Selector`); never rebuild the whole screen when one counter ticks.
- **Inject the clock** for offline earnings (`DateTime Function()`), never `DateTime.now()` in the
  core — so timed economy is deterministic and testable.
- **Number formatting** (`1.2K`, `3.4M`) is a pure helper, unit-tested.

## Genre specifics (what matters here)

- **No dark patterns / no real-money pressure**, especially for kids — see [`references/monetization-policy.md`](../references/monetization-policy.md).
  Any IAP is 13+ and parental-gated; "gacha" uses earned currency only, odds disclosed.
- **Save reliability** — persist on change + on background; migrate schema versions; never lose progress.
- **Performance at scale** — long lists are `.builder`; no rebuild-the-world `setState`; const subtrees.
- **Big numbers** — use `BigInt`/careful formatting; don't overflow or render `1e21` to a child.

## Genre checklist

- [ ] Economy/offline logic is pure Dart with an **injected clock**; curves unit-tested (`dart test`).
- [ ] Balance (costs/effects) is data (JSON/const), not hard-coded in widgets.
- [ ] `go_router` navigation; scoped rebuilds (no setState-the-world); long lists `.builder`.
- [ ] Save persists on change + background, migrates versions, survives relaunch.
- [ ] No dark patterns; any IAP 13+ + parental-gated (per monetization-policy); kids build stays offline/no-tracking.
- [ ] No `package:flutter` in `models/`/`systems/`.

## See also
- [`references/production-quality.md`](../references/production-quality.md) · [`references/ui-and-animations.md`](../references/ui-and-animations.md) · [`references/codegen-and-boilerplate.md`](../references/codegen-and-boilerplate.md).
- [`workflows/add-state-management.md`](../workflows/add-state-management.md) · [`add-navigation.md`](../workflows/add-navigation.md) · [`add-save-system.md`](../workflows/add-save-system.md) · [`add-monetization.md`](../workflows/add-monetization.md).
