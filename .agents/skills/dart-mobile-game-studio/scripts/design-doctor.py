#!/usr/bin/env python3
"""design-doctor - static UX/a11y/game-design scan for Flutter/Flame games.

Dependency-free: Python 3 standard library only. This tool reads Dart source,
pubspec.yaml, and tests. It does not run Flutter, render frames, or claim visual
approval. Treat findings as a fast design gate before manual device review.

Usage:
    design-doctor.py [PATH] [--json] [--strict] [--only DIM[,DIM...]]
                     [--quiet] [--no-color] [-h|--help]

    DIM in screen-map, interaction-a11y, motion, responsive-layout,
           visual-states, flame-ui, kids-ux, test-hooks

Exit codes: 0 = no FAIL; 1 = at least one FAIL (or WARN with --strict);
            2 = usage error / fatal internal error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

TOOL_NAME = "design-doctor"
TOOL_VERSION = "0.1"

EXCLUDED_DIR_NAMES = {
    ".dart_tool",
    ".git",
    ".idea",
    ".vscode",
    "build",
    "ios",
    "linux",
    "macos",
    "windows",
}

DIMENSIONS = [
    "screen-map",
    "interaction-a11y",
    "motion",
    "responsive-layout",
    "visual-states",
    "flame-ui",
    "kids-ux",
    "test-hooks",
]

GLYPHS = {"PASS": "[OK]", "WARN": "[WARN]", "FAIL": "[FAIL]", "INFO": "[INFO]", "SKIP": "[SKIP]"}
COLORS = {
    "PASS": "\033[32m",
    "WARN": "\033[33m",
    "FAIL": "\033[31m",
    "INFO": "\033[36m",
    "SKIP": "\033[90m",
    "_": "\033[0m",
}


def strip_comments(text: str) -> str:
    """Drop Dart comments so prose does not satisfy code-oriented checks."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    out = []
    for line in text.splitlines():
        m = re.search(r"//", line)
        if m:
            before = line[: m.start()]
            if not re.search(r"https?:$", before):
                line = before
        out.append(line)
    return "\n".join(out)


