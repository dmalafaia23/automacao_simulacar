from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .env_loader import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class APIBasicAuthConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class APIBasicAuthConfig:
    username: str
    password: str


security = HTTPBasic()


def get_basic_auth_config() -> APIBasicAuthConfig:
    username = os.getenv("API_BASIC_USERNAME")
    password = os.getenv("API_BASIC_PASSWORD")

    if not username:
        raise APIBasicAuthConfigError("API_BASIC_USERNAME nao configurado.")
    if not password:
        raise APIBasicAuthConfigError("API_BASIC_PASSWORD nao configurado.")

    return APIBasicAuthConfig(username=username, password=password)


def require_basic_auth(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    try:
        config = get_basic_auth_config()
    except APIBasicAuthConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    is_valid_username = secrets.compare_digest(credentials.username, config.username)
    is_valid_password = secrets.compare_digest(credentials.password, config.password)

    if is_valid_username and is_valid_password:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais invalidas.",
        headers={"WWW-Authenticate": "Basic"},
    )
