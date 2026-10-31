"""Run on Linux: python3 -m unittest discover -s scripts/tests -v

Docker is mocked: tests never start services or change application data.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
MOCK_DOCKER = r'''#!/usr/bin/env python3
import json
import os
import sys
args = sys.argv[1:]
with open(os.environ["MOCK_DOCKER_LOG"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(args) + "\n")
if args == ["info"]:
    sys.exit(1 if os.environ.get("MOCK_ENGINE_OFF") else 0)
if args == ["compose", "version"]:
    sys.exit(1 if os.environ.get("MOCK_COMPOSE_OFF") else 0)
if not args or args[0] != "compose":
    sys.exit(99)
rest = args[1:]
while rest and rest[0] in ("--project-directory", "--env-file", "-f"):
    rest = rest[2:]
if rest and rest[0] == os.environ.get("MOCK_FAIL_COMMAND"):
    print("Simulated Docker failure", file=sys.stderr)
    sys.exit(17)
'''


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "Requires POSIX Bash")
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dubsi launchers ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "team checkout with spaces"
        self.root.mkdir()
        shutil.copytree(SCRIPTS, self.root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "apps/web").mkdir(parents=True)
        (self.root / "infra").mkdir()
        (self.root / ".env.example").write_text("GOOGLE_CLIENT_ID=\n")
        (self.root / "apps/web/.env.example").write_text("NEXT_PUBLIC_GOOGLE_CLIENT_ID=\n")
        (self.root / "infra/docker-compose.local.yml").write_text("services: {}\n")
        executable_dir = Path(self.temp.name) / "bin"
        executable_dir.mkdir()
        executable = executable_dir / "docker"
        executable.write_text(MOCK_DOCKER)
        executable.chmod(0o755)
        self.log = Path(self.temp.name) / "docker.jsonl"
        self.env = dict(os.environ, PATH=str(executable_dir) + os.pathsep + os.environ["PATH"],
                        MOCK_DOCKER_LOG=str(self.log))

    def run_script(self, *args, script="start.sh", **env):
        return subprocess.run(["bash", str(self.root / "scripts" / script), *args],
                              cwd=self.temp.name, env=dict(self.env, **env),
                              capture_output=True, text=True, timeout=20)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def actions(self):
        result = []
        for call in self.calls():
            if not call or call[0] != "compose":
                continue
            args = call[1:]
            while args and args[0] in ("--project-directory", "--env-file", "-f"):
                args = args[2:]
            if args and args[0] != "version":
                result.append(args)
        return result

    def test_start_creates_env_and_quotes_paths_from_another_directory(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        for example, target in ((".env.example", ".env"), ("apps/web/.env.example", "apps/web/.env.local")):
            self.assertEqual((self.root / example).read_bytes(), (self.root / target).read_bytes())
        self.assertEqual(self.actions()[-1], ["up", "--detach", "--wait", "--wait-timeout", "600", "--build"])
        call = self.calls()[-1]
        self.assertEqual(call[call.index("--project-directory") + 1], str(self.root / "infra"))
        self.assertEqual([call[i + 1] for i, part in enumerate(call) if part == "--env-file"],
                         [str(self.root / ".env"), str(self.root / "apps/web/.env.local")])

    def test_existing_env_is_preserved_and_not_executed(self):
        marker = self.root / "should-not-exist"
        text = f"AUTH_SECRET=$(touch '{marker}')\nGOOGLE_CLIENT_ID=\n"
        (self.root / ".env").write_text(text)
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / ".env").read_text(), text)
        self.assertFalse(marker.exists())

    def test_no_build_and_custom_timeout(self):
        result = self.run_script("--no-build", "--timeout", "1800")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.actions()[-1], ["up", "--detach", "--wait", "--wait-timeout", "1800", "--no-build"])

    def test_stop_preserves_volumes(self):
        self.assertEqual(self.run_script("--stop").returncode, 0)
        self.assertEqual(self.actions()[-1], ["down"])
        self.assertNotIn("--volumes", sum(self.calls(), []))

    def test_data_only_targets_exactly_four_services(self):
        services = ["db", "mongodb", "redis", "mailpit"]
        result = self.run_script("--data-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.actions()[-1], ["up", "--detach", "--wait", "--wait-timeout", "600", *services])
        self.assertEqual(self.run_script("--stop", "--data-only").returncode, 0)
        self.assertEqual(self.actions()[-1], ["stop", *services])

    def test_status_and_logs(self):
        for flag, expected in (("--status", ["ps", "--all"]),
                               ("--logs", ["logs", "--follow", "--tail", "100"])):
            with self.subTest(flag=flag):
                result = self.run_script(flag)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.actions()[-1], expected)

    def test_google_ids_support_bom_crlf_quotes_and_comments(self):
        (self.root / ".env").write_bytes(b'\xef\xbb\xbfGOOGLE_CLIENT_ID="matching-id" # comment\r\n')
        (self.root / "apps/web/.env.local").write_bytes(b"NEXT_PUBLIC_GOOGLE_CLIENT_ID='matching-id'\r\n")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mismatched_ids_block_start_but_allow_status_and_stop(self):
        (self.root / ".env").write_text("GOOGLE_CLIENT_ID=one\n")
        (self.root / "apps/web/.env.local").write_text("NEXT_PUBLIC_GOOGLE_CLIENT_ID=two\n")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("client IDs", result.stderr)
        self.assertFalse(any(call[0] == "up" for call in self.actions()))
        self.assertEqual(self.run_script("--status").returncode, 0)
        self.assertEqual(self.run_script("--stop").returncode, 0)

    def test_invalid_options_fail_before_contacting_docker(self):
        for args in (("--stop", "--logs"), ("--unknown",), ("--timeout",),
                     ("--timeout", "29"), ("--timeout", "1801"),
                     ("--timeout", "1e3"), ("--timeout", "600.5")):
            with self.subTest(args=args):
                self.assertNotEqual(self.run_script(*args).returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_help_needs_no_docker(self):
        for script in ("start.sh", "migrate.sh", "seed.sh", "lint-all.sh"):
            with self.subTest(script=script):
                result = self.run_script("--help", script=script, MOCK_ENGINE_OFF="1")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Usage:", result.stdout)
        self.assertEqual(self.calls(), [])

    def test_docker_failures_are_actionable_and_preserve_exit_code(self):
        result = self.run_script(MOCK_ENGINE_OFF="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Docker is unavailable", result.stderr)
        result = self.run_script(MOCK_COMPOSE_OFF="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Compose v2", result.stderr)
        result = self.run_script(MOCK_FAIL_COMMAND="up")
        self.assertEqual(result.returncode, 17)
        self.assertIn("Docker command failed", result.stderr)

    def test_migration_and_seed_use_the_existing_jobs(self):
        result = self.run_script(script="migrate.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.actions()[-1], ["run", "--rm", "--no-deps", "-T", "api", "uv", "run", "--no-sync", "alembic", "upgrade", "head"])
        result = self.run_script(script="seed.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("python -m app.workers.bootstrap", self.actions()[-1][-1])
        self.assertNotIn("--service-ports", sum(self.calls(), []))

    def test_lint_runs_disposable_containers_without_starting_databases(self):
        result = self.run_script(script="lint-all.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        actions = self.actions()
        self.assertFalse(any(call[0] == "up" for call in actions))
        self.assertEqual(len([call for call in actions if call[0] == "run"]), 4)
        self.assertEqual(actions[-1][-3:], ["web", "pnpm", "typecheck"])
        api = next(call for call in actions if "--volume" in call)
        self.assertEqual(api[api.index("--volume") + 1], f"{self.root}/apps/api/tests:/workspace/apps/api/tests:ro")

    def test_all_shell_files_have_lf_endings_and_valid_bash_syntax(self):
        for script in SCRIPTS.glob("*.sh"):
            with self.subTest(script=script.name):
                self.assertNotIn(b"\r", script.read_bytes())
                result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
