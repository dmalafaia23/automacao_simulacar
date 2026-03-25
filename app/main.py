from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, Header, HTTPException

from .orchestrator import SimulationOrchestrator
from .schemas import (
    HealthResponse,
    SimulationCreateResponse,
    SimulationRequest,
    SimulationStatusResponse,
    SupabaseBanksResponse,
    SupabaseVehicleResponse,
)
from .store import JobStore
from .supabase import (
    SupabaseConfigError,
    SupabaseRequestError,
    find_vehicle_by_plate,
    get_supabase_config,
    list_active_banks,
)


API_VERSION = "1.1.0"
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


@app.get("/supabase/veiculos/{placa}", response_model=SupabaseVehicleResponse)
def get_vehicle_from_supabase(
    placa: str,
    authorization: str | None = Header(default=None),
) -> SupabaseVehicleResponse:
    try:
        config = get_supabase_config()
    except SupabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    user_token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        user_token = authorization[7:].strip()

    if config.is_service_role:
        authorization_mode = "service_role"
    elif user_token:
        authorization_mode = "publishable_plus_user_jwt"
    else:
        authorization_mode = "publishable_only"

    try:
        data = find_vehicle_by_plate(placa, auth_token=user_token)
    except SupabaseRequestError as exc:
        message = str(exc)
        if not config.is_service_role and not user_token:
            message = (
                f"{message} A chave atual e publica e a tabela 'veiculos' usa RLS para "
                "usuarios autenticados. Sem SUPABASE_SERVICE_ROLE_KEY ou JWT de usuario, "
                "a consulta pode falhar."
            )
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "message": message,
                "supabase_key_mode": config.key_source,
                "authorization_mode": authorization_mode,
                "details": exc.details,
            },
        ) from exc

    return SupabaseVehicleResponse(
        status="ok",
        supabase_key_mode="service_role" if config.is_service_role else "publishable",
        authorization_mode=authorization_mode,
        plate="".join(ch for ch in placa.upper() if ch.isalnum()),
        data=data,
        message=(
            "Consulta realizada com JWT do usuario."
            if authorization_mode == "publishable_plus_user_jwt"
            else "Consulta realizada com a chave configurada no servidor."
        ),
    )


@app.get("/supabase/bancos", response_model=SupabaseBanksResponse)
def get_banks_from_supabase(
    authorization: str | None = Header(default=None),
) -> SupabaseBanksResponse:
    try:
        config = get_supabase_config()
    except SupabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    user_token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        user_token = authorization[7:].strip()

    if config.is_service_role:
        authorization_mode = "service_role"
    elif user_token:
        authorization_mode = "publishable_plus_user_jwt"
    else:
        authorization_mode = "publishable_only"

    try:
        data = list_active_banks(auth_token=user_token)
    except SupabaseRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "message": str(exc),
                "supabase_key_mode": config.key_source,
                "authorization_mode": authorization_mode,
                "details": exc.details,
            },
        ) from exc

    return SupabaseBanksResponse(
        status="ok",
        supabase_key_mode="service_role" if config.is_service_role else "publishable",
        authorization_mode=authorization_mode,
        data=data,
        message="Consulta realizada no Supabase para bancos ativos.",
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
