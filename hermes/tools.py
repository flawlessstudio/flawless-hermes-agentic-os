"""Tool registry and built-in tools.

Tools are plain functions registered with a name, description, and JSON
Schema. The kernel looks tools up by name when the model requests them and
returns their string result (or an error marked ``is_error``).
"""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class ToolError(Exception):
    """Raised by a tool to report a recoverable failure to the model."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., str]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        fn: Callable[..., str],
    ) -> None:
        if name in self._tools:
            raise ValueError(f"tool {name!r} is already registered")
        self._tools[name] = Tool(name, description, input_schema, fn)

    def schemas(self) -> list[dict[str, Any]]:
        """Tool definitions in Messages-API shape, sorted for cache stability."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in sorted(self._tools.values(), key=lambda t: t.name)
        ]

    def execute(self, name: str, tool_input: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"unknown tool: {name}")
        return tool.fn(**tool_input)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# --- Built-in tools ---------------------------------------------------------

_BIN_OPS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ToolError(f"unsupported expression element: {ast.dump(node)[:80]}")


def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression via the AST — no eval(), no names."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolError(f"invalid expression: {exc}") from exc
    result = _eval_node(tree)
    # Render integers without a trailing .0 for cleaner model consumption.
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return str(result)


def _resolve_in_workspace(workspace: Path, relative: str) -> Path:
    target = (workspace / relative).resolve()
    if not target.is_relative_to(workspace):
        raise ToolError(f"path escapes the workspace: {relative!r}")
    return target


def make_read_file(workspace: Path, max_bytes: int = 65536) -> Callable[..., str]:
    def read_file(path: str) -> str:
        target = _resolve_in_workspace(workspace, path)
        if not target.is_file():
            raise ToolError(f"not a file: {path!r}")
        data = target.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="replace")

    return read_file


def make_list_dir(workspace: Path) -> Callable[..., str]:
    def list_dir(path: str = ".") -> str:
        target = _resolve_in_workspace(workspace, path)
        if not target.is_dir():
            raise ToolError(f"not a directory: {path!r}")
        entries = sorted(
            e.name + ("/" if e.is_dir() else "") for e in target.iterdir()
        )
        return "\n".join(entries) if entries else "(empty)"

    return list_dir


def builtin_registry(workspace: str | Path | None = None) -> ToolRegistry:
    """A registry with the built-in tools, sandboxed to ``workspace``."""
    ws = Path(workspace if workspace is not None else Path.cwd()).resolve()
    registry = ToolRegistry()
    registry.register(
        "calculator",
        "Evaluate an arithmetic expression (+, -, *, /, //, %, **, parentheses). "
        "Call this for any non-trivial arithmetic instead of computing mentally.",
        {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The arithmetic expression, e.g. '(17 * 23) + 4'",
                }
            },
            "required": ["expression"],
        },
        calculator,
    )
    registry.register(
        "read_file",
        "Read a UTF-8 text file inside the workspace. "
        "Call this when the answer depends on file contents.",
        {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to the workspace root",
                }
            },
            "required": ["path"],
        },
        make_read_file(ws),
    )
    registry.register(
        "list_dir",
        "List entries in a workspace directory. Directories end with '/'. "
        "Call this to discover which files exist before reading them.",
        {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to the workspace root; defaults to the root",
                }
            },
            "required": [],
        },
        make_list_dir(ws),
    )
    return registry
