"""Pruebas del agente local, sin Ollama ni red."""

from __future__ import annotations

import subprocess
import shutil
import sys
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from autodev.core import AgentError, Ollama, Session, WorkspaceTools, _safe_path, parse_text_tool_calls


class FakeOllama:
    def __init__(self):
        self.count = 0

    def chat(self, model, messages):
        self.count += 1
        if self.count == 1:
            return {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "read_file", "arguments": {"path": "genesis/motor/demo.py"}}}]}
        if self.count == 2:
            return {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "replace_text", "arguments":
                              {"path": "genesis/motor/demo.py", "old": "VALUE = 1", "new": "VALUE = 2"}}}]}
        return {"role": "assistant", "content": "Cambio mínimo aplicado.", "tool_calls": []}


class FakeOllamaNoTools:
    def __init__(self):
        self.count = 0

    def chat(self, model, messages):
        self.count += 1
        return {"role": "assistant", "content": "Aquí tienes el código que deberías escribir.", "tool_calls": []}


class FakeOllamaNudged(FakeOllama):
    def chat(self, model, messages):
        if self.count == 0:
            self.count += 1
            return {"role": "assistant", "content": "Puedes editar demo.py.", "tool_calls": []}
        if self.count == 1:
            self.count += 1
            self.assert_nudge(messages)
            return {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "read_file", "arguments": {"path": "genesis/motor/demo.py"}}}]}
        if self.count == 2:
            self.count += 1
            return {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "replace_text", "arguments":
                              {"path": "genesis/motor/demo.py", "old": "VALUE = 1", "new": "VALUE = 2"}}}]}
        return {"role": "assistant", "content": "Cambio aplicado.", "tool_calls": []}

    @staticmethod
    def assert_nudge(messages):
        assert "Llama AHORA" in messages[-1]["content"]


class FakeOllamaJsonText:
    def __init__(self):
        self.count = 0

    def chat(self, model, messages):
        self.count += 1
        if self.count == 1:
            return {"role": "assistant", "content":
                    '{"name":"read_file","arguments":{"path":"genesis/motor/demo.py"}}', "tool_calls": []}
        if self.count == 2:
            return {"role": "assistant", "content":
                    '{"name":"replace_text","arguments":{"path":"genesis/motor/demo.py",'
                    '"old":"VALUE = 1","new":"VALUE = 2"}}', "tool_calls": []}
        return {"role": "assistant", "content": "Tarea terminada.", "tool_calls": []}


def _command(path: Path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def _git_status(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True)


class ParsedToolTests(unittest.TestCase):
    def test_parses_two_plain_json_objects(self):
        actual_log = ('{"name": "list_files", "arguments": {"folder": "genesis/motor/calendario.py"}}\n'
                      '{"name": "list_files", "arguments": {"folder": "pruebas/test_azar_calendario.py"}}')
        calls = parse_text_tool_calls(actual_log)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["function"]["name"], "list_files")

    def test_parses_fenced_json(self):
        parsed = parse_text_tool_calls('```json\n{"name":"read_file","arguments":{"path":"x.py"}}\n```')
        self.assertEqual(parsed[0]["function"]["arguments"]["path"], "x.py")

    def test_rejects_non_pure_json_and_unknown_tools(self):
        for content in [
            'Aquí tienes: {"name":"read_file","arguments":{"path":"x.py"}}',
            '{"name":"run_shell","arguments":{"cmd":"del *"}}',
            '{"name":"read_file","arguments":"x.py"}',
            ' '.join(['{"name":"git_diff","arguments":{}}'] * 5),
        ]:
            with self.subTest(content=content[:60]):
                self.assertEqual(parse_text_tool_calls(content), [])


