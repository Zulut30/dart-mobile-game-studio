# Workflow: Debug Common Errors (build / runtime / analyzer / jank)

**Goal:** Go from a red build, a runtime crash, an analyzer wall, or visible jank to a **fixed and
verified** state — cheaply, without pasting 2000 log lines into context.

**When to use:** `flutter build`/`run` fails (Gradle on Android, Xcode/CocoaPods on iOS, pub on
either), the app throws at runtime, `dart analyze` is noisy, or the game janks.

**When NOT to use:** Greenfield scaffolding (use [`create-new-game`](create-new-game.md)); a pure
perf pass with no error (use [`run-performance-audit`](run-performance-audit.md)).

**Prerequisites**
- The three tools this workflow drives: [`scripts/triage-log.py`](../scripts/triage-log.py) (shrink a
  log), [`scripts/dart-doctor.py`](../scripts/dart-doctor.py) (localize), and the
  [`references/common-pitfalls`](../references/common-pitfalls.md) catalog (classify + fix).
- For dependency/codegen fixes, fence the retry in [`scripts/safe-run.sh`](../scripts/safe-run.sh) so a
  half-fix never persists. See [`references/ci-and-automation`](../references/ci-and-automation.md).

> **Doctrine:** never paste a raw multi-thousand-line log into the model. Triage first, classify by
> code, fix the **cause** (not the symptom), then re-verify with a real command. Report honestly — a
> fix you didn't re-run is a hypothesis, not a fix.

---

## STEP 1 — Capture the log to a file

Redirect **both** streams so the real error (often on `stderr`) is captured, and keep the file:

```bash
flutter build apk 2>&1 | tee /tmp/build.log        # or: flutter run, dart test, dart analyze
```

**Done when:** the full output is in a file you can re-read, not just scrolled past in the terminal.

---

## STEP 2 — Triage it (shrink to signal + a likely cause)

```bash
scripts/triage-log.py /tmp/build.log                 # ~2000 lines → ~10-25 + likely cause(s)
scripts/triage-log.py --max-lines 40 /tmp/build.log  # widen if the cause was truncated
```

Read the **toolchain** line and the **likely cause(s)** list first; they usually name the fix
category. Only then read the kept lines. This is what keeps the debug loop cheap.

**Done when:** you have a one-line hypothesis of what failed and where (which toolchain, which file/dep).

---

## STEP 3 — Classify by catalog code

Map the triaged signature to a [`common-pitfalls`](../references/common-pitfalls.md) classifier code via
its symptom→cause→fix matrix. The high-frequency ones:

| Triaged signature | Code | One-line fix |
| --- | --- | --- |
| `version solving failed` / `Because … depends on` | `DART_DYNAMIC_TYPING`* | Align/relax version constraints in `pubspec.yaml`; re-run pub get (*dependency, not typing — see below) |
| `Manifest merger failed` | `FLUTTER_LAYOUT_CONSTRAINTS`* | Reconcile `minSdk`/permissions/`<application>` attrs across plugins in `AndroidManifest.xml` |
| `Could not resolve …` (Gradle) | — | Check `repositories{}` + network/proxy and the coordinate/version |
| `Unsupported class file major version` | — | Align the Gradle/Kotlin JDK (`org.gradle.java.home` / `JAVA_HOME`) |
| `No such module 'Flutter'` / `Undefined symbols` (iOS) | `FLAME_ASSET_LIFECYCLE`* | `pod install`, open the `.xcworkspace`, check the deployment target |
| `…requires a provisioning profile` | — | Set a Team / profile in Xcode → Signing & Capabilities |
| `RenderFlex overflowed` | `FLUTTER_LAYOUT_CONSTRAINTS` | Wrap the flex child in `Expanded`/`Flexible`; ellipsis the text |
| `Vertical viewport was given unbounded height` | `FLUTTER_LAYOUT_CONSTRAINTS` | `Expanded(child: ListView…)` |
| `Null check operator used on a null value` | `DART_NULL_SAFETY` | Remove the `!`; promote-and-guard or `(x as T?) ?? fallback` |
| `LateInitializationError` | `DART_NULL_SAFETY` | Initialize in `onLoad`/constructor, or make it nullable with a fallback |
| `setState() called after dispose()` | `FLUTTER_LIFECYCLE_SETSTATE` | `cancel`/`removeListener` in `dispose`; add an `if (!mounted) return;` guard |
| `fromCache` throws / empty sprite | `FLAME_ASSET_LIFECYCLE` | `await images.load(...)` in `onLoad` before `fromCache` |
| FPS decays over a session | `FLAME_HOT_PATH_ALLOCATION` | Hoist `Paint`/`Vector2`; pool spawns |

