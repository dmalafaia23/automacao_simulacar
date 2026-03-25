from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException

from .orchestrator import SimulationOrchestrator
from .schemas import (
    HealthResponse,
    SimulationCreateResponse,
    SimulationRequest,
    SimulationStatusResponse,
)
from .store import JobStore


API_VERSION = "1.0.0"
job_store = JobStore()
orchestrator = SimulationOrchestrator(job_store)

app = FastAPI(title="Automacao Simulacar API", version=API_VERSION)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    current_time = datetime.now().astimezone()
    return HealthResponse(
        status="ok",
        version=API_VERSION,
        current_time=current_time,
        timezone=str(current_time.tzinfo),
    )


@app.post("/simulacoes", response_model=SimulationCreateResponse, status_code=202)
def create_simulation(payload: SimulationRequest) -> SimulationCreateResponse:
    if payload.itau is None and payload.c6bank is None:
        raise HTTPException(status_code=400, detail="Informe ao menos um banco para simular.")

    try:
        job_id = orchestrator.create_job(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SimulationCreateResponse(id=job_id, status="pending")


@app.get("/simulacoes/{job_id}", response_model=SimulationStatusResponse)
def get_simulation(job_id: str) -> SimulationStatusResponse:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Processamento não encontrado.")

    return SimulationStatusResponse(
        id=job.id,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        banks={
            name: {
                "bank": bank.bank,
                "status": bank.status,
                "started_at": bank.started_at,
                "finished_at": bank.finished_at,
                "result": bank.result,
                "error": bank.error,
            }
            for name, bank in job.banks.items()
        },
    )
