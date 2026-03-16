from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.simulation_event import SimulationEvent
from app.models.enums import SimulationStatus


class SimulationEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_event(self, simulation_id, status: SimulationStatus, message: str | None = None) -> SimulationEvent:
        event = SimulationEvent(simulation_id=simulation_id, status=status, message=message)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
