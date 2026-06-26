#!/usr/bin/env python3
"""dart-doctor — diagnose a Dart/Flutter mobile-game project against the
dart-mobile-game-studio skill's standards and print a categorized PASS/WARN/FAIL
report with remediation and an exit code. The project-quality analog of
`flutter doctor` (which only checks the toolchain).

Dependency-free: Python 3 standard library only.

It scans SOURCE and CONFIG only — Dart source (**/*.dart, excluding build/.dart_tool
and leading-dot dirs), pubspec.yaml, analysis_options.yaml, AndroidManifest.xml,
Info.plist — and NEVER opens Markdown/docs as a check input, so a doc that says
"no analytics" is never flagged. Findings map to references/common-pitfalls.md codes.

Usage:
    dart-doctor.py [PATH] [--json] [--build] [--strict] [--only DIM[,DIM...]]
                   [--quiet] [--no-color] [-h|--help]

    DIM ∈ environment, architecture, dart-quality, performance, kids-safety,
          accessibility, assets-licensing, build-tests

Exit codes: 0 = healthy (no FAIL; with --strict, no WARN either);
            1 = at least one FAIL (or, with --strict, a WARN);
            2 = usage error / fatal internal error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

TOOL_NAME = "dart-doctor"
TOOL_VERSION = "1.0"

EXCLUDED_DIR_NAMES = {"build", ".dart_tool", ".git", ".idea", ".vscode", "ios", "macos", "windows", "linux"}
# note: android/ is partially scanned (manifest) but its Gradle/Java is out of scope here.

DIMENSIONS = [
    "environment",
    "architecture",
    "dart-quality",
    "performance",
    "kids-safety",
    "accessibility",
    "assets-licensing",
    "build-tests",
]

GLYPHS_UNICODE = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "INFO": "•", "SKIP": "∅"}
GLYPHS_ASCII = {"PASS": "[OK]", "WARN": "[WARN]", "FAIL": "[FAIL]", "INFO": "[INFO]", "SKIP": "[SKIP]"}
COLORS = {"PASS": "\033[32m", "WARN": "\033[33m", "FAIL": "\033[31m", "INFO": "\033[36m", "SKIP": "\033[90m", "_": "\033[0m"}


# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #
def _excluded(rel: str) -> bool:
    parts = rel.split(os.sep)
    return any(p in EXCLUDED_DIR_NAMES or (p.startswith(".") and p not in (".",)) for p in parts)


def walk(root: str, suffix: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith(suffix):
                yield os.path.join(dirpath, fn)


def strip_comments(text: str) -> str:
    """Cheap: drop // line comments and /* */ blocks so commented-out code/notes don't trip checks.
    Not language-perfect (won't honor // inside strings) but good enough for heuristics."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    out = []
    for line in text.splitlines():
        # keep the part before a // that isn't inside an obvious http(s):// token
        m = re.search(r"//", line)
        if m:
            before = line[: m.start()]
            if not re.search(r"https?:$", before):
                line = before
        out.append(line)
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #
class Finding:
    __slots__ = ("status", "title", "detail", "fix", "code", "locs")

    def __init__(self, status, title, detail="", fix="", code="", locs=None):
        self.status = status
        self.title = title
        self.detail = detail
        self.fix = fix
        self.code = code
        self.locs = locs or []

    def as_dict(self):
        return {"status": self.status, "title": self.title, "detail": self.detail,
                "fix": self.fix, "code": self.code, "locations": self.locs[:20]}


class Context:
    """Loads and caches the files once; all checks read from here."""
    def __init__(self, root: str):
        self.root = root
        self.dart_files = sorted(walk(root, ".dart"))
        self.core_files = [f for f in self.dart_files
                           if re.search(r"(^|/)(lib/)?(models|systems)/", os.path.relpath(f, root).replace(os.sep, "/"))]
        self.test_files = [f for f in self.dart_files if "/test/" in f.replace(os.sep, "/") or f.endswith("_test.dart")]
        self.src_files = [f for f in self.dart_files if f not in self.test_files]
        self._text = {}
        self.pubspec = os.path.join(root, "pubspec.yaml")
        self.pubspec_text = self._read(self.pubspec) if os.path.isfile(self.pubspec) else ""
        self.analysis = os.path.join(root, "analysis_options.yaml")
        self.analysis_text = self._read(self.analysis) if os.path.isfile(self.analysis) else ""
        self.manifests = sorted(walk(os.path.join(root, "android"), "AndroidManifest.xml")) if os.path.isdir(os.path.join(root, "android")) else []

    def _read(self, path):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""

    def text(self, path, stripped=True):
        key = (path, stripped)
        if key not in self._text:
            raw = self._read(path)
            self._text[key] = strip_comments(raw) if stripped else raw
        return self._text[key]

    def rel(self, path):
        return os.path.relpath(path, self.root).replace(os.sep, "/")


def grep(ctx, files, pattern, flags=re.MULTILINE):
    rx = re.compile(pattern, flags)
    hits = []
    for f in files:
        for m in rx.finditer(ctx.text(f)):
            line = ctx.text(f)[: m.start()].count("\n") + 1
            hits.append(f"{ctx.rel(f)}:{line}")
    return hits


# --------------------------------------------------------------------------- #
# Dimension checks — each returns a list[Finding]
# --------------------------------------------------------------------------- #
def check_environment(ctx):
    out = []
    dart = shutil.which("dart")
    flutter = shutil.which("flutter")
    out.append(Finding("PASS" if dart else "WARN", "Dart SDK on PATH",
                       dart or "not found", "Install: https://dart.dev/get-dart"))
    out.append(Finding("PASS" if flutter else "INFO", "Flutter SDK on PATH",
                       flutter or "not found (fine for a pure-Dart package)",
                       "Install: https://docs.flutter.dev/get-started/install"))
    if not os.path.isfile(ctx.pubspec):
        out.append(Finding("FAIL", "pubspec.yaml present", "no pubspec.yaml under the project root",
                           "Scaffold with: flutter create <app>  (or dart create <pkg>)"))
    else:
        out.append(Finding("PASS", "pubspec.yaml present", ctx.rel(ctx.pubspec)))
    if not ctx.analysis_text:
        out.append(Finding("WARN", "analysis_options.yaml present", "no analyzer config found",
                           "Copy assets/analysis_options.yaml (strict lints + promoted errors)."))
    else:
        strong = ("very_good_analysis" in ctx.analysis_text or "flutter_lints" in ctx.analysis_text)
        out.append(Finding("PASS" if strong else "WARN", "Strong lint set",
                           "found" if strong else "no recognized lint include",
                           "include: package:very_good_analysis/analysis_options.yaml (or flutter_lints)."))
    return out


def check_architecture(ctx):
    out = []
    # pure-core must not import flutter/flame
    leak = grep(ctx, ctx.core_files, r"^\s*import\s+['\"]package:(flutter|flame)\b")
    out.append(Finding("FAIL" if leak else "PASS", "Pure-Dart core (no Flutter/Flame import)",
                       f"{len(leak)} import(s) of flutter/flame under models/ or systems/" if leak else
                       "no renderer imports in the core",
                       "Move rendering out of lib/models|systems; carry geometry on a value type (Vec2).",
                       code="ARCHITECTURE_LAYERING", locs=leak))
    # dart:ui geometry leaking into core
    uileak = grep(ctx, ctx.core_files, r"\b(Offset|Size|Rect|Color|Canvas|Vector2)\b")
    if uileak:
        out.append(Finding("WARN", "No dart:ui/Flame types in the core",
                           f"{len(uileak)} use(s) of Offset/Rect/Color/Vector2 in the core",
                           "Use a plain value Vec2/record in the model; convert at the renderer edge.",
                           code="ARCHITECTURE_LAYERING", locs=uileak))
    # a state machine (enum *phase* or sealed) somewhere in the core
    has_sm = grep(ctx, ctx.src_files, r"\benum\s+\w*(Phase|State|GameState)\b|\bsealed class\b")
    out.append(Finding("PASS" if has_sm else "WARN", "Explicit state machine",
                       "found enum/sealed state type" if has_sm else "no obvious phase enum / sealed state",
                       "Model menu→playing→paused→won/lost as an enum or sealed type (pure Dart)."))
    # folder layout
    libdir = os.path.join(ctx.root, "lib")
    if os.path.isdir(libdir):
        present = [d for d in ("models", "systems", "widgets", "game") if os.path.isdir(os.path.join(libdir, d))]
        out.append(Finding("PASS" if {"models", "systems"} & set(present) else "WARN",
                           "Layered folder layout",
                           "lib/" + ", lib/".join(present) if present else "no models//systems/ split",
                           "Use lib/models lib/systems lib/game lib/widgets; keep files small."))
    return out


def check_dart_quality(ctx):
    out = []
    # ! / as on external data — scan json/prefs/bundle lines for force-unwrap nearby
    bang = grep(ctx, ctx.src_files, r"\w+\s*\[\s*['\"][^'\"]+['\"]\s*\]\s*!")
    bang += grep(ctx, ctx.src_files, r"jsonDecode\([^)]*\)\s*\[[^\]]+\]\s*!")
    out.append(Finding("WARN" if bang else "PASS", "No force-unwrap (!) on external data",
                       f"{len(bang)} map-index '!' (likely on parsed/loaded data)" if bang else "none found",
                       "Use (x as T?) ?? fallback, or `if (json case {'k': final T v})`.",
                       code="DART_NULL_SAFETY", locs=bang))
    # dynamic typing
    dyn = grep(ctx, ctx.src_files, r"\bMap<String,\s*dynamic>|\bdynamic\b\s+\w+\s*=")
    if dyn:
        out.append(Finding("WARN", "Avoid dynamic / loose typing",
                           f"{len(dyn)} use(s) of dynamic / Map<String, dynamic>",
                           "Prefer Map<String, Object?> and typed models at the boundary.",
                           code="DART_DYNAMIC_TYPING", locs=dyn))
    # print in the play path
    prints = grep(ctx, ctx.src_files, r"(^|\s)print\(")
    out.append(Finding("WARN" if prints else "PASS", "No print() in shipped code",
                       f"{len(prints)} print() call(s)" if prints else "none",
                       "Use logging/dart:developer log, or guard behind kDebugMode (avoid_print lint).",
                       code="FLUTTER_MEMORY_LEAK" if False else "", locs=prints))
    # dispose discipline — controllers created vs dispose presence per file
    created = grep(ctx, ctx.src_files,
                   r"\b(AnimationController|StreamSubscription|TextEditingController|FocusNode|ScrollController|Timer)\b")
    has_dispose = grep(ctx, ctx.src_files, r"\bvoid\s+dispose\s*\(|\.dispose\(\)|\.cancel\(\)")
    if created and not has_dispose:
        out.append(Finding("WARN", "Dispose controllers/subscriptions",
                           f"{len(created)} disposable(s) created; no dispose()/cancel() seen",
                           "Tear down every controller/subscription/timer in State.dispose / onRemove.",
                           code="FLUTTER_MEMORY_LEAK", locs=created[:20]))
    else:
        out.append(Finding("PASS", "Dispose discipline", "disposables paired with teardown (heuristic)"))
    # bare Random()/DateTime.now() in core
    rng = grep(ctx, ctx.core_files, r"\bRandom\(\s*\)|\bDateTime\.now\(\)")
    if rng:
        out.append(Finding("WARN", "Seeded RNG / injected clock in core",
                           f"{len(rng)} bare Random()/DateTime.now() in the core",
                           "Inject a seeded Random (assets/seeded_random.dart) and a clock seam.",
                           code="", locs=rng))
    return out


def check_performance(ctx):
    out = []
    # allocation inside update()/render() — find those method bodies and scan for `new`-y constructors
    alloc_hits = []
    rx_method = re.compile(r"\b(?:void\s+)?(update|render)\s*\([^)]*\)\s*(?:async\s*)?\{", re.MULTILINE)
    rx_alloc = re.compile(r"\b(Vector2|Paint|Rect|Path|TextPaint|SpriteAnimation)\s*\(")
    for f in ctx.src_files:
        t = ctx.text(f)
        for m in rx_method.finditer(t):
            body = _balanced_body(t, m.end() - 1)
            for a in rx_alloc.finditer(body):
                line = t[: m.start()].count("\n") + 1
                alloc_hits.append(f"{ctx.rel(f)}:~{line} ({a.group(1)} in {m.group(1)}())")
    out.append(Finding("WARN" if alloc_hits else "PASS", "No allocation in update()/render()",
                       f"{len(alloc_hits)} allocation(s) in a hot method" if alloc_hits else "none found",
                       "Hoist Paint/Vector2/Rect to fields; mutate with setFrom/setValues/addScaled.",
                       code="FLAME_HOT_PATH_ALLOCATION", locs=alloc_hits))
    # dt used but not clamped
    update_files = [f for f in ctx.src_files if re.search(r"\bvoid\s+update\s*\(\s*double\s+dt", ctx.text(f))]
    unclamped = [ctx.rel(f) for f in update_files
                 if not re.search(r"dt\.clamp\(|min\(\s*dt|clamp\([^)]*dt", ctx.text(f))]
    if update_files:
        out.append(Finding("WARN" if unclamped else "PASS", "Clamp dt in update()",
                           f"{len(unclamped)} update(dt) without a visible clamp" if unclamped else "dt clamped",
                           "Flame does NOT clamp dt — `final d = math.min(dt, 1/30);` before stepping.",
                           code="FLAME_DT_IGNORED", locs=unclamped))
    # setState in build
    ss = grep(ctx, ctx.src_files, r"Widget\s+build\s*\([^)]*\)\s*(?:async\s*)?\{[^}]*setState\(")
    if ss:
        out.append(Finding("WARN", "No setState() inside build()", f"{len(ss)} occurrence(s)",
                           "Derive UI from state; defer with addPostFrameCallback.",
                           code="FLUTTER_LIFECYCLE_SETSTATE", locs=ss))
    return out


def _balanced_body(text, brace_idx):
    """Return the substring of a {...} block starting at brace_idx (index of '{')."""
    depth, i, n = 0, brace_idx, len(text)
    while i < n:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_idx: i + 1]
        i += 1
    return text[brace_idx: brace_idx + 2000]


