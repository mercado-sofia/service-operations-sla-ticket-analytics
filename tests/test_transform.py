"""Unit tests for ticket transformation business rules."""
 
import pandas as pd
 
from src.transform import assign_aging_bucket, classify_sla, normalize_status
 
 
SNAPSHOT = pd.Timestamp("2025-02-01 00:00:00")
 
 
def test_closed_ticket_met_sla() -> None:
    result = classify_sla(
        due_at=pd.Timestamp("2025-01-10 12:00:00"),
        closed_at=pd.Timestamp("2025-01-10 10:00:00"),
        snapshot_at=SNAPSHOT,
    )
    assert result == "MET"
 
 
def test_closed_ticket_breached_sla() -> None:
    result = classify_sla(
        due_at=pd.Timestamp("2025-01-10 12:00:00"),
        closed_at=pd.Timestamp("2025-01-10 13:00:00"),
        snapshot_at=SNAPSHOT,
    )
    assert result == "BREACHED"
 
 
def test_open_ticket_is_overdue() -> None:
    result = classify_sla(
        due_at=pd.Timestamp("2025-01-20 00:00:00"),
        closed_at=None,
        snapshot_at=SNAPSHOT,
    )
    assert result == "OPEN_OVERDUE"
 
 
def test_missing_due_date_has_no_sla() -> None:
    result = classify_sla(
        due_at=None,
        closed_at=None,
        snapshot_at=SNAPSHOT,
    )
    assert result == "NO_SLA"
 
 
def test_status_normalization() -> None:
    assert normalize_status("Assigned") == "IN_PROGRESS"
    assert normalize_status("unexpected status") == "OTHER"
 
 
def test_aging_bucket_assignment() -> None:
    assert assign_aging_bucket(12, is_closed=False) == "0-1 day"
    assert assign_aging_bucket(96, is_closed=False) == "4-7 days"
    assert assign_aging_bucket(None, is_closed=True) == "Closed"
