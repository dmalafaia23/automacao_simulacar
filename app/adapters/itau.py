from __future__ import annotations

from app.adapters.base import BankSimulationExecutor
from app.adapters.types import SimulationExecutionResult


class ItauSimulationExecutor(BankSimulationExecutor):
    def run(self, input_payload: dict) -> SimulationExecutionResult:
        # TODO: Integrate with real Playwright robot for ITAU here.
        raw = {
            'bank': 'itau',
            'approved': True,
            'score_stars': int(input_payload.get('retorno_estrelas', '0')),
            'simulation_value': input_payload.get('valor_financiamento'),
            'installments': [
                {'count': 48, 'amount': 'R$ 3.250,00'},
                {'count': 60, 'amount': 'R$ 2.890,00'},
            ],
        }
        normalized = {
            'approved': raw['approved'],
            'bank': 'itau',
            'score_stars': raw['score_stars'],
            'simulation_value': raw['simulation_value'],
            'down_payment': None,
            'installments': raw['installments'],
            'observations': 'Mocked response. Replace with real robot output.',
        }
        return SimulationExecutionResult(raw_result=raw, normalized_result=normalized)
