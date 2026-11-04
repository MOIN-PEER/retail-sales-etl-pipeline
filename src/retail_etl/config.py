"""Central configuration, read from environment variables (or a local .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _path(env_name: str, default: str) -> Path:
    value = Path(os.getenv(env_name, default))
    return value if value.is_absolute() else PROJECT_ROOT / value


@dataclass(frozen=True)
class Settings:
    """All tunable settings for a pipeline run."""

    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", f"sqlite:///{(PROJECT_ROOT / 'data' / 'warehouse.db').as_posix()}"
        )
    )
    raw_dir: Path = field(default_factory=lambda: _path("RAW_DATA_DIR", "data/raw"))
    processed_dir: Path = field(default_factory=lambda: _path("PROCESSED_DATA_DIR", "data/processed"))
    output_dir: Path = field(default_factory=lambda: _path("OUTPUT_DIR", "outputs"))
    log_dir: Path = field(default_factory=lambda: _path("LOG_DIR", "logs"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "3")))
    retry_backoff_seconds: float = field(
        default_factory=lambda: float(os.getenv("RETRY_BACKOFF_SECONDS", "1.0"))
    )
    # A batch fails the run if more than this share of sales rows is rejected.
    max_reject_rate: float = field(default_factory=lambda: float(os.getenv("MAX_REJECT_RATE", "0.10")))

    def ensure_dirs(self) -> None:
        for directory in (
            self.raw_dir,
            self.processed_dir,
            self.output_dir / "charts",
            self.output_dir / "reports",
            self.output_dir / "tables",
            self.log_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
