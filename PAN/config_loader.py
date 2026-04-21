import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class AppConfig:
    base_url: str
    email: str
    senha: str
    headless: bool = True
    timeout_ms: int = 30000


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    data: Dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8-sig"))
    return AppConfig(
        base_url=str(data.get("base_url", "")),
        email=str(data.get("email", "")),
        senha=str(data.get("senha", "")),
        headless=bool(data.get("headless", True)),
        timeout_ms=int(data.get("timeout_ms", 30000)),
    )
