from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread
from typing import Callable, Dict, List, Tuple
from uuid import uuid4

from .banks import run_c6bank, run_itau
from .schemas import SimulationRequest
from .store import JobStore


BankRunner = Callable[[SimulationRequest], List[Dict[str, str]]]


class SimulationOrchestrator:
    def __init__(self, store: JobStore) -> None:
        self.store = store

    def create_job(self, payload: SimulationRequest) -> str:
        enabled_banks = self._enabled_banks(payload)
        if not enabled_banks:
            raise ValueError("No enabled banks were provided for processing.")
        job_id = str(uuid4())
        self.store.create_job(job_id, payload.model_dump(mode="json"), enabled_banks)
        worker = Thread(target=self._run_job, args=(job_id, payload), daemon=True)
        worker.start()
        return job_id

    def _enabled_banks(self, payload: SimulationRequest) -> List[str]:
        banks: List[str] = []
        if payload.itau and payload.itau.enabled:
            banks.append("itau")
        if payload.c6bank and payload.c6bank.enabled:
            banks.append("c6bank")
        return banks

    def _bank_runners(self, payload: SimulationRequest) -> List[Tuple[str, BankRunner]]:
        runners: List[Tuple[str, BankRunner]] = []
        if payload.itau and payload.itau.enabled:
            runners.append(("itau", run_itau))
        if payload.c6bank and payload.c6bank.enabled:
            runners.append(("c6bank", run_c6bank))
        return runners

    def _run_job(self, job_id: str, payload: SimulationRequest) -> None:
        runners = self._bank_runners(payload)
        if not runners:
            self.store.mark_job_finished(job_id, "failed")
            return

        self.store.mark_job_processing(job_id)
        has_errors = False
        with ThreadPoolExecutor(max_workers=len(runners)) as executor:
            future_map = {}
            for bank_name, runner in runners:
                self.store.update_bank(job_id, bank_name, status="processing", started=True)
                future = executor.submit(runner, payload)
                future_map[future] = bank_name

            for future in as_completed(future_map):
                bank_name = future_map[future]
                try:
                    result = future.result()
                    self.store.update_bank(
                        job_id,
                        bank_name,
                        status="completed",
                        result=result,
                        finished=True,
                    )
                except Exception as exc:
                    has_errors = True
                    self.store.update_bank(
                        job_id,
                        bank_name,
                        status="failed",
                        error=str(exc),
                        finished=True,
                    )

        final_status = "completed_with_errors" if has_errors else "completed"
        self.store.mark_job_finished(job_id, final_status)