(*The matrix code is for the catalog's full entry; some build-tool errors live only in the matrix, not
a `*_*` code — use the row's fix directly.)

**Done when:** the failure has a code (or a matrix row) and a concrete fix target.

---

## STEP 4 — Localize in the codebase

Confirm the site before editing:

```bash
scripts/dart-doctor.py . --only performance     # or architecture / dart-quality / kids-safety …
scripts/dart-doctor.py . --json --only dart-quality | python3 -m json.tool   # exact file:line list
```

dart-doctor's per-dimension scan gives you the exact `file:line` for null-safety, hot-path
allocation, `dt` clamping, layering, and kids-safety classes — the same codes the catalog uses. For a
build-tool error (Gradle/Xcode), the file is named in the triaged lines (`build.gradle`, `Podfile`,
`pubspec.yaml`).

**Done when:** you can point at the exact line(s) to change.

---

## STEP 5 — Apply the cause-level fix

Edit toward the catalog's **good** pattern, not a symptom patch (don't silence `RenderFlex` with a
fixed height that clips; bound it with `Expanded`). For a **dependency or codegen** change, fence the
retry so a half-run can't strand the tree:

```bash
# dependency conflict: edit pubspec.yaml, then re-resolve safely
scripts/safe-run.sh --stash --triage -- flutter pub get
# regenerate after a fix, atomically:
scripts/safe-run.sh --commit --commit-msg "fix: realign deps + regen" \
  -- dart run build_runner build --delete-conflicting-outputs
```

**Done when:** the edit matches the catalog's recommended pattern and (for deps/codegen) ran under
`safe-run.sh`.

---

## STEP 6 — Re-verify with a real command

```bash
scripts/pub-get-if-changed.sh                 # only re-resolves if pubspec.lock moved
dart analyze --fatal-infos --fatal-warnings   # zero issues
dart test                                      # pure-core
flutter build apk 2>&1 | tee /tmp/build.log    # the originally-failing command
```

If it still fails, loop to Step 2 with the **new** log (the signature usually moved — that's
progress). Never declare it fixed off a stale log.

**Done when:** the originally-failing command now succeeds, and you saw the output.

---

## Master "done when"
1. The failing command was captured and triaged (not eyeballed).
2. The failure is classified to a catalog code / matrix row.
3. The fix targets the cause and matches the catalog's good pattern.
4. The originally-failing command re-runs green — with real output captured.

## Handoff
Report: the original error (one line), its classifier code, the cause, the fix (files changed), and
the **re-run output** that proves it. If you couldn't re-run (no toolchain/device), say so and give the
exact command — a fix you didn't verify is a hypothesis.

## Common pitfalls
- **Pasting the raw log** — burns tokens and buries the cause. Triage first, always.
- **Fixing the symptom** — a fixed height "fixes" overflow but clips on another device; bound it instead.
- **Declaring victory off a stale log** — re-run the exact failing command; the signature must be gone.
- **Unfenced codegen retries** — a half-run `build_runner` leaves a broken tree; use `safe-run.sh`.
- **Chasing the wrong toolchain** — read triage's toolchain line; a "Flutter" error inside a Gradle
  log is often a plugin's Android config, not your Dart.

## See also
- [`references/common-pitfalls`](../references/common-pitfalls.md) — the full symptom→cause→fix matrix + codes.
- [`references/ci-and-automation`](../references/ci-and-automation.md) — preflight, safe-run, triage, cache.
- [`run-performance-audit`](run-performance-audit.md) — when the problem is jank, not an error.
