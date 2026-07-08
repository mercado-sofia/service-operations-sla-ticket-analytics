"""Application settings loaded from environment variables."""
 
from __future__ import annotations
 
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
 
from dotenv import load_dotenv
from sqlalchemy import URL
 
 
load_dotenv()
 
 
API_FIELDS: tuple[str, ...] = (
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "agency_name",
    "complaint_type",
    "descriptor",
    "location_type",
    "incident_zip",
    "city",
    "borough",
    "status",
    "due_date",
    "resolution_description",
    "resolution_action_updated_date",
    "open_data_channel_type",
    "latitude",
    "longitude",
)
 
 
@dataclass(frozen=True)
class Settings:
    """Validated runtime settings for the pipeline."""
 
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    api_url: str
    socrata_app_token: str | None
    extract_start_date: date
    extract_end_date: date
    page_size: int
    request_timeout_seconds: int
    snapshot_timestamp: datetime
    raw_data_dir: Path
    sample_data_path: Path
    sample_size: int
 
    @property
    def database_url(self) -> URL:
        """Return a safe SQLAlchemy URL for PostgreSQL with psycopg 3."""
 
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )
 
 
def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value
 
 
def _parse_date(name: str) -> date:
    value = _required(name)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD format.") from exc
 
 
def _parse_positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
 
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return value
 
 
def get_settings() -> Settings:
    """Load, validate, and return project settings."""
 
    start_date = _parse_date("EXTRACT_START_DATE")
    end_date = _parse_date("EXTRACT_END_DATE")
 
    if end_date <= start_date:
        raise ValueError("EXTRACT_END_DATE must be later than EXTRACT_START_DATE.")
 
    snapshot_raw = os.getenv("SNAPSHOT_TIMESTAMP", "").strip()
    if snapshot_raw:
        try:
            snapshot_timestamp = datetime.fromisoformat(snapshot_raw)
        except ValueError as exc:
            raise ValueError(
                "SNAPSHOT_TIMESTAMP must use ISO format, for example "
                "2025-02-01T00:00:00."
            ) from exc
    else:
        snapshot_timestamp = datetime.combine(end_date, datetime.min.time())
 
    token = os.getenv("SOCRATA_APP_TOKEN", "").strip() or None
 
    return Settings(
        db_host=_required("DB_HOST"),
        db_port=_parse_positive_int("DB_PORT", 5432),
        db_name=_required("DB_NAME"),
        db_user=_required("DB_USER"),
        db_password=_required("DB_PASSWORD"),
        api_url=os.getenv(
            "API_URL",
            "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
        ).strip(),
        socrata_app_token=token,
        extract_start_date=start_date,
        extract_end_date=end_date,
        page_size=_parse_positive_int("PAGE_SIZE", 5000),
        request_timeout_seconds=_parse_positive_int(
            "REQUEST_TIMEOUT_SECONDS",
            60,
        ),
        snapshot_timestamp=snapshot_timestamp,
        raw_data_dir=Path(os.getenv("RAW_DATA_DIR", "data/raw").strip()),
        sample_data_path=Path(
            os.getenv(
                "SAMPLE_DATA_PATH",
                "data/sample/service_requests_sample.csv",
            ).strip()
        ),
        sample_size=_parse_positive_int("SAMPLE_SIZE", 200),
    )