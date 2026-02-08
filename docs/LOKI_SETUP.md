# Grafana Loki - Centralizovaná agregace logů

## Přehled

Loki + Promtail integrace pro INFER FORGE poskytuje centralizované ukládání a dotazování logů ze všech Docker kontejnerů.

## Komponenty

### Loki (port 3100)
- Log aggregation server
- Filesystem storage: `/loki` volume
- Retence logů: 30 dní
- TSDB schema v13

### Promtail (port 9080)
- Log collector agent
- Automaticky sbírá logy z Docker kontejnerů projektu `infer-forge`
- Přidává labely: `container`, `service`, `logstream`

### Grafana datasource
- Loki datasource přidán do Grafana provisioning
- Automaticky dostupný ve všech dashboardech
- Template variable: `${DS_LOKI}`

## Nové Grafana panely

Dashboard **INFER FORGE - Přehled** obsahuje novou sekci "Logs":

1. **Application Logs**
   - Všechny logy z backend a celery services
   - Query: `{service=~"backend|celery"} |= ""`

2. **Error Logs**
   - Pouze error logy (filtr na error/ERROR/exception/Exception)
   - Query: `{service=~"backend|celery"} |~ "error|ERROR|exception|Exception"`

## Spuštění

```bash
# Spustit celý stack včetně Loki
docker compose up -d

# Pouze Loki + Promtail
docker compose up -d loki promtail

# Zobrazit logy
docker compose logs loki
docker compose logs promtail
```

## Testování

```bash
# Ověř, že Loki běží
curl http://localhost:3100/ready

# Ověř, že Promtail běží
curl http://localhost:9080/ready

# Dotaz na Loki API (ukázkový LogQL query)
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={service="backend"}' \
  | jq .
```

## LogQL příklady

```logql
# Všechny logy z backendu
{service="backend"}

# Error logy z Celery
{service="celery"} |~ "error|ERROR"

# Logy obsahující specifický text
{service=~"backend|celery"} |= "calculation"

# Logy za posledních 5 minut s rate
rate({service="backend"}[5m])
```

## Grafana zobrazení

1. Přejdi na http://localhost:3002 (Grafana)
2. Otevři dashboard "INFER FORGE - Přehled"
3. Scrolluj dolů na sekci "Logs"
4. Panely "Application Logs" a "Error Logs" zobrazují real-time logy

## Troubleshooting

### Promtail nenačítá logy
```bash
# Zkontroluj Docker socket permissions
ls -la /var/run/docker.sock

# Zkontroluj Promtail targets
curl http://localhost:9080/targets | jq .
```

### Loki neukládá data
```bash
# Zkontroluj volume
docker volume inspect infer-forge_loki-data

# Zkontroluj Loki konfig
docker exec infer-forge-loki cat /etc/loki/local-config.yaml
```

### Grafana nevidí Loki datasource
```bash
# Zkontroluj provisioned datasources
docker exec infer-forge-grafana ls -la /etc/grafana/provisioning/datasources/

# Restartuj Grafanu
docker compose restart grafana
```

## Produkční poznámky

- Pro produkci zvažte externí S3-compatible storage místo filesystem
- Upravte retenci dle potřeb: `retention_period: 30d` v `loki-config.yml`
- Pro high-traffic aplikace přidejte multiple Promtail repliky
- Zkonfiguruj alerting na základě error logů

## Soubory

- `/Users/lhradek/code/work/infer/infer-forge/docker/loki/loki-config.yml` - Loki konfigurace
- `/Users/lhradek/code/work/infer/infer-forge/docker/promtail/promtail-config.yml` - Promtail konfigurace
- `/Users/lhradek/code/work/infer/infer-forge/docker/grafana/provisioning/datasources/prometheus.yml` - Grafana datasources (Prometheus + Loki)
- `/Users/lhradek/code/work/infer/infer-forge/docker/grafana/dashboards/infer-forge.json` - Dashboard s log panely
