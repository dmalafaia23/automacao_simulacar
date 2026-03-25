from __future__ import annotations

import json
import os
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
