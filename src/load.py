"""Load raw and transformed ticket data into PostgreSQL."""
 
from __future__ import annotations
 
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID
 
import pandas as pd
from sqlalchemy import Engine, MetaData, Table, text
from sqlalchemy.dialects.postgresql import UUID, insert
 
from src.config import API_FIELDS, Settings
 
 
RAW_COLUMNS: tuple[str, ...] = API_FIELDS + ("run_id", "ingested_at")
 
 
def _chunked(records: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    """Yield fixed-size slices for database writes."""
 
    for start in range(0, len(records), size):
        yield records[start : start + size]
 
 
def start_pipeline_run(
    engine: Engine,
    run_id: UUID,
    settings: Settings,
) -> None:
    """Insert a RUNNING audit record."""
 
    statement = text(
        """
        INSERT INTO audit.pipeline_runs (
            run_id,
            started_at,
            status,
            date_from,
            date_to
        )
        VALUES (
            :run_id,
            :started_at,
            'RUNNING',
            :date_from,
            :date_to
        )
        """
    )
 
    with engine.begin() as connection:
        connection.execute(
            statement,
            {
                "run_id": run_id,
                "started_at": datetime.now(),
                "date_from": settings.extract_start_date,
                "date_to": settings.extract_end_date,
            },
        )
  
def finish_pipeline_run(
    engine: Engine,
    run_id: UUID,
    status: str,
    rows_extracted: int = 0,
    rows_loaded: int = 0,
    quality_summary: dict[str, int] | None = None,
    raw_file_path: Path | None = None,
    error_message: str | None = None,
) -> None:
    """Complete an audit record after success or failure."""
 
    statement = text(
        """
        UPDATE audit.pipeline_runs
        SET completed_at = :completed_at,
            status = :status,
            rows_extracted = :rows_extracted,
            rows_loaded = :rows_loaded,
            quality_summary = CAST(:quality_summary AS JSONB),
            raw_file_path = :raw_file_path,
            error_message = :error_message
        WHERE run_id = :run_id
        """
    )
 
    with engine.begin() as connection:
        connection.execute(
            statement,
            {
                "run_id": run_id,
                "completed_at": datetime.now(),
                "status": status,
                "rows_extracted": rows_extracted,
                "rows_loaded": rows_loaded,
                "quality_summary": json.dumps(quality_summary or {}),
                "raw_file_path": str(raw_file_path) if raw_file_path else None,
                "error_message": error_message,
            },
        )
 
 
def load_raw_service_requests(
    engine: Engine,
    raw_dataframe: pd.DataFrame,
    run_id: UUID,
) -> int:
    """Append the source values to the raw schema."""

    if raw_dataframe.empty:
        return 0

    dataframe = raw_dataframe.copy()

    # Keep run_id as an actual UUID object.
    dataframe["run_id"] = run_id
    dataframe["ingested_at"] = datetime.now()

    dataframe = dataframe.loc[:, list(RAW_COLUMNS)]

    dataframe.to_sql(
        name="service_requests",
        con=engine,
        schema="raw",
        if_exists="append",
        index=False,
        chunksize=1000,
        method=None,
        dtype={
            "run_id": UUID(as_uuid=True),
        },
    )

    return len(dataframe)
 
 
def upsert_analytics_tickets(
    engine: Engine,
    clean_dataframe: pd.DataFrame,
    run_id: UUID,
    chunk_size: int = 1000,
) -> int:
    """Insert new tickets and update existing tickets by ticket_id."""
 
    if clean_dataframe.empty:
        return 0
 
    dataframe = clean_dataframe.copy()
    dataframe["source_run_id"] = run_id
    dataframe["updated_at"] = datetime.now()
 
    # Convert pandas missing values into Python None for psycopg.
    dataframe = dataframe.astype(object).where(pd.notna(dataframe), None)
    records = dataframe.to_dict(orient="records")
 
    metadata = MetaData()
    tickets_table = Table(
        "tickets",
        metadata,
        schema="analytics",
        autoload_with=engine,
    )
 
    base_insert = insert(tickets_table)
    update_columns = {
        column.name: getattr(base_insert.excluded, column.name)
        for column in tickets_table.columns
        if column.name != "ticket_id"
    }
 
    with engine.begin() as connection:
        for batch in _chunked(records, chunk_size):
            statement = base_insert.values(batch)
            statement = statement.on_conflict_do_update(
                index_elements=[tickets_table.c.ticket_id],
                set_=update_columns,
            )
            connection.execute(statement)
 
    return len(records)
 
 
def save_public_sample(
    clean_dataframe: pd.DataFrame,
    settings: Settings,
) -> Path:
    """Save a small recruiter-friendly sample without detailed descriptions."""
 
    public_columns = [
        "ticket_id",
        "created_at",
        "closed_at",
        "agency_code",
        "agency_name",
        "complaint_type",
        "borough",
        "normalized_status",
        "submission_channel",
        "resolution_hours",
        "open_age_hours",
        "aging_bucket",
        "sla_status",
    ]
 
    settings.sample_data_path.parent.mkdir(parents=True, exist_ok=True)
    sample = clean_dataframe.loc[:, public_columns].head(settings.sample_size)
    sample.to_csv(settings.sample_data_path, index=False)
    return settings.sample_data_path
