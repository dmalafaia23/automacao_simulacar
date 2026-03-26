from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


JobStatus = Literal[
    "pendente",
    "processando",
    "concluido",
    "concluido_com_erros",
    "erro",
]
BankStatus = Literal["pendente", "processando", "concluido", "erro"]


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


class OfertaProcessamentoResponse(BaseModel):
    id: str
    processamento_simulacao_banco_id: str
    nome_banco: str
    quantidade_parcelas: Optional[int] = None
    descricao_parcela: Optional[str] = None
    taxa: Optional[float] = None
    taxa_texto: Optional[str] = None
    entrada_valor: Optional[float] = None
    entrada_texto: Optional[str] = None
    valor_financiado: Optional[float] = None
    valor_financiado_texto: Optional[str] = None
    ordem_exibicao: int
    criado_em: datetime


class BancoProcessamentoResponse(BaseModel):
    id: str
    processamento_simulacao_id: str
    nome_banco: str
    status: BankStatus
    mensagem_erro: Optional[str] = None
    dados_entrada: Optional[Any] = None
    dados_retorno: Optional[Any] = None
    iniciado_em: Optional[datetime] = None
    finalizado_em: Optional[datetime] = None
    criado_em: datetime
    atualizado_em: datetime
    ofertas: List[OfertaProcessamentoResponse] = Field(default_factory=list)


class SimulationCreateResponse(BaseModel):
    id: str
    status: JobStatus
    quantidade_bancos: int
    bancos: List[Dict[str, Any]] = Field(default_factory=list)


class SimulationStatusResponse(BaseModel):
    id: str
    simulacao_id: Optional[str] = None
    status: JobStatus
    dados_requisicao: Optional[Any] = None
    quantidade_bancos: int
    quantidade_bancos_concluidos: int
    quantidade_bancos_com_erro: int
    iniciado_em: Optional[datetime] = None
    finalizado_em: Optional[datetime] = None
    criado_em: datetime
    atualizado_em: datetime
    bancos: List[BancoProcessamentoResponse] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    version: str
    current_time: datetime
    timezone: str


class ExternalAPIVehicleResponse(BaseModel):
    status: str
    plate: Optional[str] = None
    data: Optional[Any] = None
    message: Optional[str] = None


class ExternalAPIBanksResponse(BaseModel):
    status: str
    data: Optional[Any] = None
    message: Optional[str] = None
