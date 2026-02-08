# INFER FORGE - Produkční Deployment

Návod pro nasazení INFER FORGE do produkčního prostředí.

## Předpoklady

- **Server:** Linux (Ubuntu 22.04 LTS doporučeno), min. 4GB RAM, 50GB disk
- **Software:** Docker 24+, Docker Compose 2.20+
- **Síť:** Port 80/443 (HTTP/HTTPS), případně reverzní proxy (Nginx/Traefik)
- **Bezpečnost:** Firewall, SSH klíče, pravidelné backupy

## 1. Příprava serveru

```bash
# Aktualizace systému
sudo apt update && sudo apt upgrade -y

# Instalace Docker a Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Instalace závislostí
sudo apt install -y git certbot python3-certbot-nginx
```

## 2. Příprava aplikace

```bash
# Clone repository
git clone https://github.com/your-org/infer-forge.git
cd infer-forge

# Vytvoř produkční environment
cp .env.prod.example .env.prod

# DŮLEŽITÉ: Upravit .env.prod s reálnými hodnotami
nano .env.prod
```

### Generování bezpečných hesel

```bash
# SECRET_KEY (64 znaků)
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Database a Redis hesla (32 znaků)
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 3. CORS konfigurace

V `.env.prod` nastav správné CORS origins:

```bash
# Development
CORS_ORIGINS=http://localhost:3000

# Production (multiple origins)
CORS_ORIGINS=https://infer-forge.example.com,https://www.infer-forge.example.com

# Production s API subdoménou
CORS_ORIGINS=https://app.infer-forge.example.com,https://infer-forge.example.com
```

## 4. SSL/TLS certifikáty

INFER FORGE má integrovaný SSL setup script s podporou pro development i production certifikáty.

### Development (Self-Signed Certificate)

Pro lokální vývoj nebo testování:

```bash
./scripts/setup-ssl.sh --self-signed
```

Tento certifikát je platný 365 dní, ale zobrazí varování v prohlížeči (očekávané chování).

### Production (Let's Encrypt)

Pro produkční nasazení s důvěryhodným certifikátem:

```bash
# PŘED SPUŠTĚNÍM ujisti se, že:
# 1. Doména směřuje na tento server (DNS A záznam)
# 2. Port 80 je otevřený a dostupný z internetu
# 3. Nginx běží a má přístup k /.well-known/acme-challenge/

./scripts/setup-ssl.sh --letsencrypt infer-forge.example.com

# Po získání certifikátu restartuj nginx
docker compose -f docker-compose.prod.yml restart nginx
```

### Automatické obnovování certifikátu

Let's Encrypt certifikáty jsou platné 90 dní. Pro automatické obnovování:

```bash
# V docker-compose.prod.yml odkomentuj certbot service
# Pak spusť:
docker compose -f docker-compose.prod.yml up -d certbot
```

Nebo nastav cron job pro manuální obnovování:

```bash
# Každé pondělí v 3:00
0 3 * * 1 cd /opt/infer-forge && ./scripts/setup-ssl.sh --renew && docker compose -f docker-compose.prod.yml restart nginx
```

## 5. Spuštění aplikace

```bash
# Build a spuštění všech služeb
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Sledování logů
docker compose -f docker-compose.prod.yml logs -f

# Ověření health check
curl http://localhost:8000/health
```

## 6. Inicializace databáze

```bash
# Spuštění Alembic migrací
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Vytvoření prvního admin uživatele (volitelné)
docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.create_admin
```

## 7. Nginx reverzní proxy (doporučeno)

Vytvoř `/etc/nginx/sites-available/infer-forge`:

```nginx
# Backend API
upstream backend {
    server 127.0.0.1:8000;
}

# Frontend
upstream frontend {
    server 127.0.0.1:3000;
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name infer-forge.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name infer-forge.example.com;

    ssl_certificate /etc/letsencrypt/live/infer-forge.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/infer-forge.example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API requests
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Rate limiting
        limit_req zone=api burst=20 nodelay;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # File uploads (max 50MB)
    client_max_body_size 50M;
}

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

Aktivace:

```bash
sudo ln -s /etc/nginx/sites-available/infer-forge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 8. Automatické backupy

Vytvoř `/usr/local/bin/infer-forge-backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/infer-forge"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL
docker compose -f /opt/infer-forge/docker-compose.prod.yml exec -T db \
    pg_dump -U infer infer_forge | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Backup Redis (pokud obsahuje důležitá data)
