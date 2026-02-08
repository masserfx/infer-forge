# INFER FORGE - Bezpečnostní dokumentace

Bezpečnostní guidelines a best practices pro provoz INFER FORGE v produkčním prostředí.

## Přehled bezpečnostních opatření

### ✅ Implementováno

- [x] HTTPS/TLS šifrování (Let's Encrypt)
- [x] CORS ochrana (konfiguratelné origins)
- [x] JWT autentizace s expirací tokenů
- [x] Rate limiting na API endpointech
- [x] SQL injection ochrana (SQLAlchemy ORM)
- [x] XSS ochrana (React auto-escaping)
- [x] RBAC (Role-Based Access Control)
- [x] Audit trail všech operací
- [x] AES-256 šifrování citlivých dat
- [x] Docker containers jako non-root users
- [x] Environment variables pro secrets
- [x] Health check endpoints
- [x] Structured logging (structlog)

## 1. CORS konfigurace

### Development

```bash
# .env
CORS_ORIGINS=http://localhost:3000
```

### Production

```bash
# .env.prod
CORS_ORIGINS=https://infer-forge.example.com,https://www.infer-forge.example.com
```

### NIKDY nepoužívej

```bash
# ❌ NEBEZPEČNÉ - povoluje všechny origins
CORS_ORIGINS=*
```

### Test CORS

```bash
./scripts/test-cors.sh http://localhost:8000
```

## 2. Secrets management

### Generování silných hesel

```bash
# Automatické generování všech secrets
python scripts/generate-secrets.py --output .env.prod

# Nebo jednotlivě
python -c "import secrets; print(secrets.token_urlsafe(64))"  # SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"      # hesla
```

### Minimální požadavky

| Secret | Min. délka | Doporučeno |
|--------|------------|------------|
| SECRET_KEY | 64 znaků | 128 znaků |
| POSTGRES_PASSWORD | 32 znaků | 64 znaků |
| REDIS_PASSWORD | 32 znaků | 64 znaků |
| API Keys | vendor specific | N/A |

### Rotace secrets

**Doporučená frekvence:** každé 3 měsíce

```bash
# 1. Vygeneruj nové secrets
python scripts/generate-secrets.py --quick

# 2. Aktualizuj .env.prod

# 3. Backup databáze
./scripts/backup.sh

# 4. Restart služeb
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# 5. Ověř funkčnost
./scripts/health-check.sh
```

## 3. SSL/TLS certifikáty

INFER FORGE má integrovaný SSL setup script s podporou pro development i production certifikáty.

### Development (Self-Signed)

Pro lokální vývoj nebo testování:

```bash
./scripts/setup-ssl.sh --self-signed
```

Certifikát je platný 365 dní s podporou pro `localhost`, `127.0.0.1` a `91.99.126.53` (dev server).

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

### Automatická obnova certifikátu

Let's Encrypt certifikáty jsou platné 90 dní. Máš dvě možnosti:

**Možnost 1: Certbot service v Docker Compose (doporučeno)**

```bash
# V docker-compose.prod.yml odkomentuj certbot service
# Pak spusť:
docker compose -f docker-compose.prod.yml up -d certbot
```

Certbot service automaticky kontroluje a obnovuje certifikát každých 12 hodin.

**Možnost 2: Cron job**

```bash
# Každé pondělí v 3:00
0 3 * * 1 cd /opt/infer-forge && ./scripts/setup-ssl.sh --renew && docker compose -f docker-compose.prod.yml restart nginx
```

### Nginx SSL konfigurace (již implementováno)

Konfigurace v `docker/nginx/nginx.conf`:

```nginx
# HTTP → HTTPS redirect
server {
    listen 80;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

# HTTPS server
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Modern SSL konfigurace
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

### Ověření SSL konfigurace

```bash
# Test SSL konfigurace
openssl s_client -connect infer-forge.example.com:443 -servername infer-forge.example.com

# Zkontroluj platnost certifikátu
openssl x509 -in docker/nginx/ssl/cert.pem -text -noout | grep -A2 "Validity"

# Online test (po nasazení)
# https://www.ssllabs.com/ssltest/analyze.html?d=infer-forge.example.com
```

## 4. Rate limiting

### Nginx rate limiting

```nginx
# Definice zón
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;

# API endpoints
location /api/ {
    limit_req zone=api burst=20 nodelay;
    # ...
}

# Auth endpoints (přísnější limity)
location /api/v1/auth/ {
    limit_req zone=auth burst=5 nodelay;
    # ...
}
```

### FastAPI middleware (budoucí implementace)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/orders")
@limiter.limit("100/minute")
async def get_orders():
    ...
```

## 5. Firewall konfigurace

### UFW (Ubuntu)

```bash
# Povolit pouze potřebné porty
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Ověření
sudo ufw status verbose
```

### Interní služby (pouze localhost)

V `docker-compose.prod.yml` jsou porty bindovány na `127.0.0.1`:

```yaml
services:
  db:
    ports:
      - "127.0.0.1:5432:5432"  # ✅ Pouze localhost
  redis:
    ports:
      - "127.0.0.1:6379:6379"  # ✅ Pouze localhost
  backend:
    ports:
      - "127.0.0.1:8000:8000"  # ✅ Pouze localhost (Nginx proxy)
```

## 6. SSH hardening

```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2

# Restart SSH
sudo systemctl restart sshd
```

### SSH klíče

```bash
# Generování ED25519 klíče (moderní, bezpečný)
ssh-keygen -t ed25519 -C "admin@infer-forge"

# Přidání do serveru
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server
```

## 7. Audit trail

Všechny kritické operace jsou logovány do databáze:

```python
# Příklad audit log entry
{
    "user_id": "uuid",
    "action": "order.created",
    "entity_type": "Order",
    "entity_id": "uuid",
    "timestamp": "2026-02-07T10:30:00Z",
    "ip_address": "192.168.1.100",
    "metadata": {
        "order_number": "2026-001",
        "customer_id": "uuid"
    }
}
```

### Query audit trail

```sql
-- Všechny akce konkrétního uživatele
SELECT * FROM audit_logs
WHERE user_id = 'uuid'
ORDER BY timestamp DESC
LIMIT 100;

-- Změny na konkrétní entitě
SELECT * FROM audit_logs
WHERE entity_type = 'Order' AND entity_id = 'uuid'
ORDER BY timestamp DESC;

-- Podezřelé aktivity (mnoho failů)
SELECT user_id, COUNT(*) as failed_attempts
FROM audit_logs
WHERE action LIKE '%failed'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY user_id
HAVING COUNT(*) > 10;
```

## 8. Backup security

### Šifrované backupy

```bash
#!/bin/bash
# Backup s GPG šifrováním

BACKUP_DIR="/var/backups/infer-forge"
GPG_RECIPIENT="backup@infer.cz"

# Backup DB
docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U infer infer_forge | \
    gzip | \
    gpg --encrypt --recipient "$GPG_RECIPIENT" \
    > "$BACKUP_DIR/db_$(date +%Y%m%d).sql.gz.gpg"

# Restore
gpg --decrypt "$BACKUP_DIR/db_20260207.sql.gz.gpg" | \
    gunzip | \
    docker compose -f docker-compose.prod.yml exec -T db \
    psql -U infer infer_forge
```

### Off-site backupy

```bash
# Rsync na záložní server
rsync -avz --delete \
    -e "ssh -i /root/.ssh/backup_key" \
    /var/backups/infer-forge/ \
    backup@backup-server:/backups/infer-forge/
```

## 9. Dependency security

### Backend (Python)

```bash
# Audit dependencies
uv pip list --outdated

# Check security vulnerabilities (pip-audit)
pip install pip-audit
pip-audit

# Update dependencies
uv pip install --upgrade <package>
```

### Frontend (npm)

```bash
# Audit dependencies
npm audit

# Fix automaticky opravitelné
npm audit fix

# Update dependencies
npm update
```

### Automatické security updates

```yaml
# .github/workflows/security.yml
name: Security Audit
on:
  schedule:
    - cron: '0 0 * * 0'  # Týdně
  workflow_dispatch:

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Python security audit
        run: |
          pip install pip-audit
          pip-audit
      - name: npm security audit
        run: npm audit
```

## 10. Monitoring a alerting

### Sentry (error tracking)

```bash
# .env.prod
SENTRY_DSN=https://xxx@sentry.io/yyy
```

### Prometheus metrics (budoucí)

```python
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    request_count.inc()
    with request_duration.time():
        response = await call_next(request)
    return response
```

## 11. Security headers

Nginx security headers (již v deployment.md):

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

## 12. GDPR & ISO 9001 compliance

### Data retention

```sql
-- Automatické mazání starých audit logů (starší než 2 roky)
DELETE FROM audit_logs
WHERE timestamp < NOW() - INTERVAL '2 years';

-- Archivace před smazáním
INSERT INTO audit_logs_archive
SELECT * FROM audit_logs
WHERE timestamp < NOW() - INTERVAL '2 years';
```

### Right to be forgotten

```python
async def anonymize_user_data(user_id: str) -> None:
    """GDPR - právo být zapomenut."""
    # Anonymizuj osobní údaje
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            email=f"deleted_{user_id}@localhost",
            name="Deleted User",
            phone=None,
            deleted_at=datetime.utcnow(),
        )
    )
```

## 13. Security checklist

### Pre-production

- [ ] SECRET_KEY vygenerován random (min. 64 znaků)
- [ ] Všechna hesla silná (min. 32 znaků)
- [ ] `.env.prod` není v Git
- [ ] CORS_ORIGINS nastaveno správně (ne `*`)
- [ ] SSL/TLS certifikáty platné
- [ ] Firewall aktivní (pouze 22, 80, 443)
- [ ] SSH pouze s klíči
- [ ] Docker porty na `127.0.0.1` (ne `0.0.0.0`)
- [ ] Rate limiting aktivní
- [ ] Security headers nastaveny
- [ ] Backup skript funkční
- [ ] Monitoring (Sentry) aktivní

### Post-production

- [ ] Týdenní dependency audit
- [ ] Měsíční penetration testing
- [ ] Čtvrtletní rotace secrets
- [ ] Pravidelné security updates
- [ ] Monitoring dashboards
- [ ] Incident response plan

## 14. Incident response

### V případě security incidentu

1. **Izoluj** - Odpoj postižený server z internetu
2. **Analyzuj** - Zkontroluj logy, audit trail
3. **Obsahuj** - Změň všechny secrets, rotuj JWT tokens
4. **Obnov** - Restore z posledního známého dobrého backupu
5. **Dokumentuj** - Zapiš incident do audit logu
6. **Prevence** - Implementuj dodatečná opatření

### Kontakty

- **Security incidents:** security@infer.cz
- **On-call:** +420 XXX XXX XXX

---

**Poslední update:** 2026-02-07
**Next review:** 2026-05-07 (za 3 měsíce)
