from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.adapters.types import SimulationExecutionResult


class BankSimulationExecutor(ABC):
    @abstractmethod
    def run(self, input_payload: Dict[str, Any]) -> SimulationExecutionResult:
        """Run bank simulation with Playwright integration.

        Replace the mock implementation in concrete executors with real RPA logic.
        """
        raise NotImplementedError
