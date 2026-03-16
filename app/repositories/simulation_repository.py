from __future__ import annotations

from typing import Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.enums import BankCode, SimulationStatus
from app.models.simulation import Simulation


class SimulationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, simulation: Simulation) -> Simulation:
        self.db.add(simulation)
        self.db.commit()
        self.db.refresh(simulation)
        return simulation

    def get(self, simulation_id) -> Optional[Simulation]:
        return self.db.get(Simulation, simulation_id)

    def get_by_idempotency(self, bank: BankCode, idempotency_key: str) -> Optional[Simulation]:
        stmt = select(Simulation).where(
            Simulation.bank == bank,
            Simulation.idempotency_key == idempotency_key,
        )
        return self.db.execute(stmt).scalars().first()

    def update(self, simulation: Simulation) -> Simulation:
        self.db.add(simulation)
        self.db.commit()
        self.db.refresh(simulation)
        return simulation

    def list(self, bank: Optional[BankCode], status: Optional[SimulationStatus], limit: int, offset: int) -> Tuple[list[Simulation], int]:
        stmt = select(Simulation)
        count_stmt = select(func.count(Simulation.id))

        if bank:
            stmt = stmt.where(Simulation.bank == bank)
            count_stmt = count_stmt.where(Simulation.bank == bank)
        if status:
            stmt = stmt.where(Simulation.status == status)
            count_stmt = count_stmt.where(Simulation.status == status)

        stmt = stmt.order_by(Simulation.created_at.desc()).limit(limit).offset(offset)
        items = self.db.execute(stmt).scalars().all()
        total = self.db.execute(count_stmt).scalar_one()
        return items, total
