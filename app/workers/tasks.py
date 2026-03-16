from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.orm import Session

from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.db.session import SessionLocal
from app.models.enums import SimulationStatus
from app.services.simulation_service import SimulationService
from app.workers.celery_app import celery_app


settings = get_settings()
configure_logging(settings.log_level)


@celery_app.task(name='run_simulation')

def run_simulation(simulation_id: str) -> None:
    db: Session = SessionLocal()
    service = SimulationService(db)
    try:
        service.execute_simulation(simulation_id)
    except SoftTimeLimitExceeded:
        service.fail_simulation(simulation_id, SimulationStatus.TIMEOUT, 'Simulation timed out')
    except Exception as exc:
        service.fail_simulation(simulation_id, SimulationStatus.FAILED, str(exc))
    finally:
        db.close()
