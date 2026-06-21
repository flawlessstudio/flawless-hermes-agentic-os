"""Data/Analytics agent — SQL, CSV, ChromaDB, and dataframe summarization."""

from __future__ import annotations

import json
import statistics
from typing import Any

import structlog

from hermes_orchestrator.agent import BaseAgent
from hermes_orchestrator.schemas import AgentConfig, ToolCall, ToolResult

log = structlog.get_logger(__name__)


class DataAgent(BaseAgent):
    """Specialized agent for data engineering and analytics workflows."""

    ALLOWED_TOOLS: frozenset[str] = frozenset(
        {
            "execute_sql",
            "load_csv",
            "describe_schema",
            "query_chromadb",
            "summarize_dataframe",
        }
    )

    TOOL_SCHEMAS: list[dict[str, Any]] = [  # noqa: RUF012
        {
            "name": "execute_sql",
            "description": "Run a DuckDB SQL query in-process and return results as JSON.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "DuckDB SQL query to execute."},
                    "database": {
                        "type": "string",
                        "description": "Database path or ':memory:' for in-process.",
                        "default": ":memory:",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "load_csv",
            "description": "Load a CSV file into DuckDB in-memory and return schema info.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the CSV file."},
                    "table_name": {
                        "type": "string",
                        "description": "Name for the in-memory table.",
                        "default": "data",
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "describe_schema",
            "description": "List all tables and their columns in a DuckDB database.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "Database path or ':memory:'.",
                        "default": ":memory:",
                    }
                },
                "required": [],
            },
        },
        {
            "name": "query_chromadb",
            "description": "Query a ChromaDB collection for semantically similar documents.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "description": "ChromaDB collection name."},
                    "query": {"type": "string", "description": "Natural language query."},
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results to return.",
                        "default": 5,
                    },
                },
                "required": ["collection", "query"],
            },
        },
        {
            "name": "summarize_dataframe",
            "description": "Compute statistical summary of a list-of-dicts dataset.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of dicts representing rows.",
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional subset of columns to summarize.",
                    },
                },
                "required": ["data"],
            },
        },
    ]

    async def handle_tool(self, call: ToolCall) -> ToolResult:
        """Execute a verified tool call."""
        try:
            if call.tool_name == "execute_sql":
                return await self._execute_sql(call)
            if call.tool_name == "load_csv":
                return await self._load_csv(call)
            if call.tool_name == "describe_schema":
                return await self._describe_schema(call)
            if call.tool_name == "query_chromadb":
                return await self._query_chromadb(call)
            if call.tool_name == "summarize_dataframe":
                return await self._summarize_dataframe(call)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Tool '{call.tool_name}' not implemented in DataAgent",
            )
        except Exception as exc:
            log.error("data_agent.tool_error", tool=call.tool_name, error=str(exc))
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
            )

    async def _execute_sql(self, call: ToolCall) -> ToolResult:
        try:
            import duckdb
        except ImportError:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error="duckdb not installed. Install with: pip install duckdb",
            )
        query = call.arguments["query"]
        database = call.arguments.get("database", ":memory:")
        try:
            con = duckdb.connect(database)
            relation = con.execute(query)
            rows = relation.fetchall()
            columns = [desc[0] for desc in relation.description] if relation.description else []
            result_dicts = [dict(zip(columns, row)) for row in rows]
            con.close()
            log.info("data_agent.sql_ok", rows=len(result_dicts), query=query[:80])
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                result=json.dumps({"columns": columns, "rows": result_dicts, "count": len(rows)}),
            )
        except Exception as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"SQL error: {exc}",
            )

    async def _load_csv(self, call: ToolCall) -> ToolResult:
        try:
            import duckdb
        except ImportError:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error="duckdb not installed. Install with: pip install duckdb",
            )
        from pathlib import Path

        path = call.arguments["path"]
        table_name = call.arguments.get("table_name", "data")
        if not Path(path).exists():
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"CSV file not found: {path}",
            )
        try:
            con = duckdb.connect(":memory:")
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{path}')")
            schema_rows = con.execute(f"DESCRIBE {table_name}").fetchall()
            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            schema = [{"column": r[0], "type": r[1]} for r in schema_rows]
            con.close()
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                result=json.dumps(
                    {"table": table_name, "row_count": count, "schema": schema}, indent=2
                ),
            )
        except Exception as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"CSV load error: {exc}",
            )

    async def _describe_schema(self, call: ToolCall) -> ToolResult:
        try:
            import duckdb
        except ImportError:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error="duckdb not installed. Install with: pip install duckdb",
            )
        database = call.arguments.get("database", ":memory:")
        try:
            con = duckdb.connect(database)
            tables = con.execute("SHOW TABLES").fetchall()
            schema: dict[str, Any] = {}
            for (table_name,) in tables:
                cols = con.execute(f"DESCRIBE {table_name}").fetchall()
                schema[table_name] = [{"column": c[0], "type": c[1]} for c in cols]
            con.close()
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                result=json.dumps(schema, indent=2),
            )
        except Exception as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Schema describe error: {exc}",
            )

    async def _query_chromadb(self, call: ToolCall) -> ToolResult:
        try:
            import chromadb  # type: ignore[import-untyped]
        except ImportError:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=(
                    "chromadb not installed. "
                    "Install with: pip install chromadb"
                ),
            )
        collection_name = call.arguments["collection"]
        query = call.arguments["query"]
        n_results = int(call.arguments.get("n_results", 5))
        try:
            client = chromadb.Client()
            collection = client.get_collection(collection_name)
            results = collection.query(query_texts=[query], n_results=n_results)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                result=json.dumps(results, indent=2, default=str),
            )
        except Exception as exc:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"ChromaDB query error: {exc}",
            )

    async def _summarize_dataframe(self, call: ToolCall) -> ToolResult:
        data: list[dict[str, Any]] = call.arguments["data"]
        columns: list[str] | None = call.arguments.get("columns")
        if not data:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error="Empty dataset — nothing to summarize",
            )
        all_keys = list(data[0].keys()) if data else []
        target_cols = columns if columns else all_keys
        summary: dict[str, Any] = {"row_count": len(data), "columns": {}}
        for col in target_cols:
            values = [row.get(col) for row in data if row.get(col) is not None]
            numeric = [v for v in values if isinstance(v, (int, float))]
            col_info: dict[str, Any] = {
                "non_null_count": len(values),
                "null_count": len(data) - len(values),
            }
            if numeric:
                col_info.update(
                    {
                        "type": "numeric",
                        "min": min(numeric),
                        "max": max(numeric),
                        "mean": round(statistics.mean(numeric), 4),
                        "median": round(statistics.median(numeric), 4),
                    }
                )
                if len(numeric) > 1:
                    col_info["stdev"] = round(statistics.stdev(numeric), 4)
            else:
                str_values = [str(v) for v in values]
                col_info["type"] = "categorical"
                unique = list(dict.fromkeys(str_values))
                col_info["unique_count"] = len(unique)
                col_info["sample_values"] = unique[:5]
            summary["columns"][col] = col_info
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            result=json.dumps(summary, indent=2),
        )


def make_data_agent() -> DataAgent:
    """Factory: create a DataAgent with default configuration."""
    config = AgentConfig(
        agent_id="data",
        model="claude-sonnet-4-6",
        allowed_tools=DataAgent.ALLOWED_TOOLS,
        system_prompt=(
            "You are a data engineering and analytics agent for the Hermes Agent OS. "
            "You specialize in SQL (DuckDB), CSV processing, vector search (ChromaDB), "
            "and statistical data summarization. "
            "Always validate data quality before analysis. "
            "Flag schema issues, null rates, and outliers. "
            "Prefer typed, reproducible queries. Never load untrusted data without validation."
        ),
    )
    return DataAgent(config=config)
