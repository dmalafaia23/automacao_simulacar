from fastapi import FastAPI

from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.api.v1.routes import simulations, health


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)

app.include_router(health.router)
app.include_router(simulations.router, prefix=settings.api_v1_prefix)
