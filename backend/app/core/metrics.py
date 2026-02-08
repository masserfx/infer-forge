from prometheus_client import Counter, Histogram, Info

# App info
app_info = Info("infer_forge", "INFER FORGE application info")
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