def check_kids_safety(ctx):
    out = []
    # package families flagged by name — caught both as a dart `import 'package:X'` and a pubspec dep `X:`
    PKG = {
        "ads": ["google_mobile_ads", "firebase_admob", "unity_ads", "applovin_max", "appodeal", "ironsource"],
        "analytics/tracking": ["firebase_analytics", "amplitude_flutter", "mixpanel_flutter", "sentry_flutter",
                               "firebase_crashlytics", "facebook_app_events", "segment", "posthog_flutter"],
    }
    SYMS = {
        "advertising id": r"\b(AdvertisingId|AdId|IDFA|GAID)\b|com\.google\.android\.gms\.permission\.AD_ID",
        "external links": r"\blaunchUrl(String)?\s*\(|package:url_launcher",
        "raw http": r"http://[a-zA-Z0-9]",
    }
    any_hit = False
    for label, names in PKG.items():
        hits = []
        for n in names:
            hits += grep(ctx, ctx.src_files, r"package:%s\b" % re.escape(n))      # imported
            if ctx.pubspec_text and re.search(r"(?m)^\s*%s\s*:" % re.escape(n), ctx.pubspec_text):
                hits.append(ctx.rel(ctx.pubspec) + " (dependency)")               # declared
        if hits:
            any_hit = True
            out.append(Finding("WARN", f"Kids build: no {label}",
                               f"{len(hits)} reference(s) to {label} ({', '.join(names[:3])}…)",
                               "Forbidden in a kids/Families build. Remove, or confirm a 13+ audience and gate per monetization-policy.md.",
                               code="", locs=hits[:20]))
    for label, rx in SYMS.items():
        hits = grep(ctx, ctx.src_files + ([ctx.pubspec] if ctx.pubspec_text else []), rx)
        if label == "advertising id":
            hits += grep(ctx, ctx.manifests, r"com\.google\.android\.gms\.permission\.AD_ID")
        if hits:
            any_hit = True
            out.append(Finding("WARN", f"Kids build: no {label}",
                               f"{len(hits)} reference(s) to {label}",
                               "Forbidden in a kids/Families build. Remove, or confirm a 13+ audience and gate per monetization-policy.md.",
                               code="", locs=hits[:20]))
    if not any_hit:
        out.append(Finding("PASS", "No ads/analytics/tracking/AdvertisingId/external-links/raw-http",
                           "none detected (kids-safe defaults)"))
    # INTERNET permission when likely offline
    inet = grep(ctx, ctx.manifests, r'android\.permission\.INTERNET')
    if inet:
        out.append(Finding("INFO", "Android INTERNET permission declared",
                           "present — remove it if the game is truly offline (kids-safety prefers no network)",
                           "Drop the <uses-permission android:name=\"android.permission.INTERNET\"/> if offline."))
    return out


