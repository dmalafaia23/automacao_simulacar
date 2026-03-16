from enum import Enum


class SimulationStatus(str, Enum):
    RECEIVED = 'RECEIVED'
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    TIMEOUT = 'TIMEOUT'
    CANCELLED = 'CANCELLED'


class BankCode(str, Enum):
    ITAU = 'itau'
    C6BANK = 'c6bank'
