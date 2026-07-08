"""End-to-end orchestration for the service operations pipeline."""

from __future__ import annotations

from uuid import uuid4

from src.config import get_settings
from src.database import get_engine, test_connection
from src.extract import (
    extract_service_requests,
    records_to_dataframe,
    save_raw_jsonl,
)
from src.load import (
    finish_pipeline_run,
    load_raw_service_requests,
    save_public_sample,
    start_pipeline_run,
    upsert_analytics_tickets,
)
from src.transform import transform_service_requests


def run_pipeline() -> None:
    """Run extraction, transformation, validation, and loading."""

    settings = get_settings()
    engine = get_engine(settings)
    test_connection(engine)

    run_id = uuid4()
    rows_extracted = 0
    rows_loaded = 0
    quality_summary: dict[str, int] = {}
    raw_file_path = None

    start_pipeline_run(engine, run_id, settings)

    try:
        print(f"Starting pipeline run {run_id}")
        print(
            "Extraction window: "
            f"{settings.extract_start_date} to "
            f"{settings.extract_end_date} (end exclusive)"
        )

        records = extract_service_requests(settings)
        rows_extracted = len(records)

        raw_file_path = save_raw_jsonl(records, settings, str(run_id))
        raw_dataframe = records_to_dataframe(records)
        load_raw_service_requests(engine, raw_dataframe, run_id)

        clean_dataframe, quality_summary = transform_service_requests(
            raw_dataframe,
            settings.snapshot_timestamp,
        )

        rows_loaded = upsert_analytics_tickets(
            engine,
            clean_dataframe,
            run_id,
        )
        sample_path = save_public_sample(clean_dataframe, settings)

        finish_pipeline_run(
            engine=engine,
            run_id=run_id,
            status="SUCCESS",
            rows_extracted=rows_extracted,
            rows_loaded=rows_loaded,
            quality_summary=quality_summary,
            raw_file_path=raw_file_path,
        )

        print("Pipeline completed successfully.")
        print(f"Rows extracted: {rows_extracted:,}")
        print(f"Rows loaded/upserted: {rows_loaded:,}")
        print(f"Raw file: {raw_file_path}")
        print(f"Public sample: {sample_path}")
        print(f"Quality summary: {quality_summary}")

    except Exception as error:
        finish_pipeline_run(
            engine=engine,
            run_id=run_id,
            status="FAILED",
            rows_extracted=rows_extracted,
            rows_loaded=rows_loaded,
            quality_summary=quality_summary,
            raw_file_path=raw_file_path,
            error_message=str(error)[:4000],
        )
        print(f"Pipeline failed: {error}")
        raise
