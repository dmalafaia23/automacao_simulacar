from __future__ import annotations

from app.adapters.base import BankSimulationExecutor
from app.adapters.types import SimulationExecutionResult


class C6BankSimulationExecutor(BankSimulationExecutor):
    def run(self, input_payload: dict) -> SimulationExecutionResult:
        # TODO: Integrate with real Playwright robot for C6 BANK here.
        raw = {
            'bank': 'c6bank',
            'approved': True,
            'score_stars': int(input_payload.get('retorno_estrelas', '0')),
            'simulation_value': input_payload.get('valor_financiamento'),
            'down_payment': input_payload.get('valor_entrada'),
            'installments': [
                {'count': 36, 'amount': 'R$ 3.950,00'},
                {'count': 48, 'amount': 'R$ 3.120,00'},
            ],
        }
        normalized = {
            'approved': raw['approved'],
            'bank': 'c6bank',
            'score_stars': raw['score_stars'],
            'simulation_value': raw['simulation_value'],
            'down_payment': raw['down_payment'],
            'installments': raw['installments'],
            'observations': 'Mocked response. Replace with real robot output.',
        }
        return SimulationExecutionResult(raw_result=raw, normalized_result=normalized)
