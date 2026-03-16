from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.simulation_result import SimulationResult


class SimulationResultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, simulation_id, raw_result: dict, normalized_result: dict) -> SimulationResult:
        stmt = select(SimulationResult).where(SimulationResult.simulation_id == simulation_id)
        existing = self.db.execute(stmt).scalars().first()

        if existing:
            existing.raw_result = raw_result
            existing.normalized_result = normalized_result
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        result = SimulationResult(
            simulation_id=simulation_id,
            raw_result=raw_result,
            normalized_result=normalized_result,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_by_simulation_id(self, simulation_id) -> Optional[SimulationResult]:
        stmt = select(SimulationResult).where(SimulationResult.simulation_id == simulation_id)
        return self.db.execute(stmt).scalars().first()