def walk(root: str, suffix: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith(suffix):
                yield os.path.join(dirpath, fn)


def discover_project_roots(root: str) -> list[str]:
    root = os.path.abspath(root)
    root_pubspec = os.path.join(root, "pubspec.yaml")
    if os.path.isfile(root_pubspec):
        return [root]

    found = []
    for p in walk(root, "pubspec.yaml"):
        found.append(os.path.dirname(p))
    return sorted(set(found))


def balanced_call(text: str, start: int) -> str:
    """Return a best-effort substring for a WidgetName(...) call."""
    open_idx = text.find("(", start)
    if open_idx < 0:
        return text[start : start + 500]
    depth = 0
    for i in range(open_idx, min(len(text), open_idx + 5000)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start : open_idx + 2000]


class Finding:
    __slots__ = ("status", "title", "detail", "fix", "locs")

    def __init__(self, status: str, title: str, detail: str = "", fix: str = "", locs=None):
        self.status = status
        self.title = title
        self.detail = detail
        self.fix = fix
        self.locs = locs or []

    def as_dict(self):
        return {
            "status": self.status,
            "title": self.title,
            "detail": self.detail,
            "fix": self.fix,
            "locations": self.locs[:20],
        }


class Context:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.pubspec = os.path.join(self.root, "pubspec.yaml")
        self.pubspec_text = self._read(self.pubspec) if os.path.isfile(self.pubspec) else ""
        self.dart_files = sorted(walk(self.root, ".dart"))
        self.test_files = [
            f for f in self.dart_files if "/test/" in f.replace(os.sep, "/") or f.endswith("_test.dart")
        ]
        self.src_files = [f for f in self.dart_files if f not in self.test_files]
        self.ui_files = [
            f
            for f in self.src_files
            if re.search(r"(^|/)(lib/)?(widgets|game|screens|pages|ui|style)/", self.rel(f))
            or self.rel(f).endswith("main.dart")
        ]
        self._text = {}
        self.is_flutter = bool(re.search(r"(?m)^\s*flutter\s*:", self.pubspec_text))
        self.uses_flame = "package:flame/" in self.all_src_text or bool(
            re.search(r"(?m)^\s*flame\s*:", self.pubspec_text)
        )

    def _read(self, path: str) -> str:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""

    def text(self, path: str, stripped: bool = True) -> str:
        key = (path, stripped)
        if key not in self._text:
            raw = self._read(path)
            self._text[key] = strip_comments(raw) if stripped else raw
        return self._text[key]

    @property
    def all_src_text(self) -> str:
        return "\n".join(self.text(f) for f in self.src_files)

    @property
    def all_test_text(self) -> str:
        return "\n".join(self.text(f) for f in self.test_files)

    def rel(self, path: str) -> str:
        return os.path.relpath(path, self.root).replace(os.sep, "/")


def grep(ctx: Context, files: list[str], pattern: str, flags=re.MULTILINE) -> list[str]:
    rx = re.compile(pattern, flags)
    hits = []
    for f in files:
        text = ctx.text(f)
        for m in rx.finditer(text):
            line = text[: m.start()].count("\n") + 1
            hits.append(f"{ctx.rel(f)}:{line}")
    return hits


def check_screen_map(ctx: Context) -> list[Finding]:
    out = []
    files = ctx.src_files
    states = grep(ctx, files, r"\benum\s+\w*(Phase|State|Status)\b|\bsealed\s+class\s+\w*(Phase|State|Status)\b")
    if states:
        out.append(Finding("PASS", "Explicit screen/game state type", "enum/sealed state found", locs=states[:8]))
    else:
        out.append(
            Finding(
                "WARN",
                "Explicit screen/game state type",
                "no obvious enum/sealed state for menu -> playing -> paused -> result",
                "Model route/overlay state as GamePhase/GameStatus instead of scattered booleans.",
            )
        )

    text = ctx.all_src_text
    has_menu = bool(re.search(r"\b(menu|Menu|home|Home)\b", text))
    has_play = bool(re.search(r"\b(playing|Playing|play|Play|GamePage|GameScreen)\b", text))
    has_result = bool(re.search(r"\b(won|Won|win|Win|lost|Lost|gameOver|GameOver|Game Over)\b", text))
    if has_menu and has_play and has_result:
        out.append(Finding("PASS", "Core screen loop is visible", "menu/play/result terms found"))
    else:
        missing = [name for name, ok in (("menu", has_menu), ("play", has_play), ("result", has_result)) if not ok]
        out.append(
            Finding(
                "WARN",
                "Core screen loop is visible",
                "missing: " + ", ".join(missing),
                "Design the main loop explicitly: menu -> playing -> paused -> win/lose -> menu.",
            )
        )

    route_hits = grep(ctx, files, r"\b(Navigator|MaterialPageRoute|PageRouteBuilder|GoRouter|RouterConfig)\b")
    overlay_hits = grep(ctx, files, r"\b(Stack|OverlayEntry|showDialog|overlayBuilderMap|overlays\.)\b")
    if route_hits or overlay_hits:
        out.append(
            Finding(
                "PASS",
                "Routes/overlays are explicit",
                f"{len(route_hits)} route hit(s), {len(overlay_hits)} overlay hit(s)",
                locs=(route_hits + overlay_hits)[:10],
            )
        )
    else:
        out.append(
            Finding(
                "INFO",
                "Routes/overlays are explicit",
                "no route or overlay API found; fine for a one-screen prototype",
                "Use routes for screens and overlays for pause/result over gameplay.",
            )
        )

    if ctx.uses_flame or grep(ctx, files, r"\bupdate\s*\(\s*double\s+dt\b"):
        pause_hits = grep(ctx, files, r"\b(paused|pause|Pause|pauseEngine|resumeEngine)\b")
        if pause_hits:
            out.append(Finding("PASS", "Pause path for continuous play", "pause terms found", locs=pause_hits[:8]))
        else:
            out.append(
                Finding(
                    "WARN",
                    "Pause path for continuous play",
                    "no pause path found in a Flame/update(dt) project",
                    "Add a paused phase and pause the loop or ignore update while paused.",
                )
            )
    return out


def icon_buttons_without_tooltip(ctx: Context) -> list[str]:
    hits = []
    for f in ctx.ui_files:
        text = ctx.text(f)
        for m in re.finditer(r"\bIconButton\s*\(", text):
            block = balanced_call(text, m.start())
            if "tooltip:" not in block and "Semantics(" not in block:
                line = text[: m.start()].count("\n") + 1
                hits.append(f"{ctx.rel(f)}:{line}")
    return hits


def gamewidget_taps_without_semantics(ctx: Context) -> list[str]:
    hits = []
    for f in ctx.ui_files:
        text = ctx.text(f)
        for m in re.finditer(r"\bGestureDetector\s*\(", text):
            block = balanced_call(text, m.start())
            if "GameWidget" in block and "Semantics(" not in block:
                line = text[: m.start()].count("\n") + 1
                hits.append(f"{ctx.rel(f)}:{line}")
    return hits


def check_interaction_a11y(ctx: Context) -> list[Finding]:
    out = []
    custom_hits = grep(ctx, ctx.ui_files, r"\b(GestureDetector|InkWell|InkResponse|RawGestureDetector|Listener)\b")
    semantics_hits = grep(ctx, ctx.ui_files, r"\b(Semantics|MergeSemantics|ExcludeSemantics)\b|semanticLabel\s*:|tooltip\s*:")
    if custom_hits and not semantics_hits:
        out.append(
            Finding(
                "WARN",
                "Custom interactions have accessible names",
                f"{len(custom_hits)} custom interaction(s); no Semantics/tooltip found",
                "Wrap custom tap/paint/canvas controls in Semantics(label:, button:, value:).",
                custom_hits[:12],
            )
        )
    elif custom_hits:
        out.append(
            Finding(
                "PASS",
                "Custom interactions have accessible names",
                f"{len(custom_hits)} custom interaction(s), {len(semantics_hits)} semantics/tooltip hit(s)",
                locs=semantics_hits[:8],
            )
        )
    else:
        out.append(Finding("INFO", "Custom interactions have accessible names", "no custom interaction widgets found"))

    icon_hits = icon_buttons_without_tooltip(ctx)
    if icon_hits:
        out.append(
            Finding(
                "WARN",
                "Icon-only controls are named",
                f"{len(icon_hits)} IconButton(s) without tooltip/Semantics",
                "Add tooltip: or an explicit Semantics label.",
                icon_hits[:10],
            )
        )
    else:
        out.append(Finding("PASS", "Icon-only controls are named", "no unnamed IconButton found"))

    if re.search(r"\bliveRegion\s*:\s*true|SemanticsService\.announce", ctx.all_src_text):
        out.append(Finding("PASS", "Important state changes can be announced", "liveRegion/SemanticsService found"))
    elif re.search(r"\b(won|gameOver|GameOver|Game Over|lost)\b", ctx.all_src_text):
        out.append(
            Finding(
                "INFO",
                "Important state changes can be announced",
                "result state found, but no liveRegion/SemanticsService announcement",
                "Announce win/lose/level-up once; do not make per-frame score a live region.",
            )
        )
    return out


def check_motion(ctx: Context) -> list[Finding]:
    out = []
    motion_hits = grep(
        ctx,
        ctx.ui_files,
        r"\b(Animated\w+|AnimationController|TweenAnimationBuilder|Hero|PageRouteBuilder|Timer|Future\.delayed)\b",
    )
    reduce_hits = grep(ctx, ctx.ui_files, r"\bdisableAnimations\b|\baccessibleNavigation\b|reduceMotion")
    if motion_hits and reduce_hits:
        out.append(Finding("PASS", "Non-essential motion respects Reduce Motion", f"{len(reduce_hits)} gate(s)", locs=reduce_hits[:8]))
    elif motion_hits:
        out.append(
            Finding(
                "WARN",
                "Non-essential motion respects Reduce Motion",
                f"{len(motion_hits)} motion/delay site(s); no disableAnimations gate found",
                "Read MediaQuery.disableAnimations or platform accessibilityFeatures before animations/delays.",
                motion_hits[:12],
            )
        )
    else:
        out.append(Finding("INFO", "Non-essential motion respects Reduce Motion", "no Flutter UI motion sites found"))

    repeat_hits = grep(ctx, ctx.ui_files, r"\.repeat\s*\(")
    if repeat_hits and not reduce_hits:
        out.append(
            Finding(
                "WARN",
                "Looping animations are gated",
                f"{len(repeat_hits)} repeat() call(s) without a visible Reduce Motion gate",
                "Only start looping/reversing animation controllers when animations are allowed.",
                repeat_hits,
            )
        )
    elif repeat_hits:
        out.append(Finding("PASS", "Looping animations are gated", "repeat() and reduce-motion gate both found"))
    return out


def check_responsive_layout(ctx: Context) -> list[Finding]:
    out = []
    safe_hits = grep(ctx, ctx.ui_files, r"\bSafeArea\s*\(")
    if safe_hits:
        out.append(Finding("PASS", "SafeArea protects gameplay UI", f"{len(safe_hits)} SafeArea usage(s)", locs=safe_hits[:8]))
    else:
        out.append(
            Finding(
                "WARN",
                "SafeArea protects gameplay UI",
                "no SafeArea found in UI files",
                "Wrap play screens/HUDs so notches, status bars, and home indicators do not cover controls.",
            )
        )

    responsive_hits = grep(
        ctx,
        ctx.ui_files,
        r"\b(LayoutBuilder|OrientationBuilder|AspectRatio|MediaQuery\.(sizeOf|orientationOf|paddingOf|textScalerOf)|Expanded|Flexible|GridView\.builder|ListView\.builder|SliverGridDelegate)\b",
    )
    if responsive_hits:
        out.append(Finding("PASS", "Layout adapts to screen constraints", f"{len(responsive_hits)} responsive layout signal(s)", locs=responsive_hits[:10]))
    else:
        out.append(
            Finding(
                "WARN",
                "Layout adapts to screen constraints",
                "no responsive layout signals found",
                "Use constraints/MediaQuery/OrientationBuilder and verify phone, tablet, portrait, landscape.",
            )
        )

    text_painter_hits = grep(ctx, ctx.ui_files, r"\bTextPainter\s*\(")
    text_scaler_hits = grep(ctx, ctx.ui_files, r"\btextScaler\b|MediaQuery\.textScalerOf")
    if text_painter_hits and not text_scaler_hits:
        out.append(
            Finding(
                "WARN",
                "Custom painted text respects text scaling",
                f"{len(text_painter_hits)} TextPainter usage(s); no textScaler signal",
                "Size painted text through MediaQuery.textScalerOf(context).",
                text_painter_hits,
            )
        )
    elif text_scaler_hits:
        out.append(Finding("PASS", "Custom painted text respects text scaling", "textScaler signal found", locs=text_scaler_hits[:8]))
    else:
        out.append(Finding("INFO", "Custom painted text respects text scaling", "no TextPainter usage found"))
    return out


def check_visual_states(ctx: Context) -> list[Finding]:
    out = []
    theme_hits = grep(ctx, ctx.ui_files, r"\b(ThemeData|ColorScheme|Theme\.of)\b")
    if theme_hits:
        out.append(Finding("PASS", "Theme/palette has a central source", f"{len(theme_hits)} theme signal(s)", locs=theme_hits[:8]))
    else:
        out.append(
            Finding(
                "INFO",
                "Theme/palette has a central source",
                "no ThemeData/ColorScheme/Theme.of signal found",
                "Centralize colors/text styles before real art lands.",
            )
        )

    result_hits = grep(ctx, ctx.ui_files, r"\b(won|Won|Game Over|gameOver|GameOver|lost|Lost|score|Score|moves|Moves)\b")
    if result_hits:
        out.append(Finding("PASS", "Player feedback/result UI is visible", f"{len(result_hits)} result/HUD signal(s)", locs=result_hits[:8]))
    else:
        out.append(
            Finding(
                "WARN",
                "Player feedback/result UI is visible",
                "no obvious HUD/result/win/lose feedback found",
                "Show score/progress and explicit win/lose/retry states.",
            )
        )

    async_hits = grep(ctx, ctx.ui_files, r"\b(FutureBuilder|StreamBuilder|CircularProgressIndicator|ConnectionState|hasError|SnackBar|showDialog)\b")
    if async_hits:
        out.append(Finding("PASS", "Async/error states are designed", f"{len(async_hits)} async/error signal(s)", locs=async_hits[:8]))
    else:
        out.append(
            Finding(
                "INFO",
                "Async/error states are designed",
                "no async loading/error surface found; fine for fully local MVPs",
                "When loading assets/levels/saves, show loading, empty, error, and retry states.",
            )
        )

    if re.search(r"\b(shape|icon|label|pattern|symbol)\b", ctx.all_src_text, flags=re.IGNORECASE):
        out.append(Finding("PASS", "State is not color-only", "shape/icon/label/symbol signal found"))
    else:
        out.append(
            Finding(
                "INFO",
                "State is not color-only",
                "no shape/icon/label/symbol signal found",
                "Pair color with icon/text/shape/pattern for selection, success, errors, teams, matched state.",
            )
        )
    return out


def check_flame_ui(ctx: Context) -> list[Finding]:
    out = []
    if not ctx.uses_flame:
        return [Finding("SKIP", "Flame UI overlay checks", "project does not appear to use Flame")]

    gamewidget_hits = grep(ctx, ctx.ui_files, r"\bGameWidget\s*\(")
    if gamewidget_hits:
        out.append(Finding("PASS", "Flame game is embedded through GameWidget", f"{len(gamewidget_hits)} GameWidget usage(s)", locs=gamewidget_hits[:8]))
    else:
        out.append(
            Finding(
                "WARN",
                "Flame game is embedded through GameWidget",
                "Flame dependency/import found but no GameWidget in UI files",
                "Embed Flame in Flutter with GameWidget so menus/HUD/settings stay real widgets.",
            )
        )

    overlay_hits = grep(ctx, ctx.ui_files, r"\boverlayBuilderMap\b|\boverlays\.|\bStack\s*\(")
    if overlay_hits:
        out.append(Finding("PASS", "HUD/menus are Flutter overlays", f"{len(overlay_hits)} overlay signal(s)", locs=overlay_hits[:8]))
    else:
        out.append(
            Finding(
                "WARN",
                "HUD/menus are Flutter overlays",
                "no overlayBuilderMap/overlays/Stack signal found",
                "Keep HUD, pause, menu, settings, result panels in Flutter widgets over the canvas.",
            )
        )

    canvas_hits = gamewidget_taps_without_semantics(ctx)
    if canvas_hits:
        out.append(
            Finding(
                "WARN",
                "Canvas input has an accessible alternative",
                "GameWidget receives taps without same-surface Semantics",
                "Add Semantics on the tap surface or a visible/semantic Flutter control for the same action.",
                canvas_hits,
            )
        )
    else:
        out.append(Finding("PASS", "Canvas input has an accessible alternative", "no unlabeled GameWidget tap surface found"))
    return out


def check_kids_ux(ctx: Context) -> list[Finding]:
    out = []
    forbidden = {
        "ads": r"\b(google_mobile_ads|AdWidget|InterstitialAd|RewardedAd|BannerAd)\b",
        "tracking/analytics": r"\b(firebase_analytics|FacebookAppEvents|Mixpanel|Amplitude|AdvertisingId|IDFA|GAID|AD_ID)\b",
        "external links": r"\b(url_launcher|launchUrl|http://|https://)\b",
        "accounts/sign-in": r"\b(signIn|SignIn|Login|Account|FirebaseAuth|google_sign_in)\b",
        "store/payments": r"\b(in_app_purchase|StoreKit|BillingClient|paywall|subscription|purchase)\b",
    }
    hits = []
    files = ctx.src_files + ([ctx.pubspec] if ctx.pubspec_text else [])
    for label, pattern in forbidden.items():
        label_hits = grep(ctx, files, pattern)
        if label_hits:
            out.append(
                Finding(
                    "WARN",
                    f"Kids UX: no {label}",
                    f"{len(label_hits)} reference(s)",
                    "Remove for kids/Families builds or explicitly gate a 13+ product path.",
                    label_hits[:10],
                )
            )
            hits.extend(label_hits)
    if not hits:
        out.append(Finding("PASS", "Kids UX: no ads/tracking/external-links/accounts/payments", "none detected"))

    if re.search(r"\b(parent|parental|grown.?up)\b", ctx.all_src_text, flags=re.IGNORECASE):
        out.append(Finding("INFO", "Parental gate signal", "parent/grown-up wording found"))
    else:
        out.append(
            Finding(
                "INFO",
                "Parental gate signal",
                "no parental-gate wording found",
                "Only needed when a non-kids build has links, purchases, settings that leave the app, or account flows.",
            )
        )
    return out


def check_test_hooks(ctx: Context) -> list[Finding]:
    out = []
    if ctx.test_files:
        out.append(Finding("PASS", "Widget/unit tests exist", f"{len(ctx.test_files)} test file(s)"))
    else:
        out.append(Finding("WARN", "Widget/unit tests exist", "no *_test.dart files found", "Add unit tests for the core and widget tests for key screens."))

    guideline_terms = [
        "meetsGuideline",
        "labeledTapTargetGuideline",
        "androidTapTargetGuideline",
        "iOSTapTargetGuideline",
        "textContrastGuideline",
    ]
    found = [term for term in guideline_terms if term in ctx.all_test_text]
    if len(found) >= 3:
        out.append(Finding("PASS", "Flutter accessibility guideline tests exist", ", ".join(found)))
    else:
        out.append(
            Finding(
                "WARN",
                "Flutter accessibility guideline tests exist",
                "missing most guideline checks: " + ", ".join(t for t in guideline_terms if t not in found),
                "Add a widget test with ensureSemantics() and meetsGuideline(...) for labels, tap targets, contrast.",
            )
        )

    if "matchesGoldenFile" in ctx.all_test_text:
        out.append(Finding("PASS", "Golden/visual regression hook exists", "matchesGoldenFile found"))
    else:
        out.append(
            Finding(
                "INFO",
                "Golden/visual regression hook exists",
                "no golden test found",
                "Add goldens for stable UI screens once art direction settles.",
            )
        )
    return out


CHECKS = {
    "screen-map": check_screen_map,
    "interaction-a11y": check_interaction_a11y,
    "motion": check_motion,
    "responsive-layout": check_responsive_layout,
    "visual-states": check_visual_states,
    "flame-ui": check_flame_ui,
    "kids-ux": check_kids_ux,
    "test-hooks": check_test_hooks,
}


def run_project(root: str, only: list[str]) -> dict[str, list[Finding]]:
    ctx = Context(root)
    results = {}
    for dim in only:
        try:
            results[dim] = CHECKS[dim](ctx)
        except Exception as e:
            results[dim] = [Finding("WARN", f"{dim} check error", str(e))]
    return results


def summarize(results_by_project: dict[str, dict[str, list[Finding]]]):
    n_pass = n_warn = n_fail = 0
    for results in results_by_project.values():
        for findings in results.values():
            for finding in findings:
                if finding.status == "PASS":
                    n_pass += 1
                elif finding.status == "WARN":
                    n_warn += 1
                elif finding.status == "FAIL":
                    n_fail += 1
    return n_pass, n_warn, n_fail


def print_report(root: str, results_by_project, only: list[str], quiet: bool, no_color: bool):
    use_color = sys.stdout.isatty() and not no_color
    print(f"{TOOL_NAME} {TOOL_VERSION} - {root}\n")
    for project, results in results_by_project.items():
        print(f"## {project}")
        for dim in only:
            findings = results[dim]
            if quiet:
                findings = [f for f in findings if f.status in ("WARN", "FAIL")]
                if not findings:
                    continue
            print(f"-- {dim} --")
            for finding in findings:
                glyph = GLYPHS[finding.status]
                if use_color:
                    glyph = f"{COLORS.get(finding.status, '')}{glyph}{COLORS['_']}"
                print(f"  {glyph} {finding.title}")
                if finding.detail:
                    print(f"      {finding.detail}")
                if finding.status in ("WARN", "FAIL") and finding.fix:
                    print(f"      fix: {finding.fix}")
                for loc in finding.locs[:8]:
                    print(f"        - {loc}")
                if len(finding.locs) > 8:
                    print(f"        - ... and {len(finding.locs) - 8} more")
            print()
    n_pass, n_warn, n_fail = summarize(results_by_project)
    verdict = "FAIL" if n_fail else ("WARN" if n_warn else "PASS")
    if use_color:
        print(f"{COLORS[verdict]}== {verdict} =={COLORS['_']}  {n_pass} pass | {n_warn} warn | {n_fail} fail")
    else:
        print(f"== {verdict} ==  {n_pass} pass | {n_warn} warn | {n_fail} fail")
    print("(static scan; verify final UX on real devices/simulators with screen readers and large text)")


def main() -> int:
    ap = argparse.ArgumentParser(prog=TOOL_NAME, description="Static UX/a11y/game-design gate for Flutter/Flame games.")
    ap.add_argument("path", nargs="?", default=".", help="project or repo root (default: .)")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
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
    for dim in only:
        if dim not in DIMENSIONS:
            print(f"{TOOL_NAME}: unknown dimension '{dim}' (valid: {', '.join(DIMENSIONS)})", file=sys.stderr)
            return 2

    projects = discover_project_roots(root)
    if not projects:
        print(f"{TOOL_NAME}: no pubspec.yaml found under {root}", file=sys.stderr)
        return 2

    results_by_project = {project: run_project(project, only) for project in projects}
    n_pass, n_warn, n_fail = summarize(results_by_project)

    if args.json:
        print(
            json.dumps(
                {
                    "tool": TOOL_NAME,
                    "version": TOOL_VERSION,
                    "root": root,
                    "projects": {
                        project: {dim: [f.as_dict() for f in findings] for dim, findings in results.items()}
                        for project, results in results_by_project.items()
                    },
                    "summary": {"pass": n_pass, "warn": n_warn, "fail": n_fail},
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print_report(root, results_by_project, only, args.quiet, args.no_color)

    if n_fail or (args.strict and n_warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
