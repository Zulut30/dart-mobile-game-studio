from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / ".agents/skills/dart-mobile-game-studio/scripts"
ASSETS = REPO_ROOT / ".agents/skills/dart-mobile-game-studio/assets"
SYNC_AGENTS = REPO_ROOT / ".agents/agents/sync-agents.py"
SAFE_RUN = SCRIPTS / "safe-run.sh"
VERIFY = SCRIPTS / "verify-flutter-project.sh"
ROUTER = SCRIPTS / "task-router.py"
SELF_REVIEW = SCRIPTS / "self-review-loop.py"
VALIDATE_LEVELS = SCRIPTS / "validate-levels.py"
DOC_DOCTOR = SCRIPTS / "doc-doctor.py"
DART_DOCTOR = SCRIPTS / "dart-doctor.py"
SCAFFOLD = SCRIPTS / "scaffold-game-module.py"
MATERIALIZE_FIXTURES = SCRIPTS / "materialize-template-fixtures.py"
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
RELEASE_CANARY = REPO_ROOT / ".github/workflows/release-canary.yml"
BASH = shutil.which("bash") or "/bin/bash"


def run(
    command: list[str | Path],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    return subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        env=process_env,
        text=True,
        capture_output=True,
        timeout=30,
    )


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo)


def init_repo(repo: Path) -> None:
    repo.mkdir(parents=True)
    for args in (
        ("init", "-q"),
        ("config", "user.email", "skill-tests@example.invalid"),
        ("config", "user.name", "Skill Tests"),
    ):
        result = git(repo, *args)
        if result.returncode:
            raise AssertionError(result.stderr)
    (repo / "tracked.txt").write_text("original\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    result = git(repo, "commit", "-qm", "initial")
    if result.returncode:
        raise AssertionError(result.stderr)


class SafeRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = {"TMPDIR": self.temp.name}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_refuses_to_run_outside_git(self) -> None:
        marker = self.root / "must-not-exist"
        result = run(
            [BASH, SAFE_RUN, "--", BASH, "-c", f"touch '{marker}'"],
            cwd=self.root,
            env=self.env,
        )
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertFalse(marker.exists())
        self.assertIn("refusing to run", result.stderr)

    def test_rejects_allow_dirty_with_commit_before_command(self) -> None:
        repo = self.root / "repo"
        init_repo(repo)
        (repo / "tracked.txt").write_text("user work\n", encoding="utf-8")
        result = run(
            [BASH, SAFE_RUN, "--allow-dirty", "--commit", "--", BASH, "-c", "touch generated.txt"],
            cwd=repo,
            env=self.env,
        )
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertFalse((repo / "generated.txt").exists())
        self.assertEqual((repo / "tracked.txt").read_text(encoding="utf-8"), "user work\n")

    def test_rolls_back_failed_command(self) -> None:
        repo = self.root / "repo"
        init_repo(repo)
        command = "printf 'broken\\n' > tracked.txt; printf 'partial\\n' > generated.txt; exit 7"
        result = run([BASH, SAFE_RUN, "--", BASH, "-c", command], cwd=repo, env=self.env)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual((repo / "tracked.txt").read_text(encoding="utf-8"), "original\n")
        self.assertFalse((repo / "generated.txt").exists())
        self.assertEqual(git(repo, "status", "--porcelain").stdout, "")

    def test_stash_mode_restores_user_work_after_success(self) -> None:
        repo = self.root / "repo"
        init_repo(repo)
        (repo / "tracked.txt").write_text("user work\n", encoding="utf-8")
        result = run(
            [BASH, SAFE_RUN, "--stash", "--", BASH, "-c", "printf 'generated\\n' > generated.txt"],
            cwd=repo,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((repo / "tracked.txt").read_text(encoding="utf-8"), "user work\n")
        self.assertEqual((repo / "generated.txt").read_text(encoding="utf-8"), "generated\n")

    def test_repository_without_head_is_refused(self) -> None:
        repo = self.root / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        result = run(
            [BASH, SAFE_RUN, "--", BASH, "-c", "touch must-not-exist"],
            cwd=repo,
            env=self.env,
        )
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertFalse((repo / "must-not-exist").exists())

    def test_commit_hook_failure_is_not_reported_as_success(self) -> None:
        repo = self.root / "repo"
        init_repo(repo)
        hook = repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        result = run(
            [BASH, SAFE_RUN, "--commit", "--", BASH, "-c", "printf 'generated\\n' > generated.txt"],
            cwd=repo,
            env=self.env,
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertTrue((repo / "generated.txt").exists())
        self.assertEqual(git(repo, "rev-list", "--count", "HEAD").stdout.strip(), "1")


class VerifyProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "app"
        self.project.mkdir()
        (self.project / "pubspec.yaml").write_text(
            "name: sample_app\nenvironment:\n  sdk: '>=3.0.0 <4.0.0'\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_fake_bin(self, *, with_dart: bool) -> tuple[Path, Path]:
        fake_bin = self.root / ("bin-with-dart" if with_dart else "bin-no-sdk")
        fake_bin.mkdir()
        for name in ("bash", "dirname", "find", "grep", "head", "sort"):
            source = shutil.which(name)
            if source:
                os.symlink(source, fake_bin / name)
        log = self.root / "tool.log"
        if with_dart:
            dart = fake_bin / "dart"
            dart.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$*\" >> \"$FAKE_TOOL_LOG\"\n"
                "if [[ \"$1\" == \"--version\" ]]; then echo 'Dart SDK fake'; exit 0; fi\n"
                "if [[ \"$1\" == \"format\" ]]; then exit \"${FAKE_FORMAT_RC:-0}\"; fi\n"
                "exit 0\n",
                encoding="utf-8",
            )
            dart.chmod(0o755)
        return fake_bin, log

    def verify(self, fake_bin: Path, log: Path, **extra: str) -> subprocess.CompletedProcess[str]:
        env = {
            "PATH": str(fake_bin),
            "ROOT": str(self.project),
            "FAKE_TOOL_LOG": str(log),
            **extra,
        }
        return run([BASH, VERIFY], cwd=self.root, env=env)

    def test_missing_sdk_is_unverified_not_success(self) -> None:
        fake_bin, log = self.make_fake_bin(with_dart=False)
        result = self.verify(fake_bin, log)
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn("not verified", result.stderr)

    def test_default_verification_does_not_run_pub_get(self) -> None:
        fake_bin, log = self.make_fake_bin(with_dart=True)
        result = self.verify(fake_bin, log)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = log.read_text(encoding="utf-8")
        self.assertIn("format --output=none --set-exit-if-changed .", calls)
        self.assertIn("analyze", calls)
        self.assertIn("test", calls)
        self.assertNotIn("pub get", calls)

    def test_format_failure_fails_verification(self) -> None:
        fake_bin, log = self.make_fake_bin(with_dart=True)
        result = self.verify(fake_bin, log, FAKE_FORMAT_RC="1")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("format check failed", result.stderr)

    def test_dependency_resolution_is_explicit_opt_in(self) -> None:
        fake_bin, log = self.make_fake_bin(with_dart=True)
        result = self.verify(fake_bin, log, RESOLVE_DEPS="yes")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("pub get", log.read_text(encoding="utf-8"))


class TaskRouterTests(unittest.TestCase):
    def route(self, task: str) -> dict:
        result = run(
            [sys.executable, ROUTER, "--json", "--root", REPO_ROOT, task],
            cwd=REPO_ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_build_appbundle_routes_to_release(self) -> None:
        route = self.route("build appbundle")
        self.assertEqual(route["task_type"], "release")
        self.assertNotIn("ui-ux", route["task_types"])

    def test_writing_tests_is_not_treated_as_a_failure(self) -> None:
        route = self.route("write tests for memory match")
        self.assertEqual(route["task_type"], "testing")
        self.assertNotIn("fix-analyzer-test-failure", route["task_types"])

    def test_compound_task_keeps_both_routes(self) -> None:
        route = self.route("audit accessibility and performance")
        self.assertIn("accessibility", route["task_types"])
        self.assertIn("performance", route["task_types"])


class SelfReviewTests(unittest.TestCase):
    def test_repo_audit_reviews_every_discovered_project(self) -> None:
        result = run(
            [
                sys.executable,
                SELF_REVIEW,
                "audit repository quality",
                "--static-only",
                "--json",
                "--timeout",
                "30",
            ],
            cwd=REPO_ROOT,
            env={"SKILL_SKIP_CLI_TESTS": "yes"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["route"]["projects_reviewed"],
            ["examples/endless_runner", "examples/memory_match"],
        )
        selection = next(item for item in report["checks"] if item["id"] == "project-selection")
        self.assertEqual(selection["status"], "PASS")
        check_ids = {item["id"] for item in report["checks"]}
        self.assertIn("dart-doctor:examples/endless_runner", check_ids)
        self.assertIn("dart-doctor:examples/memory_match", check_ids)


class SyncAgentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        canonical = self.root / ".agents/agents"
        canonical.mkdir(parents=True)
        (canonical / "example-agent.md").write_text(
            "---\n"
            "name: example-agent\n"
            "description: Example generated agent.\n"
            "tools: Read, Grep\n"
            "tier: medium\n"
            "---\n\n"
            "Follow the canonical instructions.\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def sync(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, SYNC_AGENTS, "--root", self.root, *args], cwd=self.root)

    def test_check_is_read_only_and_sync_enforces_exact_mirrors(self) -> None:
        check_result = self.sync("--check")
        self.assertEqual(check_result.returncode, 1, check_result.stdout + check_result.stderr)
        self.assertFalse((self.root / ".claude").exists())
        self.assertFalse((self.root / ".cursor").exists())
        self.assertFalse((self.root / ".codex").exists())

        sync_result = self.sync()
        self.assertEqual(sync_result.returncode, 0, sync_result.stdout + sync_result.stderr)
        expected = [
            self.root / ".claude/agents/example-agent.md",
            self.root / ".cursor/rules/agents/example-agent.mdc",
            self.root / ".codex/agents/example-agent.toml",
        ]
        self.assertTrue(all(path.is_file() for path in expected))
        self.assertEqual(self.sync("--check").returncode, 0)

        stale = self.root / ".codex/agents/stale.toml"
        stale.write_text("name = 'stale'\n", encoding="utf-8")
        stale_check = self.sync("--check")
        self.assertEqual(stale_check.returncode, 1)
        self.assertIn("STALE: .codex/agents/stale.toml", stale_check.stdout)
        self.assertEqual(self.sync().returncode, 0)
        self.assertFalse(stale.exists())


class DocDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.skill = self.root / ".agents/skills/dart-mobile-game-studio"
        (self.skill / "references").mkdir(parents=True)
        (self.skill / "workflows").mkdir()
        agents = self.root / ".agents/agents"
        agents.mkdir(parents=True)
        (self.skill / "references/ok.md").write_text("# OK\n", encoding="utf-8")
        (self.skill / "SKILL.md").write_text(
            "[reference](references/ok.md) and `references/ok.md`\n",
            encoding="utf-8",
        )
        (agents / "example.md").write_text("Read `workflows/missing.md`.\n", encoding="utf-8")
        (self.root / "README.md").write_text("See [missing](docs/missing.md).\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def doctor(self) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, DOC_DOCTOR, "--root", self.root, "--json"], cwd=self.root)

    def test_detects_markdown_and_inline_paths_then_passes_when_fixed(self) -> None:
        result = self.doctor()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["errors"], 2)
        self.assertEqual({item["kind"] for item in payload["findings"]}, {"markdown-link", "inline-path"})

        (self.skill / "workflows/missing.md").write_text("# Workflow\n", encoding="utf-8")
        (self.root / "docs").mkdir()
        (self.root / "docs/missing.md").write_text("# Doc\n", encoding="utf-8")
        fixed = self.doctor()
        self.assertEqual(fixed.returncode, 0, fixed.stdout + fixed.stderr)
        self.assertEqual(json.loads(fixed.stdout)["summary"]["errors"], 0)


class DartDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "lib/game").mkdir(parents=True)
        (self.root / "pubspec.yaml").write_text("name: doctor_fixture\n", encoding="utf-8")
        (self.root / "analysis_options.yaml").write_text(
            "include: package:flutter_lints/flutter.yaml\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def diagnose(self, source: str) -> dict:
        (self.root / "lib/game/game.dart").write_text(source, encoding="utf-8")
        result = run(
            [sys.executable, DART_DOCTOR, self.root, "--only", "performance", "--json", "--no-color"],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def dt_finding(self, report: dict) -> dict:
        return next(
            item
            for item in report["dimensions"]["performance"]
            if item["code"] == "FLAME_DT_IGNORED"
        )

    def test_named_dt_clamp_helper_is_accepted(self) -> None:
        report = self.diagnose(
            "class Game {\n"
            "  void update(double dt) {\n"
            "    final step = Physics.clampDt(dt);\n"
            "    advance(step);\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(self.dt_finding(report)["status"], "PASS")

    def test_comment_or_unrelated_clamp_does_not_hide_unsafe_update(self) -> None:
        report = self.diagnose(
            "class Game {\n"
            "  void update(double dt) {\n"
            "    // Physics.clampDt(dt);\n"
            "    final volume = clampVolume(2);\n"
            "    advance(dt + volume);\n"
            "  }\n"
            "}\n"
        )
        finding = self.dt_finding(report)
        self.assertEqual(finding["status"], "WARN")
        self.assertEqual(finding["locations"], ["lib/game/game.dart:2"])


class ScaffoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def scaffold(self, name: str = "SpaceJump") -> subprocess.CompletedProcess[str]:
        return run(
            [
                sys.executable,
                SCAFFOLD,
                "--name",
                name,
                "--type",
                "simple-platformer",
                "--dest",
                self.root,
            ],
            cwd=self.root,
        )

    def test_rejects_numeric_and_reserved_identifiers_before_writing(self) -> None:
        for invalid_name in ("123", "class"):
            result = self.scaffold(invalid_name)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("valid non-reserved Dart package", result.stderr)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_generates_a_pure_dart_package_with_full_state_transitions(self) -> None:
        result = self.scaffold()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        package = self.root / "space_jump"
        model = (package / "lib/src/space_jump_game.dart").read_text(encoding="utf-8")
        library = (package / "lib/space_jump.dart").read_text(encoding="utf-8")
        tests = (package / "test/space_jump_test.dart").read_text(encoding="utf-8")
        self.assertNotIn("package:flutter", model)
        self.assertNotIn("package:flame", model)
        self.assertIn("enum SpaceJumpState { menu, playing, paused, won, lost }", model)
        for method in ("start", "pause", "resume", "win", "lose", "quitToMenu"):
            self.assertIn(f"void {method}(", model)
        self.assertIn("!dt.isFinite", model)
        self.assertIn("package:test/test.dart", tests)
        self.assertIn("terminal states can restart", tests)
        self.assertTrue(library.startswith("// space_jump"))
        self.assertNotIn("/// space_jump", library)

    def test_existing_files_are_preserved(self) -> None:
        package = self.root / "space_jump"
        package.mkdir()
        readme = package / "README.md"
        readme.write_text("user-owned\n", encoding="utf-8")

        result = self.scaffold()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(readme.read_text(encoding="utf-8"), "user-owned\n")
        self.assertIn("Skipped (already exist, left untouched)", result.stdout)

    def test_non_directory_target_fails_without_traceback(self) -> None:
        (self.root / "space_jump").write_text("occupied\n", encoding="utf-8")
        result = self.scaffold()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("is not a directory", result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)


class TemplateContractTests(unittest.TestCase):
    def read_asset(self, name: str) -> str:
        return (ASSETS / name).read_text(encoding="utf-8")

    def test_pure_models_have_no_renderer_dependencies(self) -> None:
        for name in (
            "flame_game_model_template.dart",
            "tile_game_model_template.dart",
            "seeded_random.dart",
        ):
            source = self.read_asset(name)
            self.assertNotIn("package:flutter", source)
            self.assertNotIn("package:flame", source)
            self.assertNotIn("import 'dart:ui", source)
            if name.endswith("model_template.dart"):
                self.assertIn("menu, playing, paused, won, lost", source)

    def test_renderers_import_instead_of_embedding_their_models(self) -> None:
        flame = self.read_asset("flame_game_template.dart")
        widgets = self.read_asset("flutter_game_widget_template.dart")
        self.assertIn("import 'flame_game_model_template.dart';", flame)
        self.assertNotRegex(flame, r"class\s+GameModel\b")
        self.assertIn("import 'tile_game_model_template.dart';", widgets)
        self.assertNotRegex(widgets, r"class\s+TileGameModel\b")

    def test_widget_template_injects_rng_and_exposes_semantic_tap(self) -> None:
        source = self.read_asset("flutter_game_widget_template.dart")
        self.assertIn("rng: math.Random(1)", source)
        self.assertNotIn("math.Random()", source)
        self.assertIn("onTap: tile.matched ? null : onTap", source)
        self.assertNotIn("withValues", source)
        self.assertIn("GameStatus.lost", source)

    def test_flame_template_advances_model_before_components(self) -> None:
        source = self.read_asset("flame_game_template.dart")
        model_update = source.index("model.advance(clamped)")
        component_update = source.index("super.update(clamped)")
        self.assertLess(model_update, component_update)
        self.assertNotIn("(size / 2).toOffset()", source)
        self.assertIn("if (size.x <= 0 || size.y <= 0) return;", source)


class TemplateFixtureGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.destination = self.root / "fixtures"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def generate(self) -> subprocess.CompletedProcess[str]:
        return run(
            [sys.executable, MATERIALIZE_FIXTURES, "--dest", self.destination],
            cwd=self.root,
        )

    def test_materializes_three_projects_from_exact_canonical_sources(self) -> None:
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            {path.name for path in self.destination.iterdir()},
            {"pure_models", "widgets", "flame"},
        )
        self.assertEqual(
            (self.destination / "widgets/lib/main.dart").read_text(encoding="utf-8"),
            (ASSETS / "flutter_game_widget_template.dart").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (self.destination / "flame/lib/flame_game_template.dart").read_text(encoding="utf-8"),
            (ASSETS / "flame_game_template.dart").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (self.destination / "pure_models/lib/seeded_random.dart").read_text(encoding="utf-8"),
            (ASSETS / "seeded_random.dart").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (self.destination / "widgets/analysis_options.yaml").read_text(encoding="utf-8"),
            (ASSETS / "analysis_options.yaml").read_text(encoding="utf-8"),
        )
        pure_pubspec = (self.destination / "pure_models/pubspec.yaml").read_text(encoding="utf-8")
        self.assertNotIn("flutter:", pure_pubspec)
        self.assertTrue((self.destination / "pure_models/test/model_contract_test.dart").is_file())

    def test_refuses_to_overwrite_existing_output(self) -> None:
        self.assertEqual(self.generate().returncode, 0)
        result = self.generate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("destination must be empty", result.stderr)


class WorkflowContractTests(unittest.TestCase):
    def test_ci_keeps_compiler_templates_and_vm_core_gates(self) -> None:
        source = CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("generated-contracts:", source)
        self.assertIn("fixture: [pure_models, widgets, flame, scaffold_contract]", source)
        self.assertIn("Test pure-Dart core on the VM", source)
        self.assertGreaterEqual(
            source.count("dart format --output=none --set-exit-if-changed ."),
            3,
        )
        self.assertIn("dart test test/board_factory_test.dart", source)
        self.assertIn("dart test test/collision_test.dart", source)

    def test_release_canary_builds_both_examples_for_android_and_ios(self) -> None:
        source = RELEASE_CANARY.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("project: [memory_match, endless_runner]"), 2)
        self.assertIn("${{ runner.temp }}", source)
        self.assertIn("flutter create --no-pub --platforms=android", source)
        self.assertIn("flutter build appbundle --release --no-pub", source)
        self.assertIn("flutter create --no-pub --platforms=ios", source)
        self.assertIn("flutter build ios --release --no-codesign --no-pub", source)


class ValidateLevelsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def validate(self, payload: object) -> subprocess.CompletedProcess[str]:
        level = self.root / "level.json"
        level.write_text(json.dumps(payload), encoding="utf-8")
        return run([sys.executable, VALIDATE_LEVELS, "--force-builtin", level], cwd=self.root)

    def test_builtin_accepts_valid_level(self) -> None:
        result = self.validate({
            "schemaVersion": 1,
            "id": "level_001",
            "size": {"width": 100, "height": 100},
            "entities": [],
        })
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_builtin_rejects_every_schema_violation(self) -> None:
        result = self.validate({
            "schemaVersion": 2,
            "id": "bad",
            "difficulty": 999,
            "size": {"width": 100, "height": 100},
            "entities": [{"id": "e", "kind": "piece", "sizeBox": "wrong"}],
            "unknown": True,
        })
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertIn("must be <= 1", output)
        self.assertIn("must be <= 10", output)
        self.assertIn("must be object", output)
        self.assertIn("unknown property", output)

    def test_wrong_entities_type_never_prints_traceback(self) -> None:
        result = self.validate({
            "schemaVersion": 1,
            "id": "bad_entities",
            "size": {"width": 100, "height": 100},
            "entities": 1,
        })
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        self.assertIn("entities: must be array", result.stdout + result.stderr)

    def test_non_standard_json_number_is_rejected(self) -> None:
        result = self.validate({
            "schemaVersion": 1,
            "id": "nan_level",
            "size": {"width": float("nan"), "height": 100},
            "entities": [],
        })
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("non-standard JSON constant", result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_builtin_refuses_unsupported_schema_keywords(self) -> None:
        schema = self.root / "unsupported-schema.json"
        schema.write_text(json.dumps({"type": "object", "oneOf": [{"required": ["id"]}]}), encoding="utf-8")
        level = self.root / "level.json"
        level.write_text("{}", encoding="utf-8")
        result = run(
            [sys.executable, VALIDATE_LEVELS, "--force-builtin", "--schema", schema, level],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("unsupported built-in keyword 'oneOf'", result.stderr)

    def test_malformed_builtin_schema_never_prints_traceback(self) -> None:
        schema = self.root / "malformed-schema.json"
        schema.write_text(json.dumps({"type": "object", "required": 1}), encoding="utf-8")
        level = self.root / "level.json"
        level.write_text("{}", encoding="utf-8")
        result = run(
            [sys.executable, VALIDATE_LEVELS, "--force-builtin", "--schema", schema, level],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
