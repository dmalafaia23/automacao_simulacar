from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .env_loader import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class SupabaseConfigError(RuntimeError):
    pass


class SupabaseRequestError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 500, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    api_key: str
    key_source: str

    @property
    def is_service_role(self) -> bool:
        return self.key_source == "service_role"


def get_supabase_config() -> SupabaseConfig:
    url = (
        os.getenv("SUPABASE_URL")
        or os.getenv("VITE_SUPABASE_URL")
    )
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    publishable_key = (
        os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY")
    )

    if not url:
        raise SupabaseConfigError("SUPABASE_URL ou VITE_SUPABASE_URL não configurado.")

    if service_role_key:
        return SupabaseConfig(url=url.rstrip("/"), api_key=service_role_key, key_source="service_role")

    if publishable_key:
        return SupabaseConfig(url=url.rstrip("/"), api_key=publishable_key, key_source="publishable")

    raise SupabaseConfigError(
        "Nenhuma chave do Supabase configurada. Defina SUPABASE_SERVICE_ROLE_KEY "
        "ou SUPABASE_PUBLISHABLE_KEY/VITE_SUPABASE_PUBLISHABLE_KEY."
    )


def _parse_response_body(raw_body: bytes) -> Any:
    if not raw_body:
        return None
    try:
        return json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        return raw_body.decode("utf-8", errors="replace")


def rest_select(
    table: str,
    *,
    query_params: Dict[str, str],
    auth_token: Optional[str] = None,
) -> Any:
    config = get_supabase_config()
    encoded_query = urlencode(query_params)
    url = f"{config.url}/rest/v1/{table}?{encoded_query}"

    bearer_token = auth_token or config.api_key
    headers = {
        "apikey": config.api_key,
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json",
    }

    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=30) as response:
            return _parse_response_body(response.read())
    except HTTPError as exc:
        body = _parse_response_body(exc.read())
        message = "Erro ao consultar o Supabase."
        if isinstance(body, dict) and body.get("message"):
            message = str(body["message"])
        raise SupabaseRequestError(message, status_code=exc.code, details=body if isinstance(body, dict) else {}) from exc
    except URLError as exc:
        raise SupabaseRequestError(
            "Falha de conexão com o Supabase.",
            status_code=503,
            details={"reason": str(exc.reason)},
        ) from exc


def find_vehicle_by_plate(placa: str, *, auth_token: Optional[str] = None) -> Any:
    normalized_plate = "".join(ch for ch in placa.upper() if ch.isalnum())
    return rest_select(
        "veiculos",
        query_params={
            "select": "id,placa,marca,modelo,versao,ano_fabricacao,ano_modelo,uf_licenciamento,fipe_valor,status_consulta,created_at,updated_at",
            "placa": f"eq.{normalized_plate}",
            "limit": "1",
        },
        auth_token=auth_token,
    )


def list_active_banks(*, auth_token: Optional[str] = None) -> Any:
    return rest_select(
        "bancos",
        query_params={
            "select": "id,nome,codigo,tipo_integracao,ativo,created_at,updated_at",
            "ativo": "eq.true",
            "order": "nome.asc",
        },
        auth_token=auth_token,
    )
