from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from .schemas import BankStatus, JobStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BankExecution:
    bank: str
    status: BankStatus = "pending"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


@dataclass
class SimulationJob:
    id: str
    payload: Dict[str, Any]
    status: JobStatus = "pending"
    created_at: datetime = field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    banks: Dict[str, BankExecution] = field(default_factory=dict)


class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, SimulationJob] = {}
        self._lock = Lock()

    def create_job(self, job_id: str, payload: Dict[str, Any], bank_names: List[str]) -> SimulationJob:
        with self._lock:
            job = SimulationJob(
                id=job_id,
                payload=payload,
                banks={name: BankExecution(bank=name) for name in bank_names},
            )
            self._jobs[job_id] = job
            return job

    def get_job(self, job_id: str) -> Optional[SimulationJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def mark_job_processing(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "processing"
            job.started_at = utcnow()

    def mark_job_finished(self, job_id: str, status: JobStatus) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = status
            job.finished_at = utcnow()

    def update_bank(
        self,
        job_id: str,
        bank_name: str,
        *,
        status: Optional[BankStatus] = None,
        result: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        started: bool = False,
        finished: bool = False,
    ) -> None:
        with self._lock:
            bank = self._jobs[job_id].banks[bank_name]
            if started and bank.started_at is None:
                bank.started_at = utcnow()
            if status is not None:
                bank.status = status
            if result is not None:
                bank.result = result
            if error is not None:
                bank.error = error
            if finished:
                bank.finished_at = utcnow()
