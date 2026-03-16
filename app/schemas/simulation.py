from __future__ import annotations

from typing import Annotated, Literal, Optional, Union, Any
from pydantic import BaseModel, Field

from app.models.enums import SimulationStatus, BankCode


class ItauInput(BaseModel):
    cpf: str
    placa_veiculo: str
    valor_financiamento: str
    retorno_estrelas: str


class C6BankInput(BaseModel):
    cpf: str
    celular: str
    data_nascimento: str
    uf: str
    placa_veiculo: str
    valor_financiamento: str
    valor_entrada: str
    possui_cnh: bool
    retorno_estrelas: str


class ItauSimulationRequest(BaseModel):
    bank: Literal[BankCode.ITAU]
    input: ItauInput
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None


class C6BankSimulationRequest(BaseModel):
    bank: Literal[BankCode.C6BANK]
    input: C6BankInput
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None


SimulationRequest = Annotated[
    Union[ItauSimulationRequest, C6BankSimulationRequest],
    Field(discriminator='bank'),
]


class SimulationCreateResponse(BaseModel):
    simulation_id: str
    status: SimulationStatus


class SimulationResultResponse(BaseModel):
    raw_result: Optional[dict[str, Any]] = None
    normalized_result: Optional[dict[str, Any]] = None


class SimulationDetailResponse(BaseModel):
    simulation_id: str
    bank: BankCode
    status: SimulationStatus
    input: dict[str, Any]
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    result: Optional[SimulationResultResponse] = None


class SimulationListResponse(BaseModel):
    items: list[SimulationDetailResponse]
    total: int
    limit: int
    offset: int