def check_accessibility(ctx):
    out = []
    gestures = grep(ctx, ctx.src_files, r"\bGestureDetector\b|\bonTap\s*:")
    semantics = grep(ctx, ctx.src_files, r"\bSemantics\b|semanticLabel\s*:|\bExcludeSemantics\b|\bMergeSemantics\b")
    if gestures and not semantics:
        out.append(Finding("WARN", "Semantics on interactive controls",
                           f"{len(gestures)} gesture/tap site(s); no Semantics found",
                           "Wrap painted/gesture-only controls in Semantics(label:/button:); honor textScaler & reduce-motion.",
                           code="", locs=gestures[:20]))
    else:
        out.append(Finding("PASS" if semantics else "INFO", "Semantics present",
                           f"{len(semantics)} Semantics usage(s)" if semantics else "no interactive controls detected"))
    rm = grep(ctx, ctx.src_files, r"disableAnimations|MediaQuery\.of\([^)]*\)\.disableAnimations")
    out.append(Finding("PASS" if rm else "INFO", "Reduce Motion honored",
                       f"{len(rm)} disableAnimations check(s)" if rm else "no reduce-motion gate seen (add before .repeat()/long motion)"))
    return out


def check_assets_licensing(ctx):
    out = []
    # large raster assets
    big = []
    adir = os.path.join(ctx.root, "assets")
    if os.path.isdir(adir):
        for dp, dn, fns in os.walk(adir):
            dn[:] = [d for d in dn if not d.startswith(".")]
            for fn in fns:
                if fn.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                    p = os.path.join(dp, fn)
                    try:
                        if os.path.getsize(p) > 500 * 1024:
                            big.append(f"{ctx.rel(p)} ({os.path.getsize(p)//1024} KB)")
                    except OSError:
                        pass
    out.append(Finding("WARN" if big else "PASS", "No oversized raster assets",
                       f"{len(big)} image(s) > 500 KB" if big else "none > 500 KB",
                       "Right-size art; prefer vector/CustomPainter placeholders (texture budget).",
                       code="FLAME_SPRITE_BATCHING", locs=big[:20]))
    # levels as data?
    levels = os.path.isdir(os.path.join(ctx.root, "assets", "levels"))
    out.append(Finding("PASS" if levels else "INFO", "Levels as data (JSON)",
                       "assets/levels/ present" if levels else "no assets/levels/ (fine if no levels yet)",
                       "Keep level data as validated JSON, not Dart code."))
    out.append(Finding("INFO", "Asset licensing (manual)",
                       "dart-doctor can't verify licenses — confirm every shipped image/audio/font is placeholder or user-owned.",
                       "No copyrighted characters/logos/fonts/music. Keep a license manifest."))
    return out


