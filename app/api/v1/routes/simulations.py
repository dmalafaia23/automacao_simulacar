from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import BankCode, SimulationStatus
from app.repositories.simulation_result_repository import SimulationResultRepository
from app.schemas.simulation import (
    SimulationRequest,
    SimulationCreateResponse,
    SimulationDetailResponse,
    SimulationListResponse,
    SimulationResultResponse,
)
from app.services.simulation_service import SimulationService
from app.workers.tasks import run_simulation


router = APIRouter(prefix='/simulations', tags=['simulations'])


def _to_detail_response(db: Session, simulation) -> SimulationDetailResponse:
    result_repo = SimulationResultRepository(db)
    result = result_repo.get_by_simulation_id(simulation.id)

    result_payload = None
    if result:
        result_payload = SimulationResultResponse(
            raw_result=result.raw_result,
            normalized_result=result.normalized_result,
        )

    return SimulationDetailResponse(
        simulation_id=str(simulation.id),
        bank=simulation.bank,
        status=simulation.status,
        input=simulation.input_payload,
        error_message=simulation.error_message,
        created_at=simulation.created_at.isoformat() if simulation.created_at else None,
        updated_at=simulation.updated_at.isoformat() if simulation.updated_at else None,
        started_at=simulation.started_at.isoformat() if simulation.started_at else None,
        finished_at=simulation.finished_at.isoformat() if simulation.finished_at else None,
        result=result_payload,
    )


@router.post('', status_code=status.HTTP_202_ACCEPTED, response_model=SimulationCreateResponse)

def create_simulation(payload: SimulationRequest, db: Session = Depends(get_db)):
    service = SimulationService(db)

    simulation, created = service.create_simulation(
        bank=payload.bank,
        input_payload=payload.input.model_dump(),
        idempotency_key=payload.idempotency_key,
        correlation_id=payload.correlation_id,
    )

    if created:
        run_simulation.delay(str(simulation.id))

    return SimulationCreateResponse(simulation_id=str(simulation.id), status=simulation.status)


@router.get('/{simulation_id}', response_model=SimulationDetailResponse)

def get_simulation(simulation_id: str, db: Session = Depends(get_db)):
    service = SimulationService(db)
    simulation = service.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail='Simulation not found')
    return _to_detail_response(db, simulation)


@router.get('', response_model=SimulationListResponse)

def list_simulations(
    bank: Optional[BankCode] = Query(None),
    status: Optional[SimulationStatus] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    service = SimulationService(db)
    items, total = service.list_simulations(bank, status, limit, offset)
    return SimulationListResponse(
        items=[_to_detail_response(db, item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post('/{simulation_id}/retry', status_code=status.HTTP_202_ACCEPTED, response_model=SimulationCreateResponse)

def retry_simulation(simulation_id: str, db: Session = Depends(get_db)):
    service = SimulationService(db)
    simulation = service.retry_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail='Simulation not found')

    run_simulation.delay(str(simulation.id))
    return SimulationCreateResponse(simulation_id=str(simulation.id), status=simulation.status)
