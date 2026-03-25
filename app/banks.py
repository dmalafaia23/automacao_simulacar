from __future__ import annotations

from typing import Dict, List

from C6Bank.client_data_loader import ClientData as C6BankClientData
from C6Bank.config_loader import AppConfig as C6BankConfig
from C6Bank.simulator import Simulator as C6BankSimulator
from Itau.client_data_loader import ClientData as ItauClientData
from Itau.config_loader import AppConfig as ItauConfig
from Itau.simulator import Simulator as ItauSimulator

from .schemas import SimulationRequest


def run_itau(payload: SimulationRequest) -> List[Dict[str, str]]:
    if payload.itau is None or not payload.itau.enabled:
        return []
    config = ItauConfig(**payload.itau.config.model_dump())
    client_data = ItauClientData(**payload.itau.client_data.model_dump())
    return ItauSimulator(config, client_data).run()


def run_c6bank(payload: SimulationRequest) -> List[Dict[str, str]]:
    if payload.c6bank is None or not payload.c6bank.enabled:
        return []
    config = C6BankConfig(**payload.c6bank.config.model_dump())
    client_data = C6BankClientData(**payload.c6bank.client_data.model_dump())
    return C6BankSimulator(config, client_data).run()
