import uuid
from sqlalchemy import Column, DateTime, Enum, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.enums import SimulationStatus, BankCode


class Simulation(Base):
    __tablename__ = 'simulations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank = Column(Enum(BankCode, name='bank_code'), nullable=False)
    status = Column(Enum(SimulationStatus, name='simulation_status'), nullable=False)

    input_payload = Column(JSONB, nullable=False)
    idempotency_key = Column(String(64), nullable=True, index=True)

    correlation_id = Column(String(64), nullable=True, index=True)
    attempt_count = Column(Integer, nullable=False, default=0)

    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
