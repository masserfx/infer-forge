# inferbox Monitoring Stack

## Komponenty

### Prometheus (Port 9090)
Centrální metriky server, sbírá data z:
- Backend FastAPI (`/metrics`)
- PostgreSQL exporter (port 9187)
- Redis exporter (port 9121)
- Flower Celery monitoring (port 5555)

**Přístup (prod):** `http://localhost:9090`

### Grafana (Port 3002)
Vizualizace metrik, dashboardy:
- inferbox Dashboard: 13 panelů (HTTP, Celery, DB, Redis, System)
- Auto-provisioned z `/docker/grafana/dashboards/infer-forge.json`

**Přístup (prod):** `http://localhost:3002`
**Credentials:** `${GRAFANA_ADMIN_USER}:${GRAFANA_ADMIN_PASSWORD}` (.env)

### Flower (Port 5555)
Real-time monitoring Celery tasků a workerů.

**Přístup (dev):** `http://localhost:5555`
**Přístup (prod):** `http://localhost:5555` (pouze localhost)
**Credentials:** `${FLOWER_USER}:${FLOWER_PASSWORD}` (.env)

### Alertmanager (Port 9093)
Řízení alertů z Prometheus, notifikace na email.

**Přístup (prod):** `http://localhost:9093`
**Config:** `/docker/alertmanager/alertmanager.yml`

### Exporters
- **postgres-exporter** (9187): PostgreSQL metriky (connections, queries, locks)
- **redis-exporter** (9121): Redis metriky (memory, commands, keys)

## Alert Rules

Definovány v `/docker/prometheus/alert-rules.yml`:

### Critical (repeat každou 1h)
- **BackendDown**: Backend nedostupný 3+ min
- **CeleryWorkerDown**: Flower down 5+ min
- **DatabaseDown**: PostgreSQL down 2+ min
- **RedisDown**: Redis down 2+ min
- **HighErrorRate**: >5% HTTP 5xx errorů za 5 min

### Warning (repeat každé 4h)
- **CeleryQueueBacklog**: >100 tasků ve frontě 10+ min
- **DiskUsageHigh**: >85% disk usage 10+ min
- **RedisMemoryHigh**: >80% Redis memory 5+ min
- **PostgresConnectionsHigh**: >80 DB connections 5+ min
- **HighResponseTime**: P95 >2s po dobu 5+ min

## Notifikace

Email notifikace konfigurované v `alertmanager.yml`:
- **Příjemce:** admin@infer.cz
- **Odesílatel:** alertmanager@infer.cz
- **SMTP:** smtp.infer.cz:587 (TLS)
- **Credentials:** Musí být nastavené v alertmanager config (template proměnná)

**Inhibit rules:** Critical alerts potlačí warning alerts se stejným jménem.

## Spuštění

### Development
```bash
docker compose up -d
# Flower dostupná na http://localhost:5555
```

### Production
```bash
docker compose -f docker-compose.prod.yml up -d
# Všechny monitoring služby běží, bind pouze na localhost
```

## Environment Variables

Do `.env` přidat:

```bash
# Flower
FLOWER_USER=admin
FLOWER_PASSWORD=<strong-password>
FLOWER_PORT=5555

# Grafana (už existuje)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<strong-password>

# Alertmanager email credentials
# (musí být manuálně vložené do alertmanager.yml, protože Go template)
```

## Retention

- **Prometheus:** 15 dní (default)
- **Grafana:** neomezené (dashboardy, datasources)
- **Alertmanager:** 120h notifikace history

## Metriky

### Backend FastAPI
Viz `backend/app/core/metrics.py`:
- `http_requests_total{method,endpoint,status}`
- `http_request_duration_seconds{method,endpoint}` (histogram)
- `active_users_total`
- `celery_active_tasks`
- `orders_by_status{status}`
- `calculations_by_status{status}`
- `document_storage_bytes`
- `orchestration_pipeline_duration_seconds{stage}` (histogram)
- `orchestration_tasks_total{status}`

### PostgreSQL (via exporter)
- `pg_stat_activity_count`
- `pg_stat_database_*`
- `pg_locks_count`

### Redis (via exporter)
- `redis_memory_used_bytes`
- `redis_memory_max_bytes`
- `redis_commands_processed_total`
- `redis_connected_clients`

### Flower (Celery)
- Worker status, active tasks, task success/failure rates
- Měřeno přes UI, není Prometheus endpoint (ale Flower sám poskytuje `/metrics` v novějších verzích)

## Troubleshooting

### Alert rules se nenačítají
```bash
# Zkontroluj Prometheus logs
docker compose -f docker-compose.prod.yml logs prometheus

# Validuj syntax
docker run --rm -v $(pwd)/docker/prometheus/alert-rules.yml:/tmp/rules.yml prom/prometheus:latest promtool check rules /tmp/rules.yml
```

### Alertmanager neposílá emaily
- Zkontroluj SMTP credentials v `alertmanager.yml`
- Validuj config: `docker compose -f docker-compose.prod.yml exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml`

### Flower neukazuje workery
- Zkontroluj že Celery worker běží: `docker compose -f docker-compose.prod.yml ps celery-worker`
- Ověř Redis connection string v Flower env vars

### Prometheus nescrapeuje target
- Zkontroluj `/targets` v Prometheus UI
- Ověř Docker network connectivity: `docker compose -f docker-compose.prod.yml exec prometheus wget -O- http://backend:8000/metrics`

## Security Notes

- Všechny monitoring porty v produkci bind pouze na `127.0.0.1` (nedostupné zvnějšku)
- Flower má HTTP Basic Auth (FLOWER_USER/PASSWORD)
- Grafana má admin credentials (GF_SECURITY_ADMIN_*)
- Alertmanager nemá autentizaci (pouze localhost, případně přidat reverse proxy auth)

## ISO 9001 Compliance

- Všechny metriky jsou trasovatelné (timestamp, labels)
- Alerty jsou verzované (git-tracked alert-rules.yml)
- Grafana dashboardy jsou verzované (git-tracked JSON)
- Retention politika zajišťuje auditní trail 15 dní
