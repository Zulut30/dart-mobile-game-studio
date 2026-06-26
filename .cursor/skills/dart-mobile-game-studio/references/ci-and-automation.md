# Safe automation & CI (running the skill unattended)

When an agent drives the build on a real or fresh machine, four things bite that don't show up in a
hand-run session: a **missing toolchain**, a **destructive command on a dirty tree**, a **2000-line
build log** blowing the context budget, and a **needless `pub get`** burning minutes every step. This
file is the policy + the four scripts that handle each. Wire them into every automated or long-running
workflow; they degrade gracefully when a toolchain or git isn't present.

| Hazard | Script | What it guarantees |
|---|---|---|
| Environment Lock | `scripts/flutter-preflight.sh` | reports/gates toolchain + git + project; never crashes a later step with a cryptic error |
| Sandboxing / broken state | `scripts/safe-run.sh` | savepoint → run → atomic commit (ok) / rollback (fail); the safety net never loses your work |
| Log noise / token cost | `scripts/triage-log.py` | ~2000 lines → ~10–25 + likely cause; cheap, fast model input |
| Slow re-init | `scripts/pub-get-if-changed.sh` | skips `pub get` when `pubspec.lock` is unchanged |

## Order of operations (automated build/codegen run)

```
1. flutter-preflight.sh --require dart            # (+ flutter/android/xcode as the step needs)
       └─ exit ≠ 0 → stop early with the install hint; don't enter a build you can't finish
2. pub-get-if-changed.sh                          # resolve deps only if pubspec.lock moved
3. safe-run.sh --stash --commit --triage -- <codegen / build>   # the destructive step, fenced
       ├─ success → atomic "chore(auto): …" commit, your stashed edits restored on top
       └─ failure → working tree rolled back to the start commit; log triaged to a few lines
4. (read the triage summary, fix, re-run from step 2)
```

Pure-Dart core work (`dart test` on `lib/models/`+`lib/systems/`) needs none of this — it has no
device, no codegen, no Gradle. Reach for these scripts at the **edges**: dependency changes, code
generation, and platform builds.

## 1. Environment Lock — `flutter-preflight.sh`

The skill's build/release steps assume a toolchain that a clean CI box or a new contributor may not
have. Preflight checks what's present (`dart`, `flutter`, Android SDK, Xcode, CocoaPods), the git
workspace (branch, dirtiness, detached HEAD), and the project (`pubspec.yaml`), then prints a report
and an exit code you can gate on.

```bash
scripts/flutter-preflight.sh                       # report only (exit 0)
scripts/flutter-preflight.sh --require dart        # exit 3 if dart is missing
scripts/flutter-preflight.sh --require flutter,android   # both required
scripts/flutter-preflight.sh --git-clean           # exit 4 if the tree is dirty
scripts/flutter-preflight.sh --json                # machine-readable
```

**Rule:** require only what the step actually needs. A `dart test` needs `dart`; an `appbundle` needs
`flutter,android`; an `ipa` needs `flutter,xcode`. Missing-but-not-required tools are reported, not
fatal — so a widgets-only game still passes on a box without the Android SDK.

## 2. Sandboxing — `safe-run.sh`

Codegen and `flutter clean` mutate files in place; a bad arg or a half-run leaves a broken tree.
`safe-run.sh` fences the command: it records the start commit, ensures a savepoint, runs, then either
commits the result atomically or rolls the tree back.

```bash
# regenerate serialization, commit the result atomically:
scripts/safe-run.sh --label "regen serialization" --commit \
  --commit-msg "chore(auto): regenerate json/freezed via build_runner" \
  -- dart run build_runner build --delete-conflicting-outputs

# clean on a dirty tree without losing your edits, triage on failure:
scripts/safe-run.sh --stash --triage -- flutter clean
```

**The safety net is itself safe.** Rollback is `git reset --hard <start>` + `git clean -fd`, which are
destructive, so safe-run **auto-rolls-back only when it can prove nothing is lost**:

- **clean tree** (default `--require-clean`) → reset+clean can't touch user work (there was none).
- **`--stash`** → your changes (incl. untracked, `-u`) are stashed first, then restored after.
- **`--allow-dirty`** → runs on a dirty tree but **disables** auto-rollback (you opted out of the net).

On a dirty tree with neither `--stash` nor `--allow-dirty`, it **refuses** (exit 3) rather than risk
your edits. Success path: commit the generated result first (if `--commit`), then `git stash pop` your
own edits back on top. `--commit` respects pre-commit hooks (it won't force past a failing gate).

**Autonomy pattern:** for a fully unattended regen, `--stash --commit` yields a clean atomic commit
on success and a pristine tree on failure — nothing half-generated ever persists.

## 3. Log Triage — `triage-log.py`

A failed Gradle/Xcode build prints thousands of lines; piping all of it into a model is slow and
expensive. `triage-log.py` keeps only the high-signal lines (+ context), names the toolchain, and
emits a ranked likely-cause list.

```bash
flutter build apk 2>&1 | scripts/triage-log.py            # live
scripts/triage-log.py --max-lines 40 --context 2 build.log
scripts/triage-log.py --format json build.log             # for programmatic use
```

It scores lines by strength: **strong** signatures (`BUILD FAILED`, `Manifest merger failed`,
`error:`, `version solving failed`, `Undefined symbols`, `No such module`, …) always survive
truncation; weak/progress lines (`> Task`, a lone `FAILED`) only fill the remaining budget, and when
hits exceed `--max-lines` the ones **nearest the end** win (errors cluster after the progress noise).
Cause hints map a signature to a one-line remedy (dependency conflict → align pubspec constraints;
Manifest merger → reconcile minSdk/permissions; `No such module` → `pod install`; signing → set a
Team). It is heuristic — when no signature matches it says so; skim the raw tail or add a pattern.

## 4. Build cache — `pub-get-if-changed.sh`

`flutter pub get` is the reflexive first step but it's slow; re-running it when nothing changed wastes
minutes. This hashes the dependency inputs (`pubspec.lock` + `pubspec.yaml`) into the project's
gitignored `.dart_tool/.skill_pub_hash` and skips `pub get` when the hash is unchanged **and** packages
are already resolved (`package_config.json` present).

```bash
scripts/pub-get-if-changed.sh                 # pub get only if inputs changed
scripts/pub-get-if-changed.sh --check-only    # exit 0 = up-to-date, 10 = stale (no run)
scripts/pub-get-if-changed.sh --force         # always run + refresh the cache
```

The cache lives under `.dart_tool/` (already gitignored by Flutter/Dart), so it never touches tracked
files, and it only ever runs the project's own `pub get` — never `clean` or anything destructive. It
refreshes the cache from the **post**-resolution lock hash, so a `pubspec.yaml` edit that changes the
resolved versions correctly invalidates it next run.

## CI note

The repo's GitHub Actions job is structure-only today (validate-skill.sh — no Dart toolchain), which
keeps it green without an SDK. When the example app lands, add a Dart job
(`dart-lang/setup-dart`) that runs `flutter-preflight.sh --require dart`, then
`pub-get-if-changed.sh`, then `dart format`/`analyze`/`test` — and pipe any failing platform build
through `triage-log.py` so CI logs stay readable. See [testing-and-release.md](testing-and-release.md)
and [release-policy.md](release-policy.md).
