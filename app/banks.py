from __future__ import annotations

from typing import Dict, List

from C6Bank.client_data_loader import ClientData as C6BankClientData
from C6Bank.config_loader import AppConfig as C6BankConfig
from C6Bank.simulator import Simulator as C6BankSimulator
from Itau.client_data_loader import ClientData as ItauClientData
from Itau.config_loader import AppConfig as ItauConfig
from Itau.simulator import Simulator as ItauSimulator
from PAN.client_data_loader import ClientData as PanClientData
from PAN.config_loader import AppConfig as PanConfig
from PAN.simulator import Simulator as PanSimulator
from Santander.client_data_loader import ClientData as SantanderClientData
from Santander.config_loader import AppConfig as SantanderConfig
from Santander.simulator import Simulator as SantanderSimulator

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


def run_pan(payload: SimulationRequest) -> List[Dict[str, str]]:
    if payload.pan is None or not payload.pan.enabled:
        return []
    config = PanConfig(**payload.pan.config.model_dump())
    client_data = PanClientData(**payload.pan.client_data.model_dump())
    return PanSimulator(config, client_data).run()


def run_santander(payload: SimulationRequest) -> List[Dict[str, str]]:
    if payload.santander is None or not payload.santander.enabled:
        return []
    config = SantanderConfig(**payload.santander.config.model_dump())
    client_data = SantanderClientData(**payload.santander.client_data.model_dump())
    return SantanderSimulator(config, client_data).run()
