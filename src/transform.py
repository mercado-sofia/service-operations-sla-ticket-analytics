"""Clean ticket records and calculate operational metrics."""
 
from __future__ import annotations
 
from datetime import datetime
from typing import Any
 
import pandas as pd
 
 
STATUS_MAPPING: dict[str, str] = {
    "closed": "CLOSED",
    "open": "OPEN",
    "assigned": "IN_PROGRESS",
    "started": "IN_PROGRESS",
    "in progress": "IN_PROGRESS",
    "pending": "PENDING",
}
 
 
SOURCE_TO_ANALYTICS_COLUMNS: dict[str, str] = {
    "unique_key": "ticket_id",
    "created_date": "created_at",
    "closed_date": "closed_at",
    "due_date": "due_at",
    "resolution_action_updated_date": "resolution_updated_at",
    "agency": "agency_code",
    "open_data_channel_type": "submission_channel",
    "status": "source_status",
}
 
 
ANALYTICS_COLUMNS: tuple[str, ...] = (
    "ticket_id",
    "created_at",
    "closed_at",
    "due_at",
    "resolution_updated_at",
    "agency_code",
    "agency_name",
    "complaint_type",
    "descriptor",
    "location_type",
    "incident_zip",
    "city",
    "borough",
    "source_status",
    "normalized_status",
    "submission_channel",
    "resolution_description",
    "latitude",
    "longitude",
    "resolution_hours",
    "open_age_hours",
    "aging_bucket",
    "sla_status",
    "is_open",
    "is_closed",
    "snapshot_at",
)
 
 
def normalize_status(value: Any) -> str:
    """Convert source-specific ticket statuses into a small standard set."""
 
    if value is None or pd.isna(value):
        return "OTHER"
 
    normalized_value = str(value).strip().casefold()
    return STATUS_MAPPING.get(normalized_value, "OTHER")
 
 
def classify_sla(
    due_at: pd.Timestamp | datetime | None,
    closed_at: pd.Timestamp | datetime | None,
    snapshot_at: pd.Timestamp | datetime,
) -> str:
    """Classify one ticket using its deadline and lifecycle state."""
 
    if due_at is None or pd.isna(due_at):
        return "NO_SLA"
 
    due_timestamp = pd.Timestamp(due_at)
    snapshot_timestamp = pd.Timestamp(snapshot_at)
 
    if closed_at is not None and not pd.isna(closed_at):
        closed_timestamp = pd.Timestamp(closed_at)
        return "MET" if closed_timestamp <= due_timestamp else "BREACHED"
 
    return "OPEN_OVERDUE" if snapshot_timestamp > due_timestamp else "OPEN_WITHIN_SLA"
 
 
def assign_aging_bucket(
    open_age_hours: float | int | None,
    is_closed: bool,
) -> str:
    """Assign an operational backlog aging group."""
 
    if is_closed:
        return "Closed"
 
    if open_age_hours is None or pd.isna(open_age_hours):
        return "Unknown"
 
    age_days = max(float(open_age_hours), 0.0) / 24
 
    if age_days <= 1:
        return "0-1 day"
    if age_days <= 3:
        return "2-3 days"
    if age_days <= 7:
        return "4-7 days"
    if age_days <= 14:
        return "8-14 days"
    if age_days <= 30:
        return "15-30 days"
    return "31+ days"
 
 