class StructuredOllamaTests(unittest.TestCase):
    def response(self, content):
        return io.BytesIO(json.dumps({"message": {"content": content}}).encode("utf-8"))

    def test_structured_call_and_history_round_trip(self):
        action = {"name": "read_file", "arguments": {"path": "genesis/motor/azar.py"}}
        messages = [{"role": "system", "content": "Instrucciones"},
                    {"role": "assistant", "content": "", "tool_calls": [{"function": action}]},
                    {"role": "tool", "tool_name": "read_file", "content": "contenido real"}]
        with patch("urllib.request.urlopen", return_value=self.response(json.dumps(action))) as request:
            result = Ollama().chat("qwen2.5-coder:7b", messages)
        payload = json.loads(request.call_args.args[0].data)
        self.assertIn("oneOf", payload["format"])
        self.assertNotIn("tools", payload)
        self.assertEqual(payload["messages"][-1]["role"], "user")
        self.assertIn("contenido real", payload["messages"][-1]["content"])
        self.assertEqual(result["tool_calls"][0]["function"], action)
        self.assertEqual(messages[0]["content"], "Instrucciones")

    def test_finish_requests_host_validation(self):
        content = json.dumps({"name": "finish", "arguments": {"summary": "Listo para comprobar"}})
        with patch("urllib.request.urlopen", return_value=self.response(content)):
            result = Ollama().chat("qwen2.5-coder:7b", [{"role": "user", "content": "Tarea"}])
        self.assertEqual(result["content"], "Listo para comprobar")
        self.assertEqual(result["tool_calls"], [])

    def test_prose_and_unknown_tools_are_not_executed(self):
        for content in ["Modifica el archivo así…", '{"name":"shell","arguments":{"cmd":"whoami"}}']:
            with self.subTest(content=content), patch("urllib.request.urlopen", return_value=self.response(content)):
                with self.assertRaises(AgentError):
                    Ollama().chat("qwen2.5-coder:7b", [{"role": "user", "content": "Tarea"}])


class PathsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "genesis").mkdir()
        (self.root / "genesis" / "a.py").write_text("hello\nworld\n", encoding="utf-8")
        self.tools = WorkspaceTools(self.root)
        self.tools.tool_read_file("genesis/a.py")

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

    def test_list_files_with_file_path_recovers_as_read_only(self):
        result = self.tools.tool_list_files("genesis/a.py")
        self.assertIn("list_files para un archivo", result)
        self.assertIn("1: hello", result)

    def test_unique_replacements_only(self):
        self.tools.tool_replace_text("genesis/a.py", "hello", "ciao")
        self.assertIn("ciao", (self.root / "genesis" / "a.py").read_text())
        self.assertTrue(self.tools.call("replace_text", {"path": "genesis/a.py", "old": "absent", "new": "x"}).startswith("ERROR:"))

    def test_create_does_not_overwrite(self):
        self.tools.tool_create_file("pruebas/new_test.py", "VALUE = 1\n")
        self.assertTrue(self.tools.call("create_file", {"path": "pruebas/new_test.py", "content": "x"}).startswith("ERROR:"))

    def test_writes_require_inspection(self):
        tools = WorkspaceTools(self.root)
        self.assertIn("Lee primero", tools.call("create_file", {"path": "new.py", "content": "x = 1"}))
        self.assertIn("Lee primero", tools.call("replace_text", {"path": "genesis/a.py", "old": "hello", "new": "ciao"}))
        self.assertFalse((self.root / "new.py").exists())

    def test_rewrite_requires_full_current_read_and_changes(self):
        tools = WorkspaceTools(self.root)
        self.assertIn("archivo completo", tools.call("rewrite_file", {"path": "genesis/a.py", "content": "new\n"}))
        tools.tool_read_file("genesis/a.py", 1, 1)
        self.assertIn("archivo completo", tools.call("rewrite_file", {"path": "genesis/a.py", "content": "new\n"}))
        tools.tool_read_file("genesis/a.py")
        (self.root / "genesis/a.py").write_text("external\n", encoding="utf-8")
        self.assertIn("cambió", tools.call("rewrite_file", {"path": "genesis/a.py", "content": "new\n"}))
        tools.tool_read_file("genesis/a.py")
        self.assertIn("idéntico", tools.call("rewrite_file", {"path": "genesis/a.py", "content": "external\n"}))
        self.assertIn("REESCRITO", tools.call("rewrite_file", {"path": "genesis/a.py", "content": "new\n"}))
        self.assertEqual((self.root / "genesis/a.py").read_text(), "new\n")
        self.assertIn("archivo completo", tools.call("rewrite_file", {"path": "genesis/a.py", "content": "again\n"}))

    def test_invalid_python_never_replaces_files(self):
        original = (self.root / "genesis/a.py").read_text()
        for name, args in [
            ("create_file", {"path": "invalid.py", "content": "def broken(:"}),
            ("replace_text", {"path": "genesis/a.py", "old": "hello", "new": "def broken(:"}),
            ("rewrite_file", {"path": "genesis/a.py", "content": "def broken(:"}),
        ]:
            with self.subTest(name=name):
                self.assertIn("Python no válido", self.tools.call(name, args))
                self.assertEqual((self.root / "genesis/a.py").read_text(), original)
        self.assertFalse((self.root / "invalid.py").exists())

    def test_symlink_outside_denied(self):
        outside = self.root.parent / (self.root.name + "-outside.py")
        outside.write_text("secret", encoding="utf-8")
        try:
            try:
                (self.root / "link.py").symlink_to(outside)
            except OSError as exc:
                if sys.platform == "win32" and getattr(exc, "winerror", None) == 1314:
                    self.skipTest("Windows no permite crear symlinks con los permisos actuales")
                raise
            with self.assertRaises(AgentError):
                _safe_path(self.root, "link.py", writable=True)
        finally:
            outside.unlink(missing_ok=True)

    @unittest.skipUnless(sys.platform == "win32", "Las junctions son propias de Windows")
    def test_junction_outside_denied(self):
        # Las junctions de carpetas no necesitan el privilegio de crear symlinks.
        # Mantienen una comprobación real de escapes en Windows sin elevar permisos.
        with tempfile.TemporaryDirectory() as outside_dir:
            outside = Path(outside_dir)
            (outside / "secret.py").write_text("secret", encoding="utf-8")
            junction = self.root / "external"
            subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                           check=True, capture_output=True)
            try:
                with self.assertRaises(AgentError):
                    _safe_path(self.root, "external/secret.py", writable=True)
            finally:
                junction.rmdir()


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

    def test_new_failing_module_is_checked_before_full_suite(self):
        session = Session.create(self.repo, "Añade una prueba", "qwen2.5-coder:7b", minutes=5)
        root = Path(session.state["worktree"])
        (root / "pruebas/test_new.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n"
            "    def test_new(self):\n        self.assertEqual(unknown_value, 1)\n", encoding="utf-8")
        tools = WorkspaceTools(root)
        with patch.object(tools, "tool_run_tests", wraps=tools.tool_run_tests) as run:
            passed, feedback = session._final_check(root, tools, lambda _: None)
        self.assertFalse(passed)
        self.assertIn("NameError", feedback)
        run.assert_called_once_with("module", "pruebas.test_new")
        self.assertTrue(_git_status(root))

    def test_passing_new_module_still_requires_full_suite(self):
        session = Session.create(self.repo, "Añade una prueba", "qwen2.5-coder:7b", minutes=5)
        root = Path(session.state["worktree"])
        (root / "pruebas/test_new.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n"
            "    def test_new(self):\n        self.assertEqual(2 + 2, 4)\n", encoding="utf-8")
        tools = WorkspaceTools(root)
        with patch.object(tools, "tool_run_tests", wraps=tools.tool_run_tests) as run:
            passed, feedback = session._final_check(root, tools, lambda _: None)
        self.assertTrue(passed, feedback)
        self.assertEqual([call.args for call in run.call_args_list],
                         [("module", "pruebas.test_new"), ("python",)])
        self.assertEqual(_git_status(root), "")

    def test_branch_isolated_with_fake_model(self):
        session = Session.create(self.repo, "Cambia VALUE a 2", "qwen2.5-coder:7b", minutes=5)
        logs = []
        result = session.run(logs.append, threading.Event(), client=FakeOllama())
        self.assertEqual(result, "done", logs)
        self.assertEqual((self.repo / "genesis" / "motor" / "demo.py").read_text(), "VALUE = 1\n")
        self.assertEqual((Path(session.state["worktree"]) / "genesis" / "motor" / "demo.py").read_text(), "VALUE = 2\n")
        self.assertEqual(session.state["status"], "done")
        self.assertTrue(session.state_file.is_file())

    def test_no_tool_calls_fail_instead_of_claiming_completion(self):
        session = Session.create(self.repo, "Cambia VALUE a 2", "qwen2.5-coder:7b", minutes=5)
        client = FakeOllamaNoTools()
        logs = []
        result = session.run(logs.append, threading.Event(), client=client)
        self.assertEqual(result, "paused")
        self.assertEqual(client.count, 3)
        self.assertTrue(any("Prueba fallida" in line for line in logs))
        self.assertTrue(any("Respuesta del modelo" in line for line in logs))

    def test_retry_if_model_finalizes_without_tools(self):
        session = Session.create(self.repo, "Cambia VALUE a 2", "qwen2.5-coder:7b", minutes=5)
        result = session.run(lambda _: None, threading.Event(), client=FakeOllamaNudged())
        self.assertEqual(result, "done")

    def test_plain_json_calls_execute_and_finish(self):
        session = Session.create(self.repo, "Cambia VALUE a 2", "qwen2.5-coder:7b", minutes=5)
        logs = []
        result = session.run(logs.append, threading.Event(), client=FakeOllamaJsonText())
        self.assertEqual(result, "done", logs)
        self.assertTrue(any("llamadas JSON" in line for line in logs))
        self.assertEqual((Path(session.state["worktree"]) / "genesis" / "motor" / "demo.py").read_text(), "VALUE = 2\n")

    def test_alternating_failed_actions_stop_without_commit(self):
        class Alternating:
            count = 0

            def chat(self, model, messages):
                self.count += 1
                if self.count % 2:
                    name, args = "read_file", {"path": "genesis/motor/demo.py"}
                else:
                    name, args = "replace_text", {"path": "genesis/motor/demo.py", "old": "missing", "new": "new"}
                return {"role": "assistant", "content": "", "tool_calls": [
                    {"function": {"name": name, "arguments": args}}]}

        session = Session.create(self.repo, "Reparar un archivo", "qwen2.5-coder:7b", minutes=5)
        model = Alternating()
        logs = []
        self.assertEqual(session.run(logs.append, threading.Event(), client=model), "paused")
        self.assertEqual(model.count, 6)
        self.assertTrue(any("misma acción falló tres veces" in line for line in logs))
        self.assertEqual(_git_status(Path(session.state["worktree"])), "")

    def test_context_preserves_goal_and_latest_review(self):
        session = Session.create(self.repo, "REQUISITOS ORIGINALES", "qwen2.5-coder:7b", minutes=5)
        for _ in range(20):
            session.state["messages"].extend([
                {"role": "assistant", "content": "", "tool_calls": [
                    {"function": {"name": "read_file", "arguments": {"path": "genesis/motor/demo.py"}}}]},
                {"role": "tool", "tool_name": "read_file", "content": "x" * 2000}])
        session.state["messages"].append({"role": "user", "content": "ÚLTIMA REVISIÓN: conservar todos los requisitos"})
        session._trim()
        messages = session.state["messages"]
        self.assertIn("REQUISITOS ORIGINALES", messages[1]["content"])
        self.assertIn("ÚLTIMA REVISIÓN", messages[-1]["content"])
        self.assertLessEqual(sum(len(json.dumps(m, ensure_ascii=False)) for m in messages), 12_000)
        for index, message in enumerate(messages):
            if message["role"] == "tool":
                self.assertIn(messages[index - 1]["role"], {"assistant", "tool"})


if __name__ == "__main__":
    unittest.main()
