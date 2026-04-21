import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class ClientData:
    cpf: str
    celular: str
    data_nascimento: str
    uf: str
    placa_veiculo: str
    valor_financiamento: str
    valor_entrada: str
    possui_cnh: bool
    retorno_estrelas: str


def load_client_data(path: str | Path) -> ClientData:
    data_path = Path(path)
    data: Dict[str, Any] = json.loads(data_path.read_text(encoding="utf-8-sig"))
    return ClientData(
        cpf=str(data.get("cpf", "")),
        celular=str(data.get("celular", "")),
        data_nascimento=str(data.get("data_nascimento", "")),
        uf=str(data.get("uf", "")),
        placa_veiculo=str(data.get("placa_veiculo", "")),
        valor_financiamento=str(data.get("valor_financiamento", "")),
        valor_entrada=str(data.get("valor_entrada", "")),
        possui_cnh=bool(data.get("possui_cnh", True)),
        retorno_estrelas=str(data.get("retorno_estrelas", "")),
    )
