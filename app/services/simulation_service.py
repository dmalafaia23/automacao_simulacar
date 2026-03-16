from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.adapters.registry import ExecutorRegistry
from app.models.enums import SimulationStatus, BankCode
from app.models.simulation import Simulation
from app.repositories.simulation_repository import SimulationRepository
from app.repositories.simulation_result_repository import SimulationResultRepository
from app.repositories.simulation_event_repository import SimulationEventRepository


class SimulationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.sim_repo = SimulationRepository(db)
        self.result_repo = SimulationResultRepository(db)
        self.event_repo = SimulationEventRepository(db)
        self.registry = ExecutorRegistry()

    def create_simulation(
        self,
        bank: BankCode,
        input_payload: dict,
        idempotency_key: Optional[str],
        correlation_id: Optional[str],
    ) -> Tuple[Simulation, bool]:
        if idempotency_key:
            existing = self.sim_repo.get_by_idempotency(bank, idempotency_key)
            if existing:
                return existing, False

        simulation = Simulation(
            bank=bank,
            status=SimulationStatus.RECEIVED,
            input_payload=input_payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        simulation = self.sim_repo.create(simulation)
        self.event_repo.add_event(simulation.id, SimulationStatus.RECEIVED, 'Simulation received')

        simulation.status = SimulationStatus.PENDING
        simulation = self.sim_repo.update(simulation)
        self.event_repo.add_event(simulation.id, SimulationStatus.PENDING, 'Simulation queued')

        return simulation, True

    def get_simulation(self, simulation_id) -> Optional[Simulation]:
        return self.sim_repo.get(simulation_id)

    def list_simulations(self, bank: Optional[BankCode], status: Optional[SimulationStatus], limit: int, offset: int):
        return self.sim_repo.list(bank, status, limit, offset)

    def retry_simulation(self, simulation_id) -> Optional[Simulation]:
        simulation = self.sim_repo.get(simulation_id)
        if not simulation:
            return None

        simulation.status = SimulationStatus.PENDING
        simulation.error_message = None
        simulation.attempt_count = (simulation.attempt_count or 0) + 1
        simulation = self.sim_repo.update(simulation)
        self.event_repo.add_event(simulation.id, SimulationStatus.PENDING, 'Simulation re-queued')
        return simulation

    def execute_simulation(self, simulation_id) -> Optional[Simulation]:
        simulation = self.sim_repo.get(simulation_id)
        if not simulation:
            return None

        simulation.status = SimulationStatus.RUNNING
        simulation.started_at = datetime.now(timezone.utc)
        self.sim_repo.update(simulation)
        self.event_repo.add_event(simulation.id, SimulationStatus.RUNNING, 'Simulation running')

        executor = self.registry.get_executor(simulation.bank)
        result = executor.run(simulation.input_payload)

        self.result_repo.upsert(simulation.id, result.raw_result, result.normalized_result)
        simulation.status = SimulationStatus.SUCCESS
        simulation.finished_at = datetime.now(timezone.utc)
        self.sim_repo.update(simulation)
        self.event_repo.add_event(simulation.id, SimulationStatus.SUCCESS, 'Simulation success')
        return simulation

    def fail_simulation(self, simulation_id, status: SimulationStatus, message: str) -> Optional[Simulation]:
        simulation = self.sim_repo.get(simulation_id)
        if not simulation:
            return None
        simulation.status = status
        simulation.error_message = message
        simulation.finished_at = datetime.now(timezone.utc)
        self.sim_repo.update(simulation)
        self.event_repo.add_event(simulation.id, status, message)
        return simulation
