"""Resilient operations primitives aligning with the RO spec."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TaskState(StrEnum):
    """Lifecycle states for a resilient operation task."""

    ACKED = "ACKED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    COMPENSATED = "COMPENSATED"


class EventType(StrEnum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    DONE = "done"
    CANCELLED = "cancelled"
    COMPENSATED = "compensated"


@dataclass
class Event:
    subject: str
    event_type: EventType
    seq: int
    idempotency_key: str
    action_version: str
    status: str | None = None
    error_code: str | None = None


@dataclass
class Response:
    state: TaskState
    http_status: int
    events: list[Event] = field(default_factory=list)


def _parse_major(version: str) -> int:
    try:
        return int(version.split(".")[0])
    except (ValueError, IndexError):
        return 0


class AsyncRequirementError(RuntimeError):
    """Raised when an action violates the async-first policy."""


class EventLog:
    """A simple in-memory event log modelling resilient semantics."""

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._seen_keys: set[tuple[str, str, EventType]] = set()
        self._last_seq: dict[str, tuple[int, int]] = {}

    def record(self, event: Event) -> bool:
        key = (event.subject, event.idempotency_key, event.event_type)
        # @req:RO-SEM-001 dedupe repeated events per subject/key/type
        if key in self._seen_keys:
            return False

        major = _parse_major(event.action_version)
        last = self._last_seq.get(event.subject)
        if last:
            last_seq, last_major = last
            if major < last_major:
                return False
            if major == last_major and event.seq < last_seq:
                # @req:RO-SEM-001 ignore out-of-order deliveries
                return False
        # @req:RO-SEQ-001 allow seq reset when major version bumps
        self._events.append(event)
        self._seen_keys.add(key)
        self._last_seq[event.subject] = (event.seq, major)
        return True

    def events(self) -> list[Event]:
        return list(self._events)

    def replay_done(self, subject: str, idempotency_key: str) -> Event | None:
        # @req:RO-SEM-001 expose replay helper for recovery flows
        for event in reversed(self._events):
            if (
                event.subject == subject
                and event.idempotency_key == idempotency_key
                and event.event_type is EventType.DONE
            ):
                return event
        return None


def state_to_event(state: TaskState) -> EventType:
    mapping = {
        TaskState.ACKED: EventType.ACCEPTED,
        TaskState.RUNNING: EventType.RUNNING,
        TaskState.SUCCEEDED: EventType.DONE,
        TaskState.FAILED: EventType.DONE,
        TaskState.CANCELLED: EventType.CANCELLED,
        TaskState.COMPENSATED: EventType.COMPENSATED,
    }
    # @req:RO-NAME-001 ensure consistent state ↔️ event vocabulary
    return mapping[state]


@dataclass
class ActionProfile:
    name: str
    eta_seconds: float


class AsyncFirstEnforcer:
    def __init__(self, registry: dict[str, ActionProfile]) -> None:
        self._registry = registry

    def validate(self, action: str) -> None:
        profile = self._registry.get(action)
        if not profile:
            return
        # @req:RO-RESP-003 fail registry entries that exceed 2s ETA
        if profile.eta_seconds > 2:
            raise AsyncRequirementError(
                f"Action {action} must use async response (ETA {profile.eta_seconds}s)"
            )


@dataclass
class TaskStateMachine:
    subject: str
    idempotency_key: str
    action_version: str
    event_log: EventLog
    seq: int = 0
    state: TaskState = TaskState.ACKED
    side_effects_observed: bool = False
    _cancelled_once: bool = False
    _emitted: list[Event] = field(default_factory=list)

    # @req:RO-STM-001 incorporate cancel + compensate handling

    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq

    def mark_side_effects(self) -> None:
        self.side_effects_observed = True

    def ack(self) -> Event | None:
        # emit accepted ack for async flows without state change
        return self._emit(TaskState.ACKED)

    def start(self) -> None:
        if self.state is not TaskState.ACKED:
            raise ValueError("Task must be ACKED before starting")
        # @req:RO-STM-002 enforce ACKED → RUNNING transition
        self.state = TaskState.RUNNING
        self._emit(self.state)

    def succeed(self) -> None:
        if self.state is not TaskState.RUNNING:
            raise ValueError("Task must be RUNNING before completing")
        self.state = TaskState.SUCCEEDED
        self._emit(self.state)

    def fail(self, error_code: str) -> None:
        if self.state is not TaskState.RUNNING:
            raise ValueError("Task must be RUNNING before failing")
        self.state = TaskState.FAILED
        self._emit(self.state, error_code=error_code)

    def cancel(self) -> Response:
        if self._cancelled_once:
            # @req:RO-CANCEL-002 ignore duplicates
            return Response(self.state, 200)

        if self.state in {TaskState.SUCCEEDED, TaskState.FAILED, TaskState.COMPENSATED}:
            # @req:RO-CANCEL-003 no-op after completion
            self._cancelled_once = True
            return Response(self.state, 200)

        if self.side_effects_observed:
            self.state = TaskState.COMPENSATED
        else:
            self.state = TaskState.CANCELLED
        event = self._emit(self.state)
        self._cancelled_once = True
        status_code = 202  # @req:RO-CANCEL-001 surface cancellation acknowledgement
        return Response(self.state, status_code, [event] if event else [])

    def _emit(
        self,
        state: TaskState,
        *,
        error_code: str | None = None,
    ) -> Event | None:
        event_type = state_to_event(state)
        seq = self._next_seq()
        status_value: str | None = None
        if state in {
            TaskState.SUCCEEDED,
            TaskState.FAILED,
            TaskState.CANCELLED,
            TaskState.COMPENSATED,
        }:
            status_value = state.value
        event = Event(
            subject=self.subject,
            event_type=event_type,
            seq=seq,
            idempotency_key=self.idempotency_key,
            action_version=self.action_version,
            status=status_value,
            error_code=error_code if state is TaskState.FAILED else None,
        )
        recorded = self.event_log.record(event)
        if recorded:
            # @req:RO-EVENT-001 done payload carries status + optional error
            self._emitted.append(event)
            return event
        return None

    def pull_emitted(self) -> list[Event]:
        events = list(self._emitted)
        self._emitted.clear()
        return events


class OperationResponder:
    def __init__(self, event_log: EventLog) -> None:
        self.event_log = event_log

    def respond_sync(
        self,
        machine: TaskStateMachine,
        *,
        success: bool,
        error_code: str | None = None,
    ) -> Response:
        if success:
            machine.succeed()
        else:
            machine.fail(error_code or "UNKNOWN_ERROR")
        events = machine.pull_emitted()
        # @req:RO-RESP-001 sync handlers finish in <2s returning terminal state
        return Response(machine.state, 200, events)

    def respond_async(self, machine: TaskStateMachine) -> Response:
        machine.ack()
        events = machine.pull_emitted()
        # @req:RO-RESP-002 ack path returns ACKED + event placeholder
        # @req:RO-RESP-004 represented with HTTP 202 recommendation
        return Response(TaskState.ACKED, 202, events)
