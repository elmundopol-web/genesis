"""Pruebas del agente local, sin Ollama ni red."""

from __future__ import annotations

import subprocess
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from autodev.core import AgentError, Session, WorkspaceTools, _safe_path


class FakeOllama:
    def __init__(self):
        self.count = 0

    def chat(self, model, messages):
        self.count += 1
        if self.count == 1:
            return {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "replace_text", "arguments":
                              {"path": "genesis/motor/demo.py", "old": "VALUE = 1", "new": "VALUE = 2"}}}]}
        return {"role": "assistant", "content": "Cambio mínimo aplicado.", "tool_calls": []}


def _command(path: Path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def _git_status(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True)


class PathsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "genesis").mkdir()
        (self.root / "genesis" / "a.py").write_text("hello\nworld\n", encoding="utf-8")
        self.tools = WorkspaceTools(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_refuses_traversal(self):
        for path in ["../outside.py", "/tmp/outside.py", ".git/config", "partidas/partida.db", "autodev/core.py"]:
            with self.subTest(path=path), self.assertRaises(AgentError):
                _safe_path(self.root, path, writable=True)

    def test_reads_selected_lines(self):
        lines = self.tools.tool_read_file("genesis/a.py", start=2)
        self.assertIn("2: world", lines)
        self.assertNotIn("1: hello", lines)

    def test_unique_replacements_only(self):
        self.tools.tool_replace_text("genesis/a.py", "hello", "ciao")
        self.assertIn("ciao", (self.root / "genesis" / "a.py").read_text())
        self.assertTrue(self.tools.call("replace_text", {"path": "genesis/a.py", "old": "absent", "new": "x"}).startswith("ERROR:"))

    def test_create_does_not_overwrite(self):
        self.tools.tool_create_file("pruebas/new_test.py", "VALUE = 1\n")
        self.assertTrue(self.tools.call("create_file", {"path": "pruebas/new_test.py", "content": "x"}).startswith("ERROR:"))

    def test_symlink_outside_denied(self):
        outside = self.root.parent / (self.root.name + "-outside.py")
        outside.write_text("secret", encoding="utf-8")
        try:
            (self.root / "link.py").symlink_to(outside)
            with self.assertRaises(AgentError):
                _safe_path(self.root, "link.py", writable=True)
        finally:
            outside.unlink(missing_ok=True)


@unittest.skipUnless(shutil.which("git"), "Git no está instalado; GENESIS no lo requiere para funcionar")
class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "genesis-project"
        (self.repo / "genesis" / "motor").mkdir(parents=True)
        (self.repo / "pruebas").mkdir()
        (self.repo / "pruebas" / "__init__.py").write_text("", encoding="utf-8")
        (self.repo / "genesis" / "motor" / "demo.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.repo / "pruebas" / "test_demo.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n    def test_demo(self):\n        self.assertTrue(True)\n", encoding="utf-8")
        _command(self.repo, "init", "-b", "main")
        _command(self.repo, "add", "-A")
        _command(self.repo, "-c", "user.name=Tester", "-c", "user.email=test@example.test", "commit", "-m", "base")

    def tearDown(self):
        self.temp.cleanup()

    def test_dirty_repo_not_touched(self):
        (self.repo / "genesis" / "motor" / "demo.py").write_text("VALUE = 5\n", encoding="utf-8")
        with self.assertRaises(AgentError):
            Session.create(self.repo, "Tarea", "qwen2.5-coder:7b")

    def test_stop_keeps_session_resumable(self):
        session = Session.create(self.repo, "Mejora muy pequeña", "qwen2.5-coder:7b", minutes=5)
        stop = threading.Event()
        stop.set()
        result = session.run(lambda line: None, stop, client=FakeOllama())
        self.assertEqual(result, "paused")
        reopened = Session.open(session.state_file)
        self.assertEqual(reopened.state["status"], "paused")

    def test_failed_tests_do_not_commit(self):
        (self.repo / "pruebas" / "test_demo.py").write_text(
            "import unittest\nfrom pathlib import Path\nclass T(unittest.TestCase):\n"
            "    def test_demo(self):\n"
            "        self.assertEqual(Path('genesis/motor/demo.py').read_text().strip(), 'VALUE = 1')\n",
            encoding="utf-8")
        _command(self.repo, "add", "-A")
        _command(self.repo, "-c", "user.name=Tester", "-c", "user.email=test@example.test", "commit", "-m", "more tests")
        session = Session.create(self.repo, "Cambia VALUE a 2", "qwen2.5-coder:7b", minutes=5)
        result = session.run(lambda line: None, threading.Event(), client=FakeOllama())
        self.assertEqual(result, "paused")
        self.assertTrue(_git_status(Path(session.state["worktree"])))

    def test_branch_isolated_with_fake_model(self):
        session = Session.create(self.repo, "Cambia VALUE a 2", "qwen2.5-coder:7b", minutes=5)
        logs = []
        result = session.run(logs.append, threading.Event(), client=FakeOllama())
        self.assertEqual(result, "done", logs)
        self.assertEqual((self.repo / "genesis" / "motor" / "demo.py").read_text(), "VALUE = 1\n")
        self.assertEqual((Path(session.state["worktree"]) / "genesis" / "motor" / "demo.py").read_text(), "VALUE = 2\n")
        self.assertEqual(session.state["status"], "done")
        self.assertTrue(session.state_file.is_file())


if __name__ == "__main__":
    unittest.main()