def _clean_text_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Trim strings and replace blank text with missing values."""
 
    text_columns = [
        "agency_code",
        "agency_name",
        "complaint_type",
        "descriptor",
        "location_type",
        "incident_zip",
        "city",
        "borough",
        "source_status",
        "submission_channel",
        "resolution_description",
    ]
 
    for column in text_columns:
        dataframe[column] = dataframe[column].astype("string").str.strip()
        dataframe[column] = dataframe[column].replace("", pd.NA)
    return dataframe
 
 
def transform_service_requests(
    raw_dataframe: pd.DataFrame,
    snapshot_at: datetime,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Transform source records and return clean tickets plus quality counts."""
 
    if raw_dataframe.empty:
        raise ValueError("Cannot transform an empty DataFrame.")
 
    dataframe = raw_dataframe.rename(columns=SOURCE_TO_ANALYTICS_COLUMNS).copy()
    rows_received = len(dataframe)
 
    # Ticket ID and timestamps
    dataframe["ticket_id"] = pd.to_numeric(
        dataframe["ticket_id"],
        errors="coerce",
    ).astype("Int64")
 
    date_columns = [
        "created_at",
        "closed_at",
        "due_at",
        "resolution_updated_at",
    ]
    for column in date_columns:
        dataframe[column] = pd.to_datetime(
            dataframe[column],
            errors="coerce",
        )
 
    missing_ticket_id = int(dataframe["ticket_id"].isna().sum())
    invalid_created_date = int(dataframe["created_at"].isna().sum())
 
    dataframe = dataframe.dropna(subset=["ticket_id", "created_at"]).copy()
    dataframe["ticket_id"] = dataframe["ticket_id"].astype("int64")
 
    # Keep the most recently updated version when duplicate ticket IDs appear.
    dataframe = dataframe.sort_values(
        by=["ticket_id", "resolution_updated_at", "created_at"],
        na_position="first",
    )
    duplicates_removed = int(dataframe.duplicated("ticket_id", keep="last").sum())
    dataframe = dataframe.drop_duplicates("ticket_id", keep="last").copy()
 
    invalid_lifecycle_mask = (
        dataframe["closed_at"].notna()
        & (dataframe["closed_at"] < dataframe["created_at"])
    )
    invalid_lifecycle = int(invalid_lifecycle_mask.sum())
    dataframe = dataframe.loc[~invalid_lifecycle_mask].copy()
 
    # A due date before creation cannot be trusted for SLA reporting.
    invalid_due_mask = (
        dataframe["due_at"].notna()
        & (dataframe["due_at"] < dataframe["created_at"])
    )
    invalid_due_dates = int(invalid_due_mask.sum())
    dataframe.loc[invalid_due_mask, "due_at"] = pd.NaT
 
    dataframe = _clean_text_columns(dataframe)
 
    dataframe["normalized_status"] = dataframe["source_status"].map(
        normalize_status
    )
    unknown_statuses = int((dataframe["normalized_status"] == "OTHER").sum())
    missing_due_dates = int(dataframe["due_at"].isna().sum())
 
    dataframe["latitude"] = pd.to_numeric(
        dataframe["latitude"],
        errors="coerce",
    )
    dataframe["longitude"] = pd.to_numeric(
        dataframe["longitude"],
        errors="coerce",
    )
 
    dataframe["is_closed"] = dataframe["closed_at"].notna()
    dataframe["is_open"] = ~dataframe["is_closed"]
 
    dataframe["resolution_hours"] = (
        dataframe["closed_at"] - dataframe["created_at"]
    ).dt.total_seconds() / 3600
 
    snapshot_timestamp = pd.Timestamp(snapshot_at)
    dataframe["open_age_hours"] = pd.NA
    open_mask = dataframe["is_open"]
    dataframe.loc[open_mask, "open_age_hours"] = (
        snapshot_timestamp - dataframe.loc[open_mask, "created_at"]
    ).dt.total_seconds() / 3600
    dataframe["open_age_hours"] = pd.to_numeric(
        dataframe["open_age_hours"],
        errors="coerce",
    ).clip(lower=0)
 
    dataframe["aging_bucket"] = dataframe.apply(
        lambda row: assign_aging_bucket(
            row["open_age_hours"],
            bool(row["is_closed"]),
        ),
        axis=1,
    )
 
    dataframe["sla_status"] = dataframe.apply(
        lambda row: classify_sla(
            row["due_at"],
            row["closed_at"],
            snapshot_timestamp,
        ),
        axis=1,
    )
 
    dataframe["snapshot_at"] = snapshot_timestamp
 
    clean_dataframe = dataframe.loc[:, list(ANALYTICS_COLUMNS)].copy()
 
    quality_summary = {
        "rows_received": rows_received,
        "missing_ticket_id": missing_ticket_id,
        "invalid_created_date": invalid_created_date,
        "duplicates_removed": duplicates_removed,
        "invalid_lifecycle": invalid_lifecycle,
        "invalid_due_dates": invalid_due_dates,
        "missing_due_dates": missing_due_dates,
        "unknown_statuses": unknown_statuses,
        "rows_output": len(clean_dataframe),
    }
 
    return clean_dataframe, quality_summary
