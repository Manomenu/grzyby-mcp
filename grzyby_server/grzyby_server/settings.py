import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# __file__ = grzyby_server/grzyby_server/settings.py, so .parent.parent is the project and one
# more is the solution root. That only holds for the editable install used in development;
# the image installs a wheel into site-packages, so it states the root outright.
PROJECT_ROOT = Path(__file__).parent.parent
SOLUTION_ROOT = Path(os.environ["GRZYBY_SOLUTION_ROOT"]) if "GRZYBY_SOLUTION_ROOT" in os.environ else PROJECT_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[SOLUTION_ROOT / ".env.base", SOLUTION_ROOT / ".env", PROJECT_ROOT / ".env.base", PROJECT_ROOT / ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"  # noqa: S104 — inside a container, the pod network is the boundary
    port: int = 6210

    # Browser origins allowed to call the API directly. Behind the vite proxy and nginx the
    # browser sees a single origin, so this only matters for a UI served from elsewhere.
    cors_origins: list[str] = ["http://localhost:3210"]

    # The default is the container `just db up` starts; compose and the cluster point this at
    # their own database.
    database_url: str = "postgresql://grzyby:grzyby@localhost:5443/grzyby"


settings = Settings()
