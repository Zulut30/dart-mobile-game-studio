# Asset Licensing And Provenance Gate

Use before a release candidate whenever the app ships images, sprites, fonts, audio, video, copy,
or generated media. This is an evidence checklist, not a legal opinion or a store-approval promise.

## Inventory

- [ ] Every shipped file under `assets/` appears in an inventory with: path, purpose, creator/source,
      license or ownership basis, proof location, and modification notes.
- [ ] The inventory includes app icons, splash art, screenshots, store artwork, fonts, music, sound
      effects, voice, localization copy, and third-party package assets.
- [ ] Unused, duplicate, sample, and placeholder assets are removed from the release bundle.
- [ ] Asset declarations in `pubspec.yaml` match the files that are actually shipped.

Suggested record:

| Path | Type | Creator/source | Rights basis | Proof | Modified | Release status |
|---|---|---|---|---|---|---|
| `assets/images/example.png` | image | studio placeholder | self-authored | `docs/licenses/` | no | replace |

## Rights And Provenance

- [ ] Each asset is self-authored, commissioned with transferable usage rights, user-owned with
      written permission, public domain with verified status, or covered by a compatible license.
- [ ] No ripped game sprites, characters, logos, screenshots, music, sound effects, fonts, or other
      material copied from an existing product or franchise are present.
- [ ] License obligations are recorded and satisfied: attribution, notice text, redistribution
      conditions, source availability, or modification disclosure where applicable.
- [ ] Commissioned work has a written scope covering mobile apps, store marketing, territories,
      duration, modification, and sublicensing/distribution through Apple and Google.
- [ ] Generated-media records retain the tool, account, date, prompt/reference provenance, edits,
      and the applicable service terms reviewed for commercial use.
- [ ] No generated asset intentionally imitates a living artist, protected character, trademark,
      identifiable person, or supplied reference without documented permission.

## Fonts, Icons, Audio, And Voice

- [ ] Every font license permits embedding and redistribution in a mobile application.
- [ ] Required font license files and attribution notices ship in the repository/app as required.
- [ ] Platform icons are used according to the platform/library terms; third-party icon packs have
      their own inventory entries.
- [ ] Music, loops, samples, and sound effects have explicit app-distribution rights; a streaming or
      personal-listening subscription is not treated as a production license.
- [ ] Voice recordings have performer consent covering the intended app and audience.

## Children And Privacy

- [ ] Assets and copy are age-appropriate for the declared audience and store age-rating answers.
- [ ] No child image, voice, name, school, location, account identifier, or other personal data is
      included without an approved legal/privacy basis and documented consent.
- [ ] Store screenshots and previews contain no real child data, notifications, account details,
      device identifiers, or production secrets.
- [ ] External links, promotions, purchases, and branded content follow the parental-gate and kids
      policies in `references/accessibility-child-safety.md`.

## Technical Release Checks

- [ ] Image dimensions, color space, transparency, compression, and memory cost fit the target
      devices; oversized textures are resized before bundling.
- [ ] Audio is normalized, compressed appropriately, and tested with mute/background/interruption.
- [ ] File names are lowercase and stable; no spaces, accidental Unicode variants, or case-only
      collisions that behave differently on macOS and Android/Linux.
- [ ] The release build has been inspected to confirm that rejected or placeholder assets are not
      present in the final AAB/IPA bundle.

## Release Evidence

- [ ] `docs/licenses/` (or the project-equivalent evidence folder) contains the inventory, license
      texts, permissions, invoices/contracts where appropriate, and attribution copy.
- [ ] A human owner is named for unresolved rights questions.
- [ ] All blocking rows are resolved before TestFlight/Play internal promotion to production.
- [ ] The handoff lists remaining assumptions and requests qualified legal review for uncertainty.
