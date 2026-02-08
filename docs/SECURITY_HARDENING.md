# Security Hardening Guide

Tento dokument popisuje bezpečnostní opatření implementovaná v INFER FORGE a návod pro jejich nasazení.

## Přehled změn

### 1. Docker Security
- **Non-root users**: Backend i frontend kontejnery běží pod neprivilegovanými uživateli
  - Backend: `appuser:appuser` (již implementováno)
  - Frontend: `nextjs:nodejs` (již implementováno)

### 2. FastAPI Security Headers
Middleware přidává následující HTTP security headers:
- `X-Content-Type-Options: nosniff` - ochrana proti MIME sniffing
- `X-Frame-Options: DENY` - ochrana proti clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS filtr prohlížeče
- `Strict-Transport-Security` - vynucení HTTPS (HSTS)
- `Referrer-Policy` - kontrola Referer hlavičky

**Implementace**: `backend/app/main.py` - `SecurityHeadersMiddleware`

### 3. Fail2ban Configuration
Ochrana Nginx reverse proxy proti bruteforce útokům a rate limit violations.

**Soubory**:
- `docker/fail2ban/jail.local` - konfigurace pravidel
- `docker/fail2ban/filter.d/nginx-limit-req.conf` - pattern matcher

**Pravidla**:
- `nginx-http-auth`: Ban po 5 neúspěšných HTTP auth pokusech (1 hodina)
- `nginx-limit-req`: Ban po 10 rate limit violations (10 minut)

### 4. Security Audit Script
Automatický bezpečnostní audit celého stacku.

**Spuštění**: `./scripts/security-audit.sh`

**Kontroluje**:
- Python dependencies (pip-audit)
- Node.js dependencies (npm audit)
- Otevřené síťové porty
- Docker image vulnerabilities (docker scout, pokud dostupný)
- File permissions (.env, SSL certificates)
- Docker container users (non-root)
- Git secrets (náhodně commitnuté .env soubory)
- Database backup konfigurace

**Výstup**:
- `[OK]` - test prošel
- `[WARN]` - varování (nekritické)
- `[FAIL]` - kritický problém (vyžaduje akci)

## Nasazení na produkci

### 1. Aktivace security headers
Security headers middleware je již přidán v `backend/app/main.py`. Při dalším buildu kontejneru se aktivuje automaticky:

```bash
docker compose up --build backend
```

### 2. Nasazení Fail2ban (volitelné)
Fail2ban vyžaduje host-level instalaci (nemůže běžet v Docker kontejneru s omezenými oprávněními).

**Na server 91.99.126.53**:

```bash
# Instalace fail2ban
apt-get update && apt-get install -y fail2ban

# Zkopírování konfigurace
scp -i ~/.ssh/hetzner_server_ed25519 docker/fail2ban/jail.local leos@91.99.126.53:/etc/fail2ban/
scp -i ~/.ssh/hetzner_server_ed25519 docker/fail2ban/filter.d/nginx-limit-req.conf leos@91.99.126.53:/etc/fail2ban/filter.d/

# Restart fail2ban
systemctl restart fail2ban

# Ověření
fail2ban-client status
fail2ban-client status nginx-http-auth
fail2ban-client status nginx-limit-req
```

**Sledování banů**:
```bash
fail2ban-client status nginx-limit-req
tail -f /var/log/fail2ban.log
```

**Ruční unban IP**:
```bash
fail2ban-client set nginx-limit-req unbanip <IP_ADDRESS>
```

### 3. Pravidelný security audit
Doporučujeme spouštět audit:
- **Před každým deploymentem** (v CI/CD pipeline)
- **Týdně** (cron job)
- **Po každé aktualizaci dependencies**

**Přidání do CI/CD** (.github/workflows/ci.yml):
```yaml
- name: Security Audit
  run: |
    chmod +x scripts/security-audit.sh
    ./scripts/security-audit.sh
```

**Cron job na serveru**:
```bash
# Každou neděli v 2:00
0 2 * * 0 cd /path/to/infer-forge && ./scripts/security-audit.sh 2>&1 | mail -s "INFER FORGE Security Audit" admin@infer.cz
```

## Další doporučení

### 1. File permissions
Ujistěte se, že citlivé soubory mají správná oprávnění:

```bash
chmod 600 backend/.env frontend/.env
chmod 600 docker/nginx/ssl/*.key  # pokud existují SSL klíče
```

### 2. Secrets management
- **NIKDY necommitujte** `.env` soubory do gitu
- Používejte silná hesla (min. 16 znaků)
- Rotujte JWT secret a DB credentials pravidelně

### 3. Dependency updates
```bash
# Backend
cd backend && uv pip list --outdated
uv pip install --upgrade <package>

# Frontend
cd frontend && npm outdated
npm update
```

### 4. Database backups
Ověřte, že automatické zálohy fungují:
```bash
./scripts/backup_db.sh
ls -lh backups/
```

### 5. SSL/TLS
Pro produkční provoz vždy používejte HTTPS:
- Certifikát od Let's Encrypt (certbot)
- Nginx SSL konfigurace s TLS 1.2+
- Redirect HTTP → HTTPS

### 6. Rate limiting
Nginx rate limiting je již nakonfigurován v `docker/nginx/nginx.conf`:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;
```

## Monitoring

### Security events
- **Sentry**: Exception tracking + performance monitoring
- **Prometheus + Grafana**: Metrics dashboards (port 3002)
- **Fail2ban logs**: `/var/log/fail2ban.log`
- **Nginx logs**: `docker compose logs nginx`

### Alerting
Doporučené nastavení alertů:
- 5+ failed login attempts za minutu
- 10+ HTTP 5xx errors za minutu
- Vysoké CPU/memory usage (>80%)
- Failed backup jobs

## Kontakt
Pro bezpečnostní incidenty kontaktujte:
- Email: admin@infer.cz
- Tel: (dle interního telefonního seznamu Infer s.r.o.)

## Reference
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Nginx Security Best Practices](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
