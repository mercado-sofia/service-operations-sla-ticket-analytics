CREATE OR REPLACE VIEW reporting.vw_daily_ticket_flow AS
WITH created AS (
    SELECT
        created_at::date AS report_date,
        COUNT(*) AS tickets_created
    FROM analytics.tickets
    GROUP BY created_at::date
),
closed AS (
    SELECT
        closed_at::date AS report_date,
        COUNT(*) AS tickets_closed
    FROM analytics.tickets
    WHERE closed_at IS NOT NULL
    GROUP BY closed_at::date
)
SELECT
    COALESCE(created.report_date, closed.report_date) AS report_date,
    COALESCE(created.tickets_created, 0) AS tickets_created,
    COALESCE(closed.tickets_closed, 0) AS tickets_closed
FROM created
FULL OUTER JOIN closed
    ON created.report_date = closed.report_date;


-- ============================================================
-- 2. AGENCY PERFORMANCE
-- Summarizes ticket volume, resolution time, and SLA performance
-- for each agency.
-- ============================================================

CREATE OR REPLACE VIEW reporting.vw_agency_performance AS
SELECT
    COALESCE(agency_name, agency_code, 'Unknown') AS agency_name,

    COUNT(*) AS total_tickets,

    COUNT(*) FILTER (
        WHERE is_open IS TRUE
    ) AS open_tickets,

    COUNT(*) FILTER (
        WHERE is_closed IS TRUE
    ) AS closed_tickets,

    ROUND(
        AVG(resolution_hours) FILTER (
            WHERE is_closed IS TRUE
        ),
        2
    ) AS average_resolution_hours,

    COUNT(*) FILTER (
        WHERE sla_status = 'MET'
    ) AS sla_met,

    COUNT(*) FILTER (
        WHERE sla_status = 'BREACHED'
    ) AS sla_breached,

    COUNT(*) FILTER (
        WHERE sla_status = 'OPEN_OVERDUE'
    ) AS open_overdue,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sla_status = 'MET'
        )
        / NULLIF(
            COUNT(*) FILTER (
                WHERE sla_status IN ('MET', 'BREACHED')
            ),
            0
        ),
        2
    ) AS sla_compliance_rate

FROM analytics.tickets

GROUP BY
    COALESCE(agency_name, agency_code, 'Unknown');


-- ============================================================
-- 3. SLA PERFORMANCE
-- Groups tickets by agency, complaint type, and SLA status.
-- ============================================================

CREATE OR REPLACE VIEW reporting.vw_sla_performance AS
SELECT
    COALESCE(agency_name, agency_code, 'Unknown') AS agency_name,

    COALESCE(complaint_type, 'Unknown') AS complaint_type,

    COALESCE(sla_status, 'NO_SLA')::VARCHAR(30) AS sla_status,

    COUNT(*) AS ticket_count,

    ROUND(
        AVG(resolution_hours) FILTER (
            WHERE is_closed IS TRUE
        ),
        2
    ) AS average_resolution_hours

FROM analytics.tickets

GROUP BY
    COALESCE(agency_name, agency_code, 'Unknown'),
    COALESCE(complaint_type, 'Unknown'),
    COALESCE(sla_status, 'NO_SLA')::VARCHAR(30);


-- ============================================================
-- 4. CURRENT BACKLOG
-- Contains only unresolved tickets.
-- ============================================================

CREATE OR REPLACE VIEW reporting.vw_current_backlog AS
SELECT
    ticket_id,
    created_at,
    COALESCE(agency_name, agency_code, 'Unknown') AS agency_name,
    COALESCE(complaint_type, 'Unknown') AS complaint_type,
    COALESCE(borough, 'Unknown') AS borough,
    normalized_status,
    ROUND(open_age_hours, 2) AS open_age_hours,
    aging_bucket,
    due_at,
    sla_status,
    submission_channel
FROM analytics.tickets
WHERE is_open IS TRUE
  AND is_closed IS FALSE
  AND normalized_status <> 'CLOSED';