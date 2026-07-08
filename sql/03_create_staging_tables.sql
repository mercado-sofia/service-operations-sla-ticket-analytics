CREATE TABLE staging.service_requests_clean (
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
    incident_zip VARCHAR(10),
    city TEXT,
    borough VARCHAR(50),

    source_status TEXT,
    normalized_status VARCHAR(30),
    submission_channel VARCHAR(50),
    resolution_description TEXT,
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),

    resolution_hours NUMERIC(12, 2),
    open_age_hours NUMERIC(12, 2),
    aging_bucket VARCHAR(30),
    sla_status VARCHAR(30),
    is_open BOOLEAN,
    is_closed BOOLEAN,
    is_sla_breached BOOLEAN,

    source_run_id UUID,
    transformed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);