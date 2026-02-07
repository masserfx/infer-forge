# Monitoring & Backup - INFER FORGE

Dokumentace pro monitorování a zálohování INFER FORGE platformy.

## Sentry Error Tracking

### Konfigurace

V `.env` souboru nastavte:

```env
SENTRY_DSN=https://your-key@o123456.ingest.sentry.io/789
ENVIRONMENT=production
```

Pokud `SENTRY_DSN` není nastaveno, Sentry se neaktivuje (vhodné pro development).

### Co Sentry zachytává

- Python výjimky (automaticky)
- FastAPI request chyby
- SQLAlchemy query chyby
- Async task selhání v Celery
- Performance metrics (10% vzorkování)
- Profiling (10% vzorkování)

### Manuální zachytávání

```python
import sentry_sdk

# Zachytit konkrétní chybu
try:
    # risky operation
except Exception as e:
    sentry_sdk.capture_exception(e)

# Přidat kontext
sentry_sdk.set_user({"id": user_id, "email": user_email})
sentry_sdk.set_tag("component", "pohoda-integration")
sentry_sdk.set_context("order", {"order_id": 123, "customer": "Infer"})
```

## Request Logging

Každý HTTP request je automaticky logován s:
- Metodou (GET, POST, PUT, DELETE)
- Cestou (URL path)
- Status kódem
- Dobou trvání v milisekundách

Příklad logu:
```
2026-02-07 14:32:15 INFO request method=POST path=/api/v1/orders status=201 duration=45.3ms
```

## Health Check Endpointy

### `/health` - Komplexní health check
Ověřuje DB i Redis. Vrací HTTP 200 pokud vše běží, HTTP 503 pokud je problém.

```bash
curl http://localhost:8000/health
```

Odpověď:
```json
{
  "status": "healthy",
  "services": [
    {"healthy": true, "service": "database", "latency_ms": 2.3},
    {"healthy": true, "service": "redis", "latency_ms": 1.1}
  ],
  "version": {"app": "INFER FORGE", "version": "0.1.0"}
}
```

### `/health/db` - Pouze databáze

```bash
curl http://localhost:8000/health/db
```

### `/health/redis` - Pouze Redis

```bash
curl http://localhost:8000/health/redis
```

## Prometheus Metrics (připraveno pro integraci)

Health check endpointy lze scrapovat pomocí Prometheus. Doporučená konfigurace:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'infer-forge'
    scrape_interval: 30s
    metrics_path: '/health'
    static_configs:
      - targets: ['backend:8000']
```

Pro produkci doporučujeme:
1. Exportovat custom metrics pomocí `prometheus-fastapi-instrumentator`
2. Nastavit alerting pravidla v Alertmanager
3. Vizualizovat v Grafana (dashboardy pro FastAPI + PostgreSQL + Redis)

## Database Backup

### Manuální záloha

```bash
# Export proměnných
export POSTGRES_HOST=localhost
export POSTGRES_USER=infer
export POSTGRES_PASSWORD=infer
export POSTGRES_DB=infer_forge
export BACKUP_DIR=/backups
export RETENTION_DAYS=30

# Spustit backup
./scripts/backup_db.sh
```

Výstup:
```
Starting backup: /backups/infer_forge_20260207_143215.sql.gz
Backup complete: 2.3M
Removing backups older than 30 days...
Done. Remaining backups:
  infer_forge_20260207_143215.sql.gz (2.3M)
  infer_forge_20260206_020000.sql.gz (2.1M)
```

### Automatizace přes Cron

V produkčním prostředí nastavte cron job na serveru:

```bash
# Denní backup v 2:00
0 2 * * * /path/to/infer-forge/scripts/backup_db.sh >> /var/log/infer-backup.log 2>&1
```

Nebo přes Docker Compose jako sidecar kontejner:

```yaml
services:
  backup:
    image: postgres:16-alpine
    environment:
      - POSTGRES_HOST=db
      - POSTGRES_USER=infer
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=infer_forge
      - BACKUP_DIR=/backups
      - RETENTION_DAYS=30
    volumes:
      - ./scripts/backup_db.sh:/backup.sh:ro
      - backup-data:/backups
    entrypoint: /bin/sh -c "while true; do sleep 86400; /backup.sh; done"
    depends_on:
      - db

volumes:
  backup-data:
```

### Restore ze zálohy

```bash
# Rozbalit a obnovit databázi
gunzip < /backups/infer_forge_20260207_143215.sql.gz | \
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
  -h localhost \
  -U infer \
  -d infer_forge
```

**POZOR:** Restore přepíše existující data. Doporučujeme nejprve vytvořit novou databázi:

```bash
# Vytvořit novou DB pro test restore
createdb -h localhost -U infer infer_forge_restore

# Obnovit do ní
gunzip < backup.sql.gz | psql -h localhost -U infer -d infer_forge_restore

# Ověřit data
psql -h localhost -U infer -d infer_forge_restore -c "SELECT COUNT(*) FROM orders;"
```

## Bezpečnost

### Ochrana záložních souborů

1. Zálohy obsahují citlivá data zákazníků (dle ISO 9001 a GDPR)
2. Nastavte správná oprávnění na backup adresář:

```bash
chmod 700 /backups
chown infer:infer /backups
```

3. Šifrované zálohy (doporučeno pro off-site storage):

```bash
# Backup s AES-256 šifrováním
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
  -h localhost -U infer -d infer_forge \
  --no-owner --no-privileges \
  | gzip \
  | openssl enc -aes-256-cbc -salt -pbkdf2 -out backup_encrypted.sql.gz.enc

# Restore
openssl enc -aes-256-cbc -d -pbkdf2 -in backup_encrypted.sql.gz.enc \
  | gunzip \
  | psql -h localhost -U infer -d infer_forge
```

4. Off-site kopie doporučujeme ukládat na:
   - Lokální NAS ve firmě Infer
   - Šifrované USB disky v trezoru
   - NIKDY nepřenášet nešifrované zálohy přes internet

## Structured Logging

Backend používá `structlog` pro strukturované logy ve formátu JSON.

### Příklad logu

```json
{
  "timestamp": "2026-02-07T14:32:15.123Z",
  "level": "info",
  "event": "order_created",
  "order_id": 123,
  "customer_id": 456,
  "amount": 125000.0,
  "user_id": 1,
  "request_id": "abc-123-def"
}
```

### Integrace s ELK Stack

Pro pokročilý monitoring doporučujeme ELK (Elasticsearch, Logstash, Kibana):

1. **Filebeat** - sbírá logy z Docker kontejnerů
2. **Logstash** - parsuje a transformuje JSON logy
3. **Elasticsearch** - indexuje a ukládá logy
4. **Kibana** - vizualizace a alerting

## Rate Limiting

Health check endpointy nemají rate limiting. Pro produkční API endpointy doporučujeme:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/orders")
@limiter.limit("10/minute")
async def create_order(...):
    pass
```

## Checklist před nasazením do produkce

- [ ] Nastavit `SENTRY_DSN` v `.env`
- [ ] Nastavit `ENVIRONMENT=production`
- [ ] Nakonfigurovat denní database backupy (cron nebo Docker sidecar)
- [ ] Ověřit restore procesu na test databázi
- [ ] Nastavit oprávnění na `/backups` adresář (chmod 700)
- [ ] Připravit off-site backup storage (NAS, USB trezor)
- [ ] Nastavit Prometheus scraping pro `/health` endpoint
- [ ] Vytvořit Grafana dashboardy
- [ ] Nastavit alerting pro zdravotní kontroly (Alertmanager nebo PagerDuty)
- [ ] Otestovat Sentry error capturing v production prostředí
- [ ] Zkontrolovat logrotate nastavení pro application logy

## Podpora

Pro technické dotazy kontaktujte:
- **Backend:** ocel@infer-forge.ai
- **DevOps:** kontrola@infer-forge.ai
- **Architektura:** kovář@infer-forge.ai