def check_build_tests(ctx, run_build):
    out = []
    has_tests = bool(ctx.test_files)
    out.append(Finding("PASS" if has_tests else "WARN", "Tests present",
                       f"{len(ctx.test_files)} test file(s)" if has_tests else "no *_test.dart found",
                       "Add dart test for the pure core (transitions, scoring, win/lose, seeded RNG)."))
    if not run_build:
        out.append(Finding("INFO", "Analyzer/tests not run",
                           "pass --build to run `dart analyze` + `dart test` here",
                           "dart analyze --fatal-infos --fatal-warnings ; dart test"))
        return out
    dart = shutil.which("flutter") or shutil.which("dart")
    if not dart:
        out.append(Finding("SKIP", "Analyzer/tests", "no dart/flutter toolchain on PATH",
                           "Install the SDK, then: dart analyze && dart test"))
        return out
    for label, cmd in (("dart analyze", [os.path.basename(dart), "analyze"]),
                       ("dart test", [os.path.basename(dart), "test"])):
        try:
            r = subprocess.run([dart] + cmd[1:], cwd=ctx.root, capture_output=True, text=True, timeout=300)
            ok = r.returncode == 0
            tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
            out.append(Finding("PASS" if ok else "FAIL", label, tail[0][:200],
                               "" if ok else "Fix the reported issues; pipe long logs through triage-log.py."))
        except (subprocess.TimeoutExpired, OSError) as e:
            out.append(Finding("WARN", label, f"could not run: {e}", ""))
    return out


