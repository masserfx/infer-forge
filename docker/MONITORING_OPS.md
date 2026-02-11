# inferbox Monitoring Operations Guide

## Rychlé příkazy

### Spuštění monitoring stacku

```bash
# Development (všechny porty dostupné)
docker compose up -d flower

# Production (všechny monitoring služby)
docker compose -f docker-compose.prod.yml up -d prometheus grafana alertmanager flower postgres-exporter redis-exporter
```

### Health check všech služeb

```bash
./scripts/test-monitoring.sh
```

### Reštart jednotlivých služeb

```bash
docker compose -f docker-compose.prod.yml restart prometheus
docker compose -f docker-compose.prod.yml restart grafana
docker compose -f docker-compose.prod.yml restart alertmanager
docker compose -f docker-compose.prod.yml restart flower
```

### Logy služeb

```bash
# Real-time logs
docker compose -f docker-compose.prod.yml logs -f prometheus
docker compose -f docker-compose.prod.yml logs -f alertmanager
docker compose -f docker-compose.prod.yml logs -f flower

# Poslední 100 řádků
docker compose -f docker-compose.prod.yml logs --tail=100 grafana
```

## Prometheus Operace

### Reload konfigurace (bez restartu)

```bash
# Pošle SIGHUP signál
docker compose -f docker-compose.prod.yml exec prometheus kill -HUP 1

# Nebo přes HTTP API
curl -X POST http://localhost:9090/-/reload
```

### Validace config před restartem

```bash
docker run --rm \
  -v $(pwd)/docker/prometheus/prometheus.yml:/tmp/prometheus.yml \
  -v $(pwd)/docker/prometheus/alert-rules.yml:/etc/prometheus/alert-rules.yml \
  prom/prometheus:v2.50.0 \
  --config.file=/tmp/prometheus.yml
```

### Query metrik přes CLI

```bash
# Aktuální hodnota metriky
curl -s 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result'

# Časový rozsah (range query)
curl -s 'http://localhost:9090/api/v1/query_range?query=http_requests_total&start=2024-01-01T00:00:00Z&end=2024-01-01T01:00:00Z&step=5m' | jq '.data.result'

# Active alerts
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {name: .labels.alertname, state: .state}'
```

### Seznam všech metrik

```bash
curl -s http://localhost:9090/api/v1/label/__name__/values | jq '.data[]' | sort
```

### Debugging targets

```bash
# Seznam všech targets a jejich stavu
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, instance: .labels.instance, health: .health}'
```

## Alertmanager Operace

### Reload konfigurace

```bash
docker compose -f docker-compose.prod.yml exec alertmanager kill -HUP 1

# Nebo přes HTTP API
curl -X POST http://localhost:9093/-/reload
```

### Validace config

```bash
docker compose -f docker-compose.prod.yml exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
```

### Zobrazit aktivní alerty

```bash
curl -s http://localhost:9093/api/v2/alerts | jq '.[] | {name: .labels.alertname, severity: .labels.severity, state: .status.state, starts_at: .startsAt}'
```

### Silence alert (temporary mute)

```bash
# Vytvoř silence na 2 hodiny pro alertname="BackendDown"
curl -X POST http://localhost:9093/api/v2/silences -H "Content-Type: application/json" -d '{
  "matchers": [
    {
      "name": "alertname",
      "value": "BackendDown",
      "isRegex": false
    }
  ],
  "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'",
  "endsAt": "'$(date -u -v+2H +%Y-%m-%dT%H:%M:%S.000Z)'",
  "createdBy": "admin",
  "comment": "Plánovaná údržba"
}'
```

### Zobrazit všechny silences

```bash
curl -s http://localhost:9093/api/v2/silences | jq '.[] | {id: .id, matchers: .matchers, comment: .comment, endsAt: .endsAt}'
```

### Smazat silence

```bash
# Získej ID silence
SILENCE_ID=$(curl -s http://localhost:9093/api/v2/silences | jq -r '.[0].id')

# Smaž
curl -X DELETE http://localhost:9093/api/v2/silence/$SILENCE_ID
```

## Grafana Operace

### Přístup přes API

```bash
# Vytvořit API key (přes UI: Configuration → API Keys)
GRAFANA_API_KEY="<your-api-key>"

# List dashboards
curl -s -H "Authorization: Bearer $GRAFANA_API_KEY" http://localhost:3002/api/search | jq '.[] | {id: .id, title: .title, uri: .uri}'

# Export dashboard JSON
curl -s -H "Authorization: Bearer $GRAFANA_API_KEY" http://localhost:3002/api/dashboards/uid/inferbox | jq '.dashboard' > backup-dashboard.json

# Import dashboard
curl -X POST -H "Authorization: Bearer $GRAFANA_API_KEY" -H "Content-Type: application/json" \
  -d @backup-dashboard.json \
  http://localhost:3002/api/dashboards/db
```

### Reset admin password

```bash
docker compose -f docker-compose.prod.yml exec grafana grafana-cli admin reset-admin-password <new-password>
```

### Backup Grafana data

```bash
# Backup SQLite databáze (uživatelé, datasources, dashboards)
docker compose -f docker-compose.prod.yml exec grafana cp /var/lib/grafana/grafana.db /tmp/
docker compose -f docker-compose.prod.yml cp grafana:/tmp/grafana.db ./backup-grafana-$(date +%Y%m%d).db
```

## Flower Operace

### API přístup

```bash
FLOWER_USER=${FLOWER_USER:-admin}
FLOWER_PASSWORD=${FLOWER_PASSWORD:-admin123}

# List všech workerů
curl -s -u "$FLOWER_USER:$FLOWER_PASSWORD" http://localhost:5555/api/workers | jq

# Aktivní tasky
curl -s -u "$FLOWER_USER:$FLOWER_PASSWORD" http://localhost:5555/api/tasks | jq

# Worker pool stats
curl -s -u "$FLOWER_USER:$FLOWER_PASSWORD" http://localhost:5555/api/workers | jq 'to_entries[] | {worker: .key, active: .value.active, processed: .value.processed}'
```

### Shutdown worker přes Flower

```bash
# Shutdown worker (graceful)
curl -X POST -u "$FLOWER_USER:$FLOWER_PASSWORD" \
  http://localhost:5555/api/worker/shutdown/<worker-name>

# Pool restart
curl -X POST -u "$FLOWER_USER:$FLOWER_PASSWORD" \
  http://localhost:5555/api/worker/pool/restart/<worker-name>
```

## Exporters Debugging

### PostgreSQL Exporter

```bash
# Test metriky
curl -s http://localhost:9187/metrics | grep '^pg_'

# Sleduj DB connections
watch -n 5 'curl -s http://localhost:9187/metrics | grep pg_stat_activity_count'

# Ověř connection string
docker compose -f docker-compose.prod.yml logs postgres-exporter | grep -i error
```

### Redis Exporter

```bash
# Test metriky
curl -s http://localhost:9121/metrics | grep '^redis_'

# Sleduj memory usage
watch -n 5 'curl -s http://localhost:9121/metrics | grep redis_memory_used_bytes'

# Redis info
curl -s http://localhost:9121/metrics | grep redis_info
```

## Běžné problémy a řešení

### Alert "BackendDown" firing, ale backend běží

**Příčina:** Prometheus nemůže scrape-ovat backend metrics endpoint

**Řešení:**
```bash
# Zkontroluj backend metrics endpoint
curl http://localhost:8000/metrics

# Zkontroluj Docker network
docker compose -f docker-compose.prod.yml exec prometheus wget -O- http://backend:8000/metrics

# Restart Prometheus
docker compose -f docker-compose.prod.yml restart prometheus
```

### Flower neukazuje workery

**Příčina:** Celery worker není připojený, nebo Flower má špatný broker URL

**Řešení:**
```bash
# Zkontroluj Celery worker logs
docker compose -f docker-compose.prod.yml logs celery-worker | tail -50

# Zkontroluj Redis connection
docker compose -f docker-compose.prod.yml exec celery-worker redis-cli -h redis -a "$REDIS_PASSWORD" ping

# Restart Flower
docker compose -f docker-compose.prod.yml restart flower
```

### Grafana dashboard prázdný (no data)

**Příčina:** Prometheus datasource není správně nakonfigurovaný

**Řešení:**
```bash
# Zkontroluj datasource v Grafana
curl -s -H "Authorization: Bearer $GRAFANA_API_KEY" http://localhost:3002/api/datasources | jq

# Test Prometheus z Grafana containeru
docker compose -f docker-compose.prod.yml exec grafana wget -O- http://prometheus:9090/api/v1/query?query=up

# Re-provision datasource
docker compose -f docker-compose.prod.yml restart grafana
```

### Alert email notifications nechodí

**Příčina:** SMTP credentials nebo config error

**Řešení:**
```bash
# Zkontroluj Alertmanager logs
docker compose -f docker-compose.prod.yml logs alertmanager | grep -i email

# Test SMTP z Alertmanager containeru
docker compose -f docker-compose.prod.yml exec alertmanager nc -zv smtp.infer.cz 587

# Manuální test notification (webhook)
curl -X POST http://localhost:9093/api/v1/alerts -H "Content-Type: application/json" -d '[{
  "labels": {"alertname": "TestAlert", "severity": "warning"},
  "annotations": {"summary": "Test alert", "description": "Testing email notification"}
}]'
```

### Prometheus "too many open files"

**Příčina:** Nedostatečný limit file descriptors

**Řešení:**
```bash
# Zvýš ulimit v docker-compose.prod.yml
# Pod prometheus službu přidej:
#   ulimits:
#     nofile:
#       soft: 65536
#       hard: 65536

# Restart
docker compose -f docker-compose.prod.yml up -d prometheus
```

## Monitoring Best Practices

1. **Pravidelně kontroluj alerts** (alespoň 2x denně)
2. **Nastavuj silences při plánované údržbě** (ne disable alertu)
3. **Exportuj důležité dashboardy jako JSON** do gitu
4. **Backup Grafana DB** před velkými změnami
5. **Sleduj retention** — Prometheus default 15 dní
6. **Dokumentuj custom metriky** v kódu (komentář u `Counter()`, `Histogram()`)
7. **Alert thresholdy pravidelně review** (co je "high" se mění s traffikem)
8. **Test alerting** alespoň 1x měsíčně (trigger test alert)

## Production Checklist

Před nasazením do produkce ověřit:

- [ ] Všechny monitoring porty bind pouze na `127.0.0.1`
- [ ] Flower má silné credentials (`FLOWER_PASSWORD`)
- [ ] Grafana má silné admin heslo (`GRAFANA_ADMIN_PASSWORD`)
- [ ] Alertmanager SMTP credentials jsou validní
- [ ] Test email notification chodí na správný email
- [ ] Prometheus retention je nastaven (default 15d OK)
- [ ] Grafana datasource ukazuje na správný Prometheus
- [ ] Alert rules neobsahují typo (test s `promtool check rules`)
- [ ] Všechny exportery (postgres, redis) scraped correctly
- [ ] Backup script zahrnuje Grafana DB + Prometheus data
- [ ] Dokumentace obsahuje on-call postup pro kritické alerty

## Reference

- Prometheus Query Language (PromQL): https://prometheus.io/docs/prometheus/latest/querying/basics/
- Alertmanager Config: https://prometheus.io/docs/alerting/latest/configuration/
- Grafana Provisioning: https://grafana.com/docs/grafana/latest/administration/provisioning/
- Flower API: https://flower.readthedocs.io/en/latest/api.html