docker compose -f /opt/infer-forge/docker-compose.prod.yml exec -T redis \
    redis-cli --rdb /data/dump.rdb SAVE
docker cp infer-forge-redis-1:/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Backup dokumentů a uploadů
tar -czf "$BACKUP_DIR/volumes_$DATE.tar.gz" \
    -C /var/lib/docker/volumes \
    infer-forge_documents infer-forge_uploads

# Smazání starých backupů
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete

echo "Backup dokončen: $DATE"
```

Nastav cron job:

```bash
sudo chmod +x /usr/local/bin/infer-forge-backup.sh
sudo crontab -e

# Denní backup v 2:00
0 2 * * * /usr/local/bin/infer-forge-backup.sh >> /var/log/infer-forge-backup.log 2>&1
```

## 9. Monitoring a logování

### Strukturované logy

```bash
# Sledování všech logů
docker compose -f docker-compose.prod.yml logs -f

# Pouze backend
docker compose -f docker-compose.prod.yml logs -f backend

# Celery worker
docker compose -f docker-compose.prod.yml logs -f celery-worker

# Export logů do souboru
docker compose -f docker-compose.prod.yml logs --no-color > logs.txt
```

### Sentry integrace (volitelné)

1. Vytvoř projekt na [sentry.io](https://sentry.io)
2. Přidej DSN do `.env.prod`:
   ```bash
   SENTRY_DSN=https://xxx@sentry.io/yyy
   ```
3. Restartuj služby:
   ```bash
   docker compose -f docker-compose.prod.yml restart backend celery-worker
   ```

## 10. Aktualizace aplikace

```bash
# Pull nových změn
cd /opt/infer-forge
git pull

# Backup před aktualizací
/usr/local/bin/infer-forge-backup.sh

# Rebuild a restart služeb
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Spuštění migrací
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Ověření health check
curl http://localhost:8000/health
```

## 11. Rollback (v případě problémů)

```bash
# Zastavení služeb
docker compose -f docker-compose.prod.yml down

# Obnovení Git verze
git checkout <předchozí-commit-hash>

# Rebuild a spuštění
docker compose -f docker-compose.prod.yml up -d --build

# Rollback databáze (pokud potřeba)
docker compose -f docker-compose.prod.yml exec backend alembic downgrade <revision>
```

## 12. Bezpečnostní checklist

- [ ] Silná hesla v `.env.prod` (min. 32 znaků)
- [ ] `.env.prod` není v Git (ověř `.gitignore`)
- [ ] CORS_ORIGINS nastaveno na produkční domény (ne `*`)
- [ ] SSL/TLS certifikáty aktivní (HTTPS)
- [ ] Firewall aktivní (UFW/iptables)
- [ ] SSH pouze s klíči (disable password auth)
- [ ] Pravidelné security updates (`unattended-upgrades`)
- [ ] Denní databázové backupy
- [ ] Monitoring (Sentry, Prometheus, nebo Grafana)
- [ ] Rate limiting na API endpointech
- [ ] Docker containers běží jako non-root users

## 13. Řešení problémů

### Služba se nespustí

```bash
# Detailní logy
docker compose -f docker-compose.prod.yml logs backend

# Ověření health checks
docker compose -f docker-compose.prod.yml ps
```

### Databázové chyby

```bash
# Připojení do DB konzole
docker compose -f docker-compose.prod.yml exec db psql -U infer -d infer_forge

# Ověření migrací
docker compose -f docker-compose.prod.yml exec backend alembic current
```

### Celery worker nereaguje

```bash
# Restart workeru
docker compose -f docker-compose.prod.yml restart celery-worker

# Sledování Celery logů
docker compose -f docker-compose.prod.yml logs -f celery-worker

# Kontrola Redis fronty
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD
> KEYS celery*
```

## 14. Kontakty

- **Technická podpora:** dev@infer.cz
- **Dokumentace:** `/opt/infer-forge/docs/`
- **GitHub Issues:** https://github.com/your-org/infer-forge/issues

---

**Poznámka:** Tento deployment je navržen pro on-premise instalaci kvůli citlivým zákaznickým datům (ISO 9001:2016, GDPR compliance).
