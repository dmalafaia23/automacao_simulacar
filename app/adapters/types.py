from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class SimulationExecutionResult:
    raw_result: Dict[str, Any]
    normalized_result: Dict[str, Any]
