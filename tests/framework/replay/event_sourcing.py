"""Event sourcing for distributed replay."""

import uuid
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    MODEL_PREDICTION = "model_prediction"


@dataclass
class SystemEvent:
    """System event for replay."""

    event_id: str
    event_type: EventType
    timestamp: float
    service: str
    action: str
    payload: Dict[str, Any]


@dataclass
class ExecutionTimeline:
    """Execution timeline for reconstruction."""

    trace_id: str
    events: List[SystemEvent]
    start_time: float
    end_time: float


class EventSourcingReplayEngine:
    """Event-sourced replay engine."""

    def __init__(self):
        self.timelines: Dict[str, ExecutionTimeline] = {}
        self.current_events: List[SystemEvent] = []
        self.current_trace_id: Optional[str] = None

    def start_trace(self, trace_id: Optional[str] = None) -> str:
        """Start a new trace."""
        self.current_trace_id = trace_id or str(uuid.uuid4())
        self.current_events = []
        return self.current_trace_id

    def record_event(
        self, event_type: EventType, service: str, action: str, payload: Dict[str, Any]
    ) -> str:
        """Record an event."""
        event = SystemEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=time.time(),
            service=service,
            action=action,
            payload=payload,
        )
        self.current_events.append(event)
        return event.event_id

    def end_trace(self) -> ExecutionTimeline:
        """End current trace."""
        if not self.current_events:
            raise ValueError("No events in trace")

        start_time = min(e.timestamp for e in self.current_events)
        end_time = max(e.timestamp for e in self.current_events)

        timeline = ExecutionTimeline(
            trace_id=self.current_trace_id,
            events=self.current_events,
            start_time=start_time,
            end_time=end_time,
        )

        self.timelines[self.current_trace_id] = timeline
        return timeline
