#!/usr/bin/env python3
"""triage-log.py — distill a giant Flutter/Gradle/Xcode build log into the few lines that matter.

A failed `flutter build` (Gradle on Android, Xcode/CocoaPods on iOS) can spit out thousands of lines.
Feeding all of it to a model is slow, expensive, and noisy. This filter keeps only the critical lines
(plus a little surrounding context), detects which toolchain failed, and emits a short, ranked
"likely causes" list — turning ~2000 lines into ~10-25 so the agent (or you) can spot the real problem
(e.g. a version conflict in pubspec.yaml, a Manifest merger clash, a missing iOS module) fast.

Lines are scored by signal strength: STRONG signatures (BUILD FAILED, Manifest merger, `error:`,
version solving failed, Undefined symbols…) always survive truncation; weak/progress lines (`> Task`,
a lone FAILED) only fill the remaining budget. When there are more hits than --max-lines, the ones
nearest the END of the log win — real errors cluster there, after the progress noise.

No third-party deps. Reads a file argument or stdin.

Usage:
  flutter build apk 2>&1 | scripts/triage-log.py            # filter a live build
  scripts/triage-log.py build.log                            # filter a saved log
  scripts/triage-log.py --max-lines 40 --context 2 build.log
  scripts/triage-log.py --format json build.log              # machine-readable

Exit: 0 if it ran (regardless of whether the underlying build passed); 2 on usage error.
"""
from __future__ import annotations

import argparse
import re
import sys

# Toolchain `detect` patterns — used only to label which tool produced the log (by match count).
DETECT: dict[str, list[str]] = {
    "dart/flutter": [r"\bFlutter\b", r"\bdart\b", r"\.dart[:\"]", r"pub get", r"package:flutter"],
    "gradle/android": [r"\bGradle\b", r"> Task :", r"\bAAPT2?\b", r"build\.gradle", r"BUILD FAILED"],
    "xcode/ios": [r"\bXcode\b", r"xcodebuild", r"\.xcodeproj", r"CompileSwift", r"\bRunner\b"],
    "cocoapods": [r"CocoaPods", r"pod install", r"Podfile", r"\bCDN\b"],
}

# STRONG = high-signal failure signatures; these always survive truncation.
STRONG = [
    r"\*\* BUILD FAILED \*\*",
    r"BUILD FAILED",
    r"FAILURE: Build failed",
    r"What went wrong:",
    r"Execution failed for task",
    r"Manifest merger failed",
    r"Could not (resolve|find|download|determine)",
    r"Duplicate class",
    r"Unsupported class file major version",
    r"version solving failed",
    r"Because .+ depends on",
    r"^\s*Error:",                       # dart
    r"\berror\s+[•·]\s",                 # dart analyze: "error • msg • file:line"
    r"^.*?\berror:",                     # gradle/xcode "error:"
    r"\bUnhandled exception\b",
    r"\bCompilation(Error| failed)\b",
    r"is not a subtype of",
    r"Undefined (name|class|method|getter|setter)",
    r"The (getter|method|setter|name) '[^']+' (isn't|is not) defined",
    r"Target of URI doesn't exist",
    r"Undefined symbols?",
    r"No such module",
    r"(Code Sign\w*|provisioning profile|no profiles for|requires a provisioning)",
    r"linker command failed",
    r"The following build commands failed",
    r"Unable to find a specification",
    r"^\s*\[!\]",                        # CocoaPods error marker
    r"RenderFlex overflowed",
    r"Failed assertion",
]

# WEAK = relevant but lower-signal (progress/detail); only fill the remaining budget.
WEAK = [
    r"> Task :.*FAILED",
    r"^\s*> (?!Task )",                  # gradle indents the actual cause with "> " (but not "> Task")
    r"(min|compile|target)SdkVersion",
    r"AAPT.*error|error: .*\.(xml|java|kt)",
    r"package .+ does not exist",
    r"\bNDK\b.*(not|error)",
    r"\bFAILED\b",
    r"CDN: .* (Repo update failed|error)",
    r"required a higher minimum deployment target",
    r"does not contain bitcode",
    r"Exception has occurred",
]

