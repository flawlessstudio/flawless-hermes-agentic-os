"""Tests for Sandbox, AsyncMessageBus, and AgentRegistry."""

from __future__ import annotations

import asyncio

import pytest

from hermes_orchestrator.bus import AsyncMessageBus
from hermes_orchestrator.registry import AgentRegistry, RegistrationError
from hermes_orchestrator.sandbox import Sandbox, SandboxViolation
from hermes_orchestrator.schemas import AgentConfig, AgentMessage, MessagePriority, ToolCall

# ─────────────────────────── Sandbox ───────────────────────────────────────


class TestSandbox:
    def test_allowed_tool_passes(self) -> None:
        sandbox = Sandbox("agent_1", frozenset({"search_web", "read_file"}))
        # Should not raise.
        sandbox.check("search_web")
        sandbox.check("read_file")

    def test_disallowed_tool_raises(self) -> None:
        sandbox = Sandbox("agent_1", frozenset({"search_web"}))
        with pytest.raises(SandboxViolation) as exc_info:
            sandbox.check("delete_file")
        assert exc_info.value.tool_name == "delete_file"
        assert exc_info.value.agent_id == "agent_1"

    def test_empty_whitelist_blocks_all(self) -> None:
        sandbox = Sandbox("agent_no_tools", frozenset())
        with pytest.raises(SandboxViolation):
            sandbox.check("anything")

    def test_is_allowed_true(self) -> None:
        sandbox = Sandbox("a", frozenset({"tool_x"}))
        assert sandbox.is_allowed("tool_x") is True

    def test_is_allowed_false(self) -> None:
        sandbox = Sandbox("a", frozenset({"tool_x"}))
        assert sandbox.is_allowed("tool_y") is False

    def test_validate_tool_call_allowed(self) -> None:
        sandbox = Sandbox("a", frozenset({"my_tool"}))
        call = ToolCall(tool_name="my_tool", arguments={})
        sandbox.validate_tool_call(call)  # no exception

    def test_validate_tool_call_denied(self) -> None:
        sandbox = Sandbox("a", frozenset({"my_tool"}))
        call = ToolCall(tool_name="forbidden_tool", arguments={})
        with pytest.raises(SandboxViolation):
            sandbox.validate_tool_call(call)

    def test_sandbox_violation_message_contains_details(self) -> None:
        sandbox = Sandbox("researcher", frozenset({"search_web"}))
        with pytest.raises(SandboxViolation) as exc_info:
            sandbox.check("exec_code")
        msg = str(exc_info.value)
        assert "researcher" in msg
        assert "exec_code" in msg

    def test_repr(self) -> None:
        sandbox = Sandbox("x", frozenset({"a", "b"}))
        assert "Sandbox" in repr(sandbox)
        assert "x" in repr(sandbox)


# ─────────────────────────── AsyncMessageBus ───────────────────────────────


