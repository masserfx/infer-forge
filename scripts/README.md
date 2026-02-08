# INFER FORGE Scripts

Utility skripty pro správu INFER FORGE produkčního prostředí.

## Zálohovací Systém

### Instalace automatických záloh
```bash
sudo ./backup-cron.sh
```

### Manuální záloha
```bash
# Denní záloha
./backup_db.sh

# Týdenní záloha (delší retention)
./backup_db.sh --weekly
```

### Obnovení ze zálohy
```bash
# Pouze databáze
./restore_db.sh /opt/infer-forge/backups/infer-forge-backup-*.sql.gz

# Databáze + uploads
./restore_db.sh backup.sql.gz uploads.tar.gz
```

### Sledování
```bash
# Live logy
tail -f /var/log/infer-forge-backup.log

# Seznam záloh
ls -lh /opt/infer-forge/backups/
```

## SSL/TLS Certifikáty

### Development
```bash
# Generuj self-signed certifikát
./setup-ssl.sh --self-signed

# Test konfigurace
./test-ssl.sh
```

### Production
```bash
# Získej Let's Encrypt certifikát
./setup-ssl.sh --letsencrypt infer-forge.example.com

# Obnov certifikát
./setup-ssl.sh --renew

# Test produkční konfigurace
./test-ssl.sh infer-forge.example.com
```

Viz [docker/nginx/ssl/README.md](../docker/nginx/ssl/README.md) pro kompletní SSL dokumentaci.

## Kompletní Dokumentace

Viz [docs/BACKUP_SYSTEM.md](../docs/BACKUP_SYSTEM.md) pro detailní návod, retention policy, troubleshooting a ISO 9001 compliance.

## Skripty

| Skript | Účel |
|--------|------|
| `backup_db.sh` | Záloha DB + uploads (pg_dump, docker cp, gzip) |
| `backup-rotation.sh` | Rotace záloh (7/4/3 denní/týdenní/měsíční) |
| `backup-cron.sh` | Instalace cron jobs (denní 2:00, týdenní ne 3:00) |
| `restore_db.sh` | Obnovení DB ze zálohy (safety backup, alembic) |
| `setup-ssl.sh` | SSL certifikát setup (self-signed nebo Let's Encrypt) |
| `test-ssl.sh` | Test SSL konfigurace a certifikátů |
| `generate-secrets.py` | Generování bezpečných secrets pro .env.prod |
| `test-cors.sh` | Test CORS konfigurace |
| `health-check.sh` | Health check všech služeb |
| `security-audit.sh` | Security audit (dependencies, config, permissions) |

## Environment Variables

```bash
# Cesty
BACKUP_DIR=/opt/infer-forge/backups
LOG_FILE=/var/log/infer-forge-backup.log

# Retention
RETENTION_DAYS=30
WEEKLY_RETENTION_DAYS=90

# Database (z .env.prod)
POSTGRES_DB=infer_forge
POSTGRES_USER=infer
POSTGRES_PASSWORD=***
```

## Požadavky

- Docker Compose (production stack `docker-compose.prod.yml`)
- Root oprávnění (pro cron setup)
- `.env.prod` soubor v kořenu projektu
