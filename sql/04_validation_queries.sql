-- 1. Confirm raw and analytics row counts.
SELECT COUNT(*) AS raw_rows
FROM raw.service_requests;
 
SELECT COUNT(*) AS analytics_rows
FROM analytics.tickets;
 
-- 2. The analytics primary key should prevent duplicates.
SELECT ticket_id, COUNT(*) AS duplicate_count
FROM analytics.tickets
GROUP BY ticket_id
HAVING COUNT(*) > 1;
 
-- 3. Closed dates should never occur before created dates.
SELECT COUNT(*) AS invalid_lifecycle_rows
FROM analytics.tickets
WHERE closed_at < created_at;
 
-- 4. Review SLA distribution.
SELECT sla_status, COUNT(*) AS ticket_count
FROM analytics.tickets
GROUP BY sla_status
ORDER BY ticket_count DESC;
 
-- 5. Review backlog aging.
SELECT aging_bucket, COUNT(*) AS open_ticket_count
FROM analytics.tickets
WHERE is_open
GROUP BY aging_bucket
ORDER BY open_ticket_count DESC;
 
-- 6. Review the latest pipeline executions.
SELECT
    run_id,
    started_at,
    completed_at,
    status,
    date_from,
    date_to,
    rows_extracted,
    rows_loaded,
    quality_summary,
    error_message
FROM audit.pipeline_runs
ORDER BY started_at DESC
LIMIT 10;
 
-- 7. Validate reporting views.
SELECT *
FROM reporting.vw_agency_performance
ORDER BY total_tickets DESC
LIMIT 20;
 
SELECT *
FROM reporting.vw_current_backlog
ORDER BY open_age_hours DESC
LIMIT 20;