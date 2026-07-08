CREATE TABLE IF NOT EXISTS raw.service_requests (
    raw_id BIGSERIAL PRIMARY KEY,
    unique_key TEXT,
    created_date TEXT,
    closed_date TEXT,
    agency TEXT,
    agency_name TEXT,
    complaint_type TEXT,
    descriptor TEXT,
    location_type TEXT,
    incident_zip TEXT,
    city TEXT,
    borough TEXT,
    status TEXT,
    due_date TEXT,
    resolution_description TEXT,
    resolution_action_updated_date TEXT,
    open_data_channel_type TEXT,
    latitude TEXT,
    longitude TEXT,
    run_id UUID NOT NULL,
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
 
CREATE INDEX IF NOT EXISTS idx_raw_service_requests_run_id
    ON raw.service_requests (run_id);
 
CREATE INDEX IF NOT EXISTS idx_raw_service_requests_unique_key
    ON raw.service_requests (unique_key);
 
CREATE TABLE IF NOT EXISTS analytics.tickets (
    ticket_id BIGINT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    due_at TIMESTAMP,
    resolution_updated_at TIMESTAMP,
    agency_code VARCHAR(50),
    agency_name TEXT,
    complaint_type TEXT,
    descriptor TEXT,
    location_type TEXT,
    incident_zip VARCHAR(20),
    city TEXT,
    borough VARCHAR(50),
    source_status TEXT,
    normalized_status VARCHAR(30) NOT NULL,
    submission_channel VARCHAR(50),
    resolution_description TEXT,
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    resolution_hours NUMERIC(14, 2),
    open_age_hours NUMERIC(14, 2),
    aging_bucket VARCHAR(30) NOT NULL,
    sla_status VARCHAR(30) NOT NULL,
    is_open BOOLEAN NOT NULL,
    is_closed BOOLEAN NOT NULL,
    snapshot_at TIMESTAMP NOT NULL,
    source_run_id UUID NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_ticket_state CHECK (is_open <> is_closed),
    CONSTRAINT chk_resolution_hours_nonnegative
        CHECK (resolution_hours IS NULL OR resolution_hours >= 0),
    CONSTRAINT chk_open_age_hours_nonnegative
        CHECK (open_age_hours IS NULL OR open_age_hours >= 0)
);
 
CREATE INDEX IF NOT EXISTS idx_tickets_created_at
    ON analytics.tickets (created_at);
 
CREATE INDEX IF NOT EXISTS idx_tickets_agency_name
    ON analytics.tickets (agency_name);
 
CREATE INDEX IF NOT EXISTS idx_tickets_complaint_type
    ON analytics.tickets (complaint_type);
 
CREATE INDEX IF NOT EXISTS idx_tickets_sla_status
    ON analytics.tickets (sla_status);
 
CREATE INDEX IF NOT EXISTS idx_tickets_is_open
    ON analytics.tickets (is_open);
 
CREATE TABLE IF NOT EXISTS audit.pipeline_runs (
    run_id UUID PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    rows_extracted INTEGER NOT NULL DEFAULT 0,
    rows_loaded INTEGER NOT NULL DEFAULT 0,
    quality_summary JSONB,
    raw_file_path TEXT,
    error_message TEXT,
    CONSTRAINT chk_pipeline_status
        CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED'))
);