from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException

from .external_api import (
    ExternalAPIConfigError,
    ExternalAPIRequestError,
    get_processing,
    find_vehicle_by_plate,
    get_external_api_config,
    list_banks,
    list_vehicles,
)
from .orchestrator import SimulationOrchestrator
from .schemas import (
    ExternalAPIBanksResponse,
    ExternalAPIVehicleResponse,
    HealthResponse,
    SimulationCreateResponse,
    SimulationRequest,
    SimulationStatusResponse,
)


API_VERSION = "1.3.0"
orchestrator = SimulationOrchestrator()

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


@app.get("/externa/bancos", response_model=ExternalAPIBanksResponse)
def get_banks_from_external_api() -> ExternalAPIBanksResponse:
    try:
        get_external_api_config()
    except ExternalAPIConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        data = list_banks()
    except ExternalAPIRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": str(exc), "details": exc.details},
        ) from exc

    return ExternalAPIBanksResponse(
        status="ok",
        data=data.get("data") if isinstance(data, dict) else data,
        message="Consulta realizada na API externa para bancos ativos.",
    )


@app.get("/externa/veiculos", response_model=ExternalAPIVehicleResponse)
def get_vehicles_from_external_api() -> ExternalAPIVehicleResponse:
    try:
        get_external_api_config()
    except ExternalAPIConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        data = list_vehicles()
    except ExternalAPIRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": str(exc), "details": exc.details},
        ) from exc

    return ExternalAPIVehicleResponse(
        status="ok",
        data=data.get("data") if isinstance(data, dict) else data,
        message="Consulta realizada na API externa para veiculos.",
    )


@app.get("/externa/veiculos/{placa}", response_model=ExternalAPIVehicleResponse)
def get_vehicle_from_external_api(placa: str) -> ExternalAPIVehicleResponse:
    try:
        get_external_api_config()
    except ExternalAPIConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    normalized_plate = "".join(ch for ch in placa.upper() if ch.isalnum())
    try:
        data = find_vehicle_by_plate(placa)
    except ExternalAPIRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": str(exc), "details": exc.details},
        ) from exc

    return ExternalAPIVehicleResponse(
        status="ok",
        plate=normalized_plate,
        data=data.get("data") if isinstance(data, dict) else data,
        message="Consulta realizada na API externa para a placa informada.",
    )


@app.post("/simulacoes", response_model=SimulationCreateResponse, status_code=202)
def create_simulation(payload: SimulationRequest) -> SimulationCreateResponse:
    if payload.itau is None and payload.c6bank is None:
        raise HTTPException(status_code=400, detail="Informe ao menos um banco para simular.")

    try:
        return orchestrator.create_job(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExternalAPIRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": str(exc), "details": exc.details},
        ) from exc


@app.get("/simulacoes/{job_id}", response_model=SimulationStatusResponse)
def get_simulation(job_id: str) -> SimulationStatusResponse:
    try:
        response = get_processing(job_id)
    except ExternalAPIRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": str(exc), "details": exc.details},
        ) from exc

    data = response["data"]
    return SimulationStatusResponse(**data)
