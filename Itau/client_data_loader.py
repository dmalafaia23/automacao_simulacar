import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class ClientData:
    cpf: str
    placa_veiculo: str
    valor_financiamento: str
    retorno_estrelas: str


def load_client_data(path: str | Path) -> ClientData:
    data_path = Path(path)
    data: Dict[str, Any] = json.loads(data_path.read_text(encoding="utf-8-sig"))
    return ClientData(
        cpf=str(data.get("cpf", "")),
        placa_veiculo=str(data.get("placa_veiculo", "")),
        valor_financiamento=str(data.get("valor_financiamento", "")),
        retorno_estrelas=str(data.get("retorno_estrelas", "")),
    )