CHECKS = {
    "environment": lambda ctx, rb: check_environment(ctx),
    "architecture": lambda ctx, rb: check_architecture(ctx),
    "dart-quality": lambda ctx, rb: check_dart_quality(ctx),
    "performance": lambda ctx, rb: check_performance(ctx),
    "kids-safety": lambda ctx, rb: check_kids_safety(ctx),
    "accessibility": lambda ctx, rb: check_accessibility(ctx),
    "assets-licensing": lambda ctx, rb: check_assets_licensing(ctx),
    "build-tests": lambda ctx, rb: check_build_tests(ctx, rb),
}


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(prog=TOOL_NAME, add_help=True,
                                 description="Project-quality health check for a Dart/Flutter game.")
    ap.add_argument("path", nargs="?", default=".", help="project root (default: .)")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    ap.add_argument("--build", action="store_true", help="actually run dart analyze + dart test")
    ap.add_argument("--strict", action="store_true", help="treat WARN as failure for the exit code")
    ap.add_argument("--only", default="", help="comma list of dimensions to run")
    ap.add_argument("--quiet", action="store_true", help="only print WARN/FAIL")
    ap.add_argument("--no-color", action="store_true", help="disable ANSI color")
    args = ap.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"{TOOL_NAME}: not a directory: {root}", file=sys.stderr)
        return 2

    only = [d.strip() for d in args.only.split(",") if d.strip()] if args.only else DIMENSIONS
    for d in only:
        if d not in DIMENSIONS:
            print(f"{TOOL_NAME}: unknown dimension '{d}' (valid: {', '.join(DIMENSIONS)})", file=sys.stderr)
            return 2

    ctx = Context(root)
    results = {}
    for dim in only:
        try:
            results[dim] = CHECKS[dim](ctx, args.build)
        except Exception as e:  # a check bug shouldn't abort the whole report
            results[dim] = [Finding("WARN", f"{dim} check error", str(e))]

    n_fail = sum(1 for fs in results.values() for f in fs if f.status == "FAIL")
    n_warn = sum(1 for fs in results.values() for f in fs if f.status == "WARN")
    n_pass = sum(1 for fs in results.values() for f in fs if f.status == "PASS")

    if args.json:
        print(json.dumps({
            "tool": TOOL_NAME, "version": TOOL_VERSION, "root": root,
            "summary": {"pass": n_pass, "warn": n_warn, "fail": n_fail},
            "dimensions": {d: [f.as_dict() for f in fs] for d, fs in results.items()},
        }, indent=2, ensure_ascii=False))
    else:
        use_color = sys.stdout.isatty() and not args.no_color
        glyphs = GLYPHS_UNICODE if (sys.stdout.encoding or "").lower().startswith("utf") else GLYPHS_ASCII
        print(f"{TOOL_NAME} {TOOL_VERSION} — {root}\n")
        for dim in only:
            fs = results[dim]
            if args.quiet:
                fs = [f for f in fs if f.status in ("WARN", "FAIL")]
                if not fs:
                    continue
            print(f"── {dim} ──")
            for f in fs:
                g = glyphs[f.status]
                if use_color:
                    g = f"{COLORS.get(f.status,'')}{g}{COLORS['_']}"
                code = f"  [{f.code}]" if f.code else ""
                print(f"  {g} {f.title}{code}")
                if f.detail:
                    print(f"      {f.detail}")
                if f.status in ("WARN", "FAIL") and f.fix:
                    print(f"      ↳ fix: {f.fix}")
                for loc in f.locs[:8]:
                    print(f"        · {loc}")
                if len(f.locs) > 8:
                    print(f"        · … and {len(f.locs) - 8} more")
            print()
        verdict = "FAIL" if n_fail else ("WARN" if n_warn else "PASS")
        bar = f"{n_pass} pass · {n_warn} warn · {n_fail} fail"
        if use_color:
            print(f"{COLORS[verdict]}== {verdict} =={COLORS['_']}  {bar}")
        else:
            print(f"== {verdict} ==  {bar}")
        if not args.build:
            print("(static scan; pass --build to run dart analyze + dart test)")

    if n_fail or (args.strict and n_warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