class TestAsyncMessageBus:
    @pytest.mark.asyncio
    async def test_publish_and_receive(self) -> None:
        bus = AsyncMessageBus()
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage) -> None:
            received.append(msg)

        bus.subscribe("agent_1", handler)
        await bus.start()
        try:
            await bus.publish(
                AgentMessage(
                    sender_id="sys",
                    recipient_id="agent_1",
                    topic="ping",
                    payload={"seq": 1},
                )
            )
            await asyncio.sleep(0.1)
        finally:
            await bus.stop()

        assert len(received) == 1
        assert received[0].topic == "ping"

    @pytest.mark.asyncio
    async def test_priority_ordering(self) -> None:
        bus = AsyncMessageBus(worker_count=1)
        order: list[int] = []

        async def handler(msg: AgentMessage) -> None:
            order.append(msg.payload["seq"])
            await asyncio.sleep(0.01)

        bus.subscribe("agent_1", handler)
        await bus.start()
        try:
            # Publish low priority first, then critical.
            await bus.publish(
                AgentMessage(
                    sender_id="s",
                    recipient_id="agent_1",
                    topic="t",
                    payload={"seq": 2},
                    priority=MessagePriority.LOW,
                )
            )
            await bus.publish(
                AgentMessage(
                    sender_id="s",
                    recipient_id="agent_1",
                    topic="t",
                    payload={"seq": 1},
                    priority=MessagePriority.CRITICAL,
                )
            )
            await asyncio.sleep(0.3)
        finally:
            await bus.stop()

        # CRITICAL (seq=1) should be processed before LOW (seq=2).
        assert order[0] == 1
        assert order[1] == 2

    @pytest.mark.asyncio
    async def test_wildcard_subscriber_receives_all(self) -> None:
        bus = AsyncMessageBus()
        received: list[AgentMessage] = []

        async def handler(msg: AgentMessage) -> None:
            received.append(msg)

        bus.subscribe("*", handler)
        await bus.start()
        try:
            for i in range(3):
                await bus.publish(
                    AgentMessage(
                        sender_id="s",
                        recipient_id=f"agent_{i}",
                        topic="t",
                        payload={},
                    )
                )
            await asyncio.sleep(0.2)
        finally:
            await bus.stop()

        assert len(received) == 3

    @pytest.mark.asyncio
    async def test_dead_letter_queue_on_repeated_failure(self) -> None:
        bus = AsyncMessageBus()

        async def failing_handler(msg: AgentMessage) -> None:
            raise RuntimeError("boom")

        bus.subscribe("agent_err", failing_handler)
        await bus.start()
        try:
            await bus.publish(
                AgentMessage(
                    sender_id="s",
                    recipient_id="agent_err",
                    topic="fail",
                    payload={},
                    max_retries=1,
                )
            )
            await asyncio.sleep(0.5)
        finally:
            await bus.stop()

        # After max_retries exceeded, message lands in DLQ.
        assert len(bus.dead_letters) >= 1

    @pytest.mark.asyncio
    async def test_no_handler_is_silent(self) -> None:
        bus = AsyncMessageBus()
        await bus.start()
        try:
            # No subscribers — should not raise.
            await bus.publish(
                AgentMessage(sender_id="s", recipient_id="nobody", topic="t", payload={})
            )
            await asyncio.sleep(0.1)
        finally:
            await bus.stop()


# ─────────────────────────── AgentRegistry ─────────────────────────────────


class _FakeAgent:
    """Minimal stub satisfying what AgentRegistry needs."""

    def __init__(self, agent_id: str) -> None:
        self.config = AgentConfig(agent_id=agent_id)


class TestAgentRegistry:
    def test_register_and_get(self) -> None:
        reg = AgentRegistry()
        agent = _FakeAgent("a1")
        reg.register(agent)  # type: ignore[arg-type]
        assert reg.get("a1") is agent

    def test_duplicate_registration_raises(self) -> None:
        reg = AgentRegistry()
        a = _FakeAgent("dup")
        reg.register(a)  # type: ignore[arg-type]
        with pytest.raises(RegistrationError):
            reg.register(a)  # type: ignore[arg-type]

    def test_deregister(self) -> None:
        reg = AgentRegistry()
        a = _FakeAgent("x")
        reg.register(a)  # type: ignore[arg-type]
        assert reg.deregister("x") is True
        assert reg.get("x") is None

    def test_deregister_missing_returns_false(self) -> None:
        reg = AgentRegistry()
        assert reg.deregister("ghost") is False

    def test_list_ids(self) -> None:
        reg = AgentRegistry()
        for aid in ("c", "a", "b"):
            reg.register(_FakeAgent(aid))  # type: ignore[arg-type]
        assert reg.list_ids() == ["a", "b", "c"]

    def test_count(self) -> None:
        reg = AgentRegistry()
        for i in range(3):
            reg.register(_FakeAgent(f"agent_{i}"))  # type: ignore[arg-type]
        assert reg.count() == 3

    def test_clear(self) -> None:
        reg = AgentRegistry()
        reg.register(_FakeAgent("z"))  # type: ignore[arg-type]
        reg.clear()
        assert reg.count() == 0

    def test_contains(self) -> None:
        reg = AgentRegistry()
        reg.register(_FakeAgent("present"))  # type: ignore[arg-type]
        assert "present" in reg
        assert "absent" not in reg
