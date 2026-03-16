import uuid
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.enums import SimulationStatus


class SimulationEvent(Base):
    __tablename__ = 'simulation_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False, index=True)
    status = Column(Enum(SimulationStatus, name='simulation_status'), nullable=False)
    message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
