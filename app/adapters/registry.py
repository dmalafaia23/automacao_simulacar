from __future__ import annotations

from typing import Dict

from app.adapters.base import BankSimulationExecutor
from app.adapters.c6bank import C6BankSimulationExecutor
from app.adapters.itau import ItauSimulationExecutor
from app.models.enums import BankCode


class ExecutorRegistry:
    def __init__(self) -> None:
        self._executors: Dict[BankCode, BankSimulationExecutor] = {
            BankCode.ITAU: ItauSimulationExecutor(),
            BankCode.C6BANK: C6BankSimulationExecutor(),
        }

    def get_executor(self, bank: BankCode) -> BankSimulationExecutor:
        if bank not in self._executors:
            raise ValueError(f'Unsupported bank: {bank}')
        return self._executors[bank]
