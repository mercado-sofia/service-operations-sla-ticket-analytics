"""Extract NYC 311 service requests through the Socrata API."""
 
from __future__ import annotations
 
import json
from datetime import datetime
from pathlib import Path
from typing import Any
 
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
 
from src.config import API_FIELDS, Settings
 
 
def _build_session(app_token: str | None) -> requests.Session:
    """Create an HTTP session with retry handling."""
 
    retry_policy = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
 
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry_policy))
    session.headers.update({"Accept": "application/json"})
 
    if app_token:
        session.headers.update({"X-App-Token": app_token})
 
    return session
 
 
def _build_query_params(
    settings: Settings,
    offset: int,
) -> dict[str, str | int]:
    """Build a deterministic, paginated SoQL request."""
 
    start = settings.extract_start_date.isoformat()
    end = settings.extract_end_date.isoformat()
 
    return {
        "$select": ",".join(API_FIELDS),
        "$where": (
            f"created_date >= '{start}T00:00:00.000' "
            f"AND created_date < '{end}T00:00:00.000'"
        ),
        "$order": "created_date ASC, unique_key ASC",
        "$limit": settings.page_size,
        "$offset": offset,
    }
 
 
def extract_service_requests(settings: Settings) -> list[dict[str, Any]]:
    """Download all records inside the configured extraction window."""
 
    session = _build_session(settings.socrata_app_token)
    all_records: list[dict[str, Any]] = []
    offset = 0
 
    while True:
        response = session.get(
            settings.api_url,
            params=_build_query_params(settings, offset),
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
 
        page: list[dict[str, Any]] = response.json()
        if not page:
            break
 
        all_records.extend(page)
        print(f"Extracted {len(all_records):,} records...")
 
        if len(page) < settings.page_size:
            break
 
        offset += settings.page_size
 
    if not all_records:
        raise RuntimeError(
            "The API returned no records. Check the date range, endpoint, "
            "and internet connection."
        )
 
    return all_records
 
 
def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert API records into a DataFrame with a stable column order."""
 
    dataframe = pd.DataFrame.from_records(records)
 
    for column in API_FIELDS:
        if column not in dataframe.columns:
            dataframe[column] = None
 
    return dataframe.loc[:, list(API_FIELDS)].copy()
 
 
def save_raw_jsonl(
    records: list[dict[str, Any]],
    settings: Settings,
    run_id: str,
) -> Path:
    """Save the untouched API response as newline-delimited JSON."""
 
    settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = settings.raw_data_dir / (
        f"service_requests_{settings.extract_start_date}_"
        f"{settings.extract_end_date}_{timestamp}_{run_id}.jsonl"
    )
 
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
 
    return output_path
