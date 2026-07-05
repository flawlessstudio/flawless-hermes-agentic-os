import tempfile
import unittest
from pathlib import Path

from hermes.kernel import Hermes
from hermes.providers import MockProvider, ProviderResponse
from hermes.tools import ToolError, builtin_registry, calculator


def text_response(text: str) -> ProviderResponse:
    return ProviderResponse(
        content=[{"type": "text", "text": text}], stop_reason="end_turn"
    )


def tool_response(tool_id: str, name: str, tool_input: dict) -> ProviderResponse:
    return ProviderResponse(
        content=[{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}],
        stop_reason="tool_use",
    )


class KernelTests(unittest.TestCase):
    def test_direct_answer_without_tools(self):
        provider = MockProvider([text_response("Paris.")])
        agent = Hermes(provider, builtin_registry())
        result = agent.run("Capital of France?")
        self.assertEqual(result.answer, "Paris.")
        self.assertEqual(result.steps, 1)
        self.assertEqual(result.tool_calls, [])

    def test_tool_loop_executes_and_feeds_back(self):
        provider = MockProvider(
            [
                tool_response("t1", "calculator", {"expression": "6 * 7"}),
                text_response("The answer is 42."),
            ]
        )
        agent = Hermes(provider, builtin_registry())
        result = agent.run("What is 6 * 7?")

        self.assertEqual(result.answer, "The answer is 42.")
        self.assertEqual(result.steps, 2)
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0]["output"], "42")

        # The second provider call must contain the tool_result in ONE user message.
        second_call = provider.calls[1]
        last = second_call[-1]
        self.assertEqual(last["role"], "user")
        self.assertEqual(last["content"][0]["type"], "tool_result")
        self.assertEqual(last["content"][0]["tool_use_id"], "t1")
        self.assertEqual(last["content"][0]["content"], "42")

    def test_parallel_tool_calls_return_in_one_message(self):
        provider = MockProvider(
            [
                ProviderResponse(
                    content=[
                        {"type": "tool_use", "id": "a", "name": "calculator",
                         "input": {"expression": "1 + 1"}},
                        {"type": "tool_use", "id": "b", "name": "calculator",
                         "input": {"expression": "2 + 2"}},
                    ],
                    stop_reason="tool_use",
                ),
                text_response("2 and 4."),
            ]
        )
        agent = Hermes(provider, builtin_registry())
        result = agent.run("Compute both.")
        last = provider.calls[1][-1]
        self.assertEqual(last["role"], "user")
        self.assertEqual([b["tool_use_id"] for b in last["content"]], ["a", "b"])
        self.assertEqual(len(result.tool_calls), 2)

    def test_tool_error_is_reported_not_raised(self):
        provider = MockProvider(
            [
                tool_response("t1", "calculator", {"expression": "import os"}),
                text_response("That expression was invalid."),
            ]
        )
        agent = Hermes(provider, builtin_registry())
        result = agent.run("Evaluate something bad.")
        self.assertTrue(result.tool_calls[0]["is_error"])
        block = provider.calls[1][-1]["content"][0]
        self.assertTrue(block["is_error"])
        self.assertIn("Error:", block["content"])

    def test_unknown_tool_is_recoverable(self):
        provider = MockProvider(
            [
                tool_response("t1", "no_such_tool", {}),
                text_response("Recovered."),
            ]
        )
        agent = Hermes(provider, builtin_registry())
        result = agent.run("Use a bogus tool.")
        self.assertTrue(result.tool_calls[0]["is_error"])
        self.assertEqual(result.answer, "Recovered.")

    def test_step_limit_stops_runaway_loop(self):
        responses = [
            tool_response(f"t{i}", "calculator", {"expression": "1 + 1"})
            for i in range(5)
        ]
        provider = MockProvider(responses)
        agent = Hermes(provider, builtin_registry(), max_steps=3)
        result = agent.run("Loop forever.")
        self.assertTrue(result.stopped_early)
        self.assertEqual(result.steps, 3)

    def test_refusal_stop_reason(self):
        provider = MockProvider(
            [ProviderResponse(content=[], stop_reason="refusal")]
        )
        agent = Hermes(provider, builtin_registry())
        result = agent.run("Something declined.")
        self.assertIn("declined", result.answer)


class CalculatorTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(calculator("(17 * 23) + 4"), "395")
        self.assertEqual(calculator("10 / 4"), "2.5")
        self.assertEqual(calculator("2 ** 10"), "1024")
        self.assertEqual(calculator("-5 + 3"), "-2")

    def test_rejects_names_and_calls(self):
        for bad in ("__import__('os')", "x + 1", "print(1)", "[1,2]"):
            with self.assertRaises(ToolError):
                calculator(bad)


class WorkspaceToolTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        (self.ws / "notes.txt").write_text("hello hermes")
        (self.ws / "sub").mkdir()
        self.registry = builtin_registry(self.ws)

    def tearDown(self):
        self._tmp.cleanup()

    def test_read_file(self):
        self.assertEqual(self.registry.execute("read_file", {"path": "notes.txt"}),
                         "hello hermes")

    def test_list_dir(self):
        listing = self.registry.execute("list_dir", {})
        self.assertIn("notes.txt", listing)
        self.assertIn("sub/", listing)

    def test_path_traversal_blocked(self):
        with self.assertRaises(ToolError):
            self.registry.execute("read_file", {"path": "../../etc/passwd"})

    def test_missing_file_is_tool_error(self):
        with self.assertRaises(ToolError):
            self.registry.execute("read_file", {"path": "nope.txt"})


class SchemaTests(unittest.TestCase):
    def test_schemas_are_sorted_and_complete(self):
        registry = builtin_registry()
        schemas = registry.schemas()
        names = [s["name"] for s in schemas]
        self.assertEqual(names, sorted(names))
        for schema in schemas:
            self.assertIn("description", schema)
            self.assertEqual(schema["input_schema"]["type"], "object")


if __name__ == "__main__":
    unittest.main()