# regex → one-line remedy (first match per key wins; rough priority order).
CAUSE_HINTS: list[tuple[str, str]] = [
    (r"version solving failed|Because .+ depends on",
     "Dependency conflict in pubspec.yaml — align/relax the version constraints, then re-run pub get."),
    (r"Manifest merger failed",
     "AndroidManifest conflict — reconcile minSdk / permissions / <application> attrs across plugins."),
    (r"Could not (resolve|find|download)",
     "Gradle can't fetch a dependency — check repositories{} + network/proxy and the coordinate/version."),
    (r"Unsupported class file major version|Unsupported Java",
     "JDK mismatch — align the Gradle/Kotlin JDK with the project (check org.gradle.java.home / JAVA_HOME)."),
    (r"Duplicate class",
     "Two dependencies ship the same class — exclude one or align their versions."),
    (r"(min)SdkVersion",
     "minSdkVersion too low for a plugin — raise it in android/app/build.gradle."),
    (r"No such module|Undefined symbols",
     "iOS module/link error — run pod install, open the .xcworkspace, and check the deployment target."),
    (r"provisioning profile|Code Sign|no profiles for",
     "Signing — set a Team / provisioning profile in Xcode → Signing & Capabilities (or automatic signing)."),
    (r"Unable to find a specification|CDN: ",
     "CocoaPods spec/CDN issue — run 'pod repo update' (or bump the pod), then 'pod install'."),
    (r"Target of URI doesn't exist|Undefined name|isn't defined|does not exist",
     "Missing import or undeclared symbol/dependency — add the import or the package to pubspec.yaml."),
    (r"is not a subtype of",
     "Type mismatch — check generic/argument types (often a fromJson or an unchecked cast)."),
    (r"RenderFlex overflowed",
     "Layout overflow — wrap the flex child in Expanded/Flexible (common-pitfalls.md → FLUTTER_LAYOUT_CONSTRAINTS)."),
]


def compile_set(pats: list[str]) -> list[re.Pattern]:
    return [re.compile(p) for p in pats]


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True, description="Distill a build log to the lines that matter.")
    ap.add_argument("file", nargs="?", help="log file (default: stdin)")
    ap.add_argument("--max-lines", type=int, default=25, help="max critical lines to keep (default 25)")
    ap.add_argument("--context", type=int, default=1, help="lines of context around each hit (default 1)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args()

    try:
        raw = open(args.file, encoding="utf-8", errors="replace").read() if args.file else sys.stdin.read()
    except OSError as e:
        print(f"triage-log: cannot read {args.file}: {e}", file=sys.stderr)
        return 2

    lines = raw.splitlines()
    total = len(lines)

    detect = {name: compile_set(pats) for name, pats in DETECT.items()}
    strong = compile_set(STRONG)
    weak = compile_set(WEAK)

    # label toolchains by detect-match count
    scores = {name: 0 for name in DETECT}
    for ln in lines:
        for name, pats in detect.items():
            if any(p.search(ln) for p in pats):
                scores[name] += 1
    detected = sorted((n for n, s in scores.items() if s > 0), key=lambda n: -scores[n])

    # priority per line: 2 strong, 1 weak, 0 none
    def prio(ln: str) -> int:
        if any(p.search(ln) for p in strong):
            return 2
        if any(p.search(ln) for p in weak):
            return 1
        return 0

    hits = [(i, prio(ln)) for i, ln in enumerate(lines)]
    hits = [(i, p) for i, p in hits if p > 0]
    matched_text = "\n".join(lines[i] for i, _ in hits)

    truncated = 0
    if len(hits) <= args.max_lines:
        chosen = [i for i, _ in hits]
    else:
        # keep the strongest, and among equals prefer the END of the log (errors cluster there)
        ranked = sorted(hits, key=lambda t: (t[1], t[0]), reverse=True)[: args.max_lines]
        chosen = sorted(i for i, _ in ranked)
        truncated = len(hits) - args.max_lines

    # expand chosen hits with context
    keep: set[int] = set()
    for i in chosen:
        for j in range(max(0, i - args.context), min(total, i + args.context + 1)):
            keep.add(j)
    kept_sorted = sorted(keep)
    hit_set = {i for i, _ in hits}

    # likely causes over ALL matched text (not just the kept window)
    causes: list[str] = []
    for pat, hint in CAUSE_HINTS:
        if re.search(pat, matched_text) and hint not in causes:
            causes.append(hint)

    if args.format == "json":
        import json
        out = {
            "toolchains": detected or ["unknown"],
            "total_lines": total,
            "critical_hits": len(hits),
            "kept_lines": len(kept_sorted),
            "truncated_hits": truncated,
            "likely_causes": causes,
            "lines": [{"n": i + 1, "text": lines[i], "hit": i in hit_set} for i in kept_sorted],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    tc = ", ".join(detected) if detected else "unknown"
    print("== Build log triage ==")
    print(f"toolchain: {tc}   |   {len(hits)} critical line(s) of {total} total"
          + (f"   ({truncated} lower-signal hits dropped — raise --max-lines)" if truncated else ""))
    if causes:
        print("\nlikely cause(s):")
        for c in causes:
            print(f"  → {c}")
    if not hits:
        print("\n(no known error signatures matched — the failure may be non-fatal or a new pattern;")
        print(" skim the raw tail, or add a pattern to triage-log.py.)")
        return 0
    print("\nrelevant lines:")
    prev = None
    for i in kept_sorted:
        if prev is not None and i != prev + 1:
            print("  …")
        marker = ">>" if i in hit_set else "  "
        print(f"  {marker} {i + 1:>5}  {lines[i]}")
        prev = i
    return 0


if __name__ == "__main__":
    sys.exit(main())
