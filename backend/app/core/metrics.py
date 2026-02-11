from prometheus_client import Counter, Histogram, Info

# App info
app_info = Info("inferbox", "inferbox application info")
app_info.info({"version": "0.1.0", "environment": "production"})

# HTTP metrics (used by middleware)
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Business metrics
orders_created_total = Counter("orders_created_total", "Total orders created")
calculations_completed_total = Counter("calculations_completed_total", "Total calculations completed")
emails_processed_total = Counter("emails_processed_total", "Total emails processed", ["classification"])
pohoda_sync_total = Counter("pohoda_sync_total", "Total Pohoda sync operations", ["status"])
notifications_sent_total = Counter("notifications_sent_total", "Total notifications sent", ["type"])

# Pipeline metrics
pipeline_stage_duration = Histogram(
    "pipeline_stage_duration_seconds",
    "Pipeline stage duration",
    ["stage"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)
pipeline_stage_total = Counter(
    "pipeline_stage_total",
    "Pipeline stages processed",
    ["stage", "status"],
)
pipeline_emails_total = Counter(
    "pipeline_emails_total",
    "Emails entering pipeline",
    ["classification"],
)
claude_tokens_used = Counter(
    "claude_tokens_used_total",
    "Claude API tokens consumed",
    ["task"],
)
claude_api_calls = Counter(
    "claude_api_calls_total",
    "Claude API calls",
    ["task", "status"],
)
dlq_entries_total = Counter(
    "dlq_entries_total",
    "Dead letter queue entries",
    ["stage"],
)
