from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


JobStatus = Literal[
    "pending",
    "processing",
    "completed",
    "completed_with_errors",
    "failed",
]
BankStatus = Literal["pending", "processing", "completed", "failed"]


class ItauConfigPayload(BaseModel):
    base_url: str
    email: str
    senha: str
    headless: bool = True
    timeout_ms: int = 30000


class ItauClientPayload(BaseModel):
    cpf: str
    placa_veiculo: str
    valor_financiamento: str
    retorno_estrelas: str


class ItauSimulationPayload(BaseModel):
    enabled: bool = True
    config: ItauConfigPayload
    client_data: ItauClientPayload


class C6BankConfigPayload(BaseModel):
    base_url: str
    email: str
    senha: str
    headless: bool = True
    timeout_ms: int = 30000


class C6BankClientPayload(BaseModel):
    cpf: str
    celular: str
    data_nascimento: str
    uf: str
    placa_veiculo: str
    valor_financiamento: str
    valor_entrada: str
    possui_cnh: bool = True
    retorno_estrelas: str


class C6BankSimulationPayload(BaseModel):
    enabled: bool = True
    config: C6BankConfigPayload
    client_data: C6BankClientPayload


class SimulationRequest(BaseModel):
    itau: Optional[ItauSimulationPayload] = None
    c6bank: Optional[C6BankSimulationPayload] = None


class BankResultResponse(BaseModel):
    bank: str
    status: BankStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class SimulationCreateResponse(BaseModel):
    id: str
    status: JobStatus


class SimulationStatusResponse(BaseModel):
    id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    banks: Dict[str, BankResultResponse] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    version: str
    current_time: datetime
    timezone: str
