"""AsyncMessageBus — priority-aware async message bus with dead-letter queue.

The bus is backed by :class:`asyncio.PriorityQueue`.  Messages are routed by
``recipient_id``; ``None`` means broadcast to all subscribers.

Features
--------
- Typed messages via :class:`~hermes_orchestrator.schemas.AgentMessage`
- Priority levels (CRITICAL → LOW)
- Dead-letter queue (DLQ) for messages that exceed ``max_retries``
- Back-pressure: ``publish`` blocks when the queue is full (configurable ``maxsize``)
- Subscriber callbacks registered per ``recipient_id`` or wildcard ``"*"``

Usage::

    bus = AsyncMessageBus()
    await bus.start()

    async def handler(msg: AgentMessage) -> None:
        print(msg.payload)

    bus.subscribe("agent_1", handler)
    await bus.publish(AgentMessage(sender_id="sys", recipient_id="agent_1",
                                    topic="ping", payload={"seq": 1}))
    await bus.stop()
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from hermes_orchestrator.schemas import AgentMessage, MessageStatus

log = structlog.get_logger(__name__)

MessageHandler = Callable[[AgentMessage], Coroutine[Any, Any, None]]

# Priority queue items: (priority_int, sequence_number, message)
_QueueItem = tuple[int, int, AgentMessage]


class AsyncMessageBus:
    """Priority async message bus.

    Parameters
    ----------
    maxsize:
        Maximum queue depth (0 = unlimited).  When the queue is full,
        :meth:`publish` will block until space is available.
    worker_count:
        Number of concurrent message-dispatch worker coroutines.
    """

    def __init__(
        self,
        maxsize: int = 1000,
        worker_count: int = 4,
    ) -> None:
        self._queue: asyncio.PriorityQueue[_QueueItem] = asyncio.PriorityQueue(maxsize=maxsize)
        self._dlq: list[AgentMessage] = []
        self._subscribers: dict[str, list[MessageHandler]] = {}
        self._worker_count = worker_count
        self._workers: list[asyncio.Task[None]] = []
        self._seq: int = 0
        self._running = False

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Start the dispatch workers."""
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(self._dispatch_loop(), name=f"bus_worker_{i}")
            for i in range(self._worker_count)
        ]
        log.info("message_bus.started", worker_count=self._worker_count)

    async def stop(self, drain_timeout: float = 5.0) -> None:
        """Stop the bus, optionally draining in-flight messages.

        Parameters
        ----------
        drain_timeout:
            Seconds to wait for the queue to drain before cancelling workers.
        """
        if not self._running:
            return
        self._running = False

        # Wait for queue to drain within the timeout.
        try:
            await asyncio.wait_for(self._queue.join(), timeout=drain_timeout)
        except TimeoutError:
            log.warning("message_bus.drain_timeout", timeout=drain_timeout)

        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        log.info("message_bus.stopped", dlq_size=len(self._dlq))

    # ------------------------------------------------------------------ #
    # Subscription                                                         #
    # ------------------------------------------------------------------ #

    def subscribe(self, recipient_id: str, handler: MessageHandler) -> None:
        """Register *handler* to receive messages for *recipient_id*.

        Use ``"*"`` as *recipient_id* to subscribe to all messages (broadcast).

        Parameters
        ----------
        recipient_id:
            Agent ID, or ``"*"`` for wildcard.
        handler:
            Async callable ``async def handler(msg: AgentMessage) -> None``.
        """
        self._subscribers.setdefault(recipient_id, []).append(handler)
        log.debug("message_bus.subscribed", recipient_id=recipient_id)

    def unsubscribe(self, recipient_id: str, handler: MessageHandler) -> bool:
        """Remove a specific handler for *recipient_id*.

        Returns
        -------
        bool
            ``True`` if the handler was found and removed.
        """
        handlers = self._subscribers.get(recipient_id, [])
        try:
            handlers.remove(handler)
            return True
        except ValueError:
            return False

    # ------------------------------------------------------------------ #
    # Publishing                                                           #
    # ------------------------------------------------------------------ #

    async def publish(self, message: AgentMessage) -> None:
        """Enqueue *message* for dispatch.

        Blocks if the queue is at capacity (back-pressure).

        Parameters
        ----------
        message:
            The message to send.
        """
        self._seq += 1
        item: _QueueItem = (int(message.priority), self._seq, message)
        await self._queue.put(item)
        log.debug(
            "message_bus.published",
            id=message.id,
            topic=message.topic,
            priority=message.priority.name,
        )

    def publish_nowait(self, message: AgentMessage) -> None:
        """Non-blocking publish.  Raises ``asyncio.QueueFull`` if queue is full."""
        self._seq += 1
        item: _QueueItem = (int(message.priority), self._seq, message)
        self._queue.put_nowait(item)

    # ------------------------------------------------------------------ #
    # Dead-letter queue                                                    #
    # ------------------------------------------------------------------ #

    @property
    def dead_letters(self) -> list[AgentMessage]:
        """Read-only view of failed messages in the DLQ."""
        return list(self._dlq)

    def clear_dlq(self) -> int:
        """Clear the DLQ and return the number of messages removed."""
        count = len(self._dlq)
        self._dlq.clear()
        return count

    # ------------------------------------------------------------------ #
    # Internal dispatch loop                                               #
    # ------------------------------------------------------------------ #

    async def _dispatch_loop(self) -> None:
        while True:
            try:
                _, _, message = await self._queue.get()
                try:
                    await self._dispatch(message)
                except Exception:
                    log.error(
                        "message_bus.dispatch_error",
                        id=message.id,
                        topic=message.topic,
                        exc_info=True,
                    )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break

    async def _dispatch(self, message: AgentMessage) -> None:
        """Route message to matching handlers."""
        message = message.model_copy(update={"status": MessageStatus.PROCESSING})

        handlers: list[MessageHandler] = []
        # Targeted handlers
        if message.recipient_id and message.recipient_id in self._subscribers:
            handlers.extend(self._subscribers[message.recipient_id])
        # Wildcard handlers
        if "*" in self._subscribers:
            handlers.extend(self._subscribers["*"])

        if not handlers:
            log.debug("message_bus.no_handlers", topic=message.topic, id=message.id)
            return

        for handler in handlers:
            try:
                await handler(message)
            except Exception as exc:
                message = message.model_copy(update={"retry_count": message.retry_count + 1})
                if message.retry_count >= message.max_retries:
                    dead = message.model_copy(update={"status": MessageStatus.DEAD_LETTERED})
                    self._dlq.append(dead)
                    log.error(
                        "message_bus.dead_lettered",
                        id=message.id,
                        topic=message.topic,
                        retries=message.retry_count,
                        error=str(exc),
                    )
                else:
                    # Re-queue with same priority for retry.
                    await self.publish(message)
