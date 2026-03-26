from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .env_loader import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class ExternalAPIConfigError(RuntimeError):
    pass


class ExternalAPIRequestError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 500, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


@dataclass(frozen=True)
class ExternalAPIConfig:
    base_url: str
    api_key: str


def get_external_api_config() -> ExternalAPIConfig:
    base_url = os.getenv("EXTERNAL_API_URL")
    api_key = os.getenv("EXTERNAL_API_KEY")

    if not base_url:
        raise ExternalAPIConfigError("EXTERNAL_API_URL não configurado.")
    if not api_key:
        raise ExternalAPIConfigError("EXTERNAL_API_KEY não configurado.")

    return ExternalAPIConfig(base_url=base_url.rstrip("/"), api_key=api_key)


def _parse_response_body(raw_body: bytes) -> Any:
    if not raw_body:
        return None
    try:
        return json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        return raw_body.decode("utf-8", errors="replace")


def external_api_post(payload: Dict[str, Any]) -> Any:
    config = get_external_api_config()
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        config.base_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": config.api_key,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return _parse_response_body(response.read())
    except HTTPError as exc:
        body = _parse_response_body(exc.read())
        message = "Erro ao consultar a API externa."
        if isinstance(body, dict) and body.get("error"):
            message = str(body["error"])
        raise ExternalAPIRequestError(
            message,
            status_code=exc.code,
            details=body if isinstance(body, dict) else {},
        ) from exc
    except URLError as exc:
        raise ExternalAPIRequestError(
            "Falha de conexão com a API externa.",
            status_code=503,
            details={"reason": str(exc.reason)},
        ) from exc


def list_banks() -> Any:
    return external_api_post({"action": "list_bancos"})


def list_vehicles() -> Any:
    return external_api_post({"action": "list_veiculos"})


def find_vehicle_by_plate(placa: str) -> Any:
    normalized_plate = "".join(ch for ch in placa.upper() if ch.isalnum())
    return external_api_post({"action": "list_veiculos", "placa": normalized_plate})


def create_processing(
    *,
    dados_requisicao: Dict[str, Any],
    bancos: list[str],
    simulacao_id: Optional[str] = None,
) -> Any:
    payload: Dict[str, Any] = {
        "action": "criar_processamento",
        "dados_requisicao": dados_requisicao,
        "bancos": bancos,
    }
    if simulacao_id is not None:
        payload["simulacao_id"] = simulacao_id
    return external_api_post(payload)


def get_processing(processamento_id: str) -> Any:
    return external_api_post({"action": "get_processamento", "id": processamento_id})


def update_processing(
    processamento_id: str,
    **fields: Any,
) -> Any:
    payload: Dict[str, Any] = {"action": "atualizar_processamento", "id": processamento_id}
    payload.update(fields)
    return external_api_post(payload)


def update_processing_bank(
    banco_processamento_id: str,
    **fields: Any,
) -> Any:
    payload: Dict[str, Any] = {"action": "atualizar_banco", "id": banco_processamento_id}
    payload.update(fields)
    return external_api_post(payload)


def insert_processing_offers(
    processamento_simulacao_banco_id: str,
    ofertas: list[Dict[str, Any]],
) -> Any:
    return external_api_post(
        {
            "action": "inserir_ofertas",
            "processamento_simulacao_banco_id": processamento_simulacao_banco_id,
            "ofertas": ofertas,
        }
    )


def parse_numero_decimal(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None

    match = re.search(r"-?\d[\d\.\,]*", text)
    if not match:
        return None

    number_text = match.group(0)
    if "." in number_text and "," in number_text:
        number_text = number_text.replace(".", "").replace(",", ".")
    elif "," in number_text:
        number_text = number_text.replace(",", ".")

    try:
        return float(number_text)
    except ValueError:
        return None


def parse_quantidade_parcelas(descricao_parcela: Optional[str]) -> Optional[int]:
    if descricao_parcela is None:
        return None
    match = re.search(r"(\d+)\s*x", descricao_parcela.lower())
    if not match:
        return None
    return int(match.group(1))


def normalize_offers(bank_name: str, simulation_rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    normalized: list[Dict[str, Any]] = []
    for index, row in enumerate(simulation_rows):
        descricao_parcela = str(row.get("parcela", "")).strip() or None
        taxa_texto = str(row.get("taxa", "")).strip() or None
        entrada_texto = str(row.get("entrada", "")).strip() or None
        valor_financiado_texto = str(row.get("financiado", "")).strip() or None
        normalized.append(
            {
                "nome_banco": bank_name,
                "quantidade_parcelas": parse_quantidade_parcelas(descricao_parcela),
                "descricao_parcela": descricao_parcela,
                "taxa": parse_numero_decimal(taxa_texto),
                "taxa_texto": taxa_texto,
                "entrada_valor": parse_numero_decimal(entrada_texto),
                "entrada_texto": entrada_texto,
                "valor_financiado": parse_numero_decimal(valor_financiado_texto),
                "valor_financiado_texto": valor_financiado_texto,
                "ordem_exibicao": index,
            }
        )
    return normalized
