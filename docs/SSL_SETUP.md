# INFER FORGE - SSL/TLS Setup Guide

Kompletní průvodce konfigurací SSL/TLS pro INFER FORGE s podporou pro development (self-signed) i production (Let's Encrypt) certifikáty.

## Přehled

INFER FORGE má integrovaný SSL setup systém s následujícími komponenty:

- **Nginx konfigurace** - HTTP→HTTPS redirect, moderní TLS, security headers
- **Setup script** - Automatizované generování certifikátů
- **Test script** - Validace SSL konfigurace
- **Certbot service** - Automatické obnovování Let's Encrypt certifikátů

## Architektura

```
docker/nginx/
├── nginx.conf           # Nginx konfigurace s SSL
└── ssl/
    ├── cert.pem         # SSL certifikát (fullchain)
    ├── key.pem          # Privátní klíč
    ├── .gitignore       # Ignore certifikáty v Gitu
    └── README.md        # SSL dokumentace

docker/certbot/          # Let's Encrypt certbot data (auto-generováno)
├── etc/                 # Certbot konfigurace
├── www/                 # ACME challenge webroot
└── log/                 # Certbot logy

scripts/
├── setup-ssl.sh         # SSL setup script
└── test-ssl.sh          # SSL test script
```

## Quick Start

### Development Setup (5 minut)

```bash
# 1. Vygeneruj self-signed certifikát
./scripts/setup-ssl.sh --self-signed

# 2. Spusť Docker stack
docker compose -f docker-compose.prod.yml up -d

# 3. Test SSL konfigurace
./scripts/test-ssl.sh

# 4. Otevři aplikaci
open https://localhost
# (Akceptuj bezpečnostní varování - očekávané pro self-signed)
```

### Production Setup (15 minut)

```bash
# PŘEDPOKLADY:
# - Doména směřuje na tento server (DNS A záznam)
# - Port 80 a 443 jsou otevřené
# - Docker Compose je nainstalován

# 1. Vygeneruj dočasný self-signed certifikát (pro první start)
./scripts/setup-ssl.sh --self-signed

# 2. Spusť Docker stack (musí běžet pro ACME challenge)
docker compose -f docker-compose.prod.yml up -d

# 3. Získej Let's Encrypt certifikát
./scripts/setup-ssl.sh --letsencrypt infer-forge.example.com

# 4. Restartuj nginx s novým certifikátem
docker compose -f docker-compose.prod.yml restart nginx

# 5. Zapni automatické obnovování (odkomentuj v docker-compose.prod.yml)
docker compose -f docker-compose.prod.yml up -d certbot

# 6. Test produkční konfigurace
./scripts/test-ssl.sh infer-forge.example.com

# 7. Ověř SSL grade (volitelné)
# https://www.ssllabs.com/ssltest/analyze.html?d=infer-forge.example.com
```

## Setup Script Možnosti

### Self-Signed Certificate

Pro development nebo testování bez vlastní domény:

```bash
./scripts/setup-ssl.sh --self-signed
```

**Vlastnosti:**
- Platnost: 365 dní
- Podporované domény: localhost, 127.0.0.1, 91.99.126.53
- Subject Alternative Names (SAN) pro flexibilitu
- Prohlížeč zobrazí varování (očekávané chování)

### Let's Encrypt Certificate

Pro produkční nasazení s důvěryhodným certifikátem:

```bash
./scripts/setup-ssl.sh --letsencrypt your-domain.com
```

**Požadavky:**
1. Doména musí směřovat na tento server (DNS A záznam)
2. Port 80 musí být otevřený a dostupný z internetu
3. Nginx musí běžet a mít přístup k `/.well-known/acme-challenge/`

**Vlastnosti:**
- Platnost: 90 dní
- Důvěryhodný pro všechny prohlížeče
- Zdarma
- Rate limit: 50 certifikátů týdně (na doménu)

### Obnovení Certifikátu

Pro manuální obnovení Let's Encrypt certifikátu:

```bash
./scripts/setup-ssl.sh --renew
docker compose -f docker-compose.prod.yml restart nginx
```

## Automatické Obnovování

Let's Encrypt certifikáty expirují po 90 dnech. Máš dvě možnosti automatického obnovování:

### Možnost 1: Certbot Docker Service (doporučeno)

Odkomentuj certbot service v `docker-compose.prod.yml`:

```yaml
certbot:
  image: certbot/certbot
  volumes:
    - ./docker/certbot/etc:/etc/letsencrypt
    - ./docker/certbot/www:/var/www/certbot
    - ./docker/certbot/log:/var/log/letsencrypt
  entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
  depends_on:
    - nginx
  restart: unless-stopped
```

Pak spusť:

```bash
docker compose -f docker-compose.prod.yml up -d certbot
```

Certbot automaticky kontroluje a obnovuje certifikát každých 12 hodin.

### Možnost 2: Cron Job

Přidej do cronu (pro uživatele s Docker přístupem):

```bash
# Každé pondělí v 3:00
0 3 * * 1 cd /opt/infer-forge && ./scripts/setup-ssl.sh --renew && docker compose -f docker-compose.prod.yml restart nginx >> /var/log/infer-forge-ssl-renew.log 2>&1
```

## Nginx Konfigurace

Konfigurace je v `docker/nginx/nginx.conf`:

### HTTP Server (Port 80)

```nginx
server {
    listen 80;
    server_name _;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect vše ostatní na HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}
```

### HTTPS Server (Port 443)

```nginx
server {
    listen 443 ssl http2;
    server_name _;

    # SSL certifikáty
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Modern SSL konfigurace
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:...';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ... location bloky pro API, WS, frontend ...
}
```

## SSL Test Script

Pro ověření SSL konfigurace spusť:

```bash
./scripts/test-ssl.sh [domain]
```

**Kontroly:**
- Existence certifikátů
- Platnost certifikátu (expirační datum)
- Shoda certifikátu a privátního klíče
- Oprávnění souborů (600 pro key, 644 pro cert)
- Validita nginx konfigurace
- HTTPS připojení
- Bezpečnostní headery

**Příklad výstupu:**

```
==========================================
  INFER FORGE SSL/TLS Configuration Test
==========================================

[✓] Certifikáty nalezeny
[✓] Certifikát je platný ještě 89 dní
[✓] Certifikát a privátní klíč jsou spárované
[✓] cert.pem má správná oprávnění (644)
[✓] key.pem má správná oprávnění (600)
[✓] docker-compose.prod.yml je validní
[✓] Nginx container běží
[✓] Nginx konfigurace je validní
[✓] HTTPS spojení k domain.com úspěšné
[✓] HSTS header nalezen
[✓] X-Frame-Options header nalezen
[✓] X-Content-Type-Options header nalezen

==========================================
  Test dokončen
==========================================
```

## Bezpečnostní Best Practices

### Oprávnění Souborů

```bash
# Privátní klíč - pouze vlastník
chmod 600 docker/nginx/ssl/key.pem

# Certifikát - čitelný pro všechny
chmod 644 docker/nginx/ssl/cert.pem
```

### Git Security

Certifikáty a klíče jsou v `.gitignore`:

```gitignore
# SSL certifikáty
*.pem
*.crt
*.key
*.csr
docker/certbot/
```

**NIKDY necommituj privátní klíče do Git!**

### TLS Protokoly

Používáme pouze moderní TLS verze:

```nginx
ssl_protocols TLSv1.2 TLSv1.3;  # ✅ Bezpečné
# ssl_protocols TLSv1 TLSv1.1;  # ❌ Zastaralé a zranitelné
```

### Cipher Suite

Moderní cipher suite s forward secrecy:

```nginx
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers off;  # Preferuj klientské ciphers (moderní praxe)
```

### HSTS (HTTP Strict Transport Security)

Nutí prohlížeč vždy používat HTTPS:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

**Pozor:** HSTS je "lepkavý" - po nastavení nelze snadno vrátit na HTTP!

## Troubleshooting

### Certbot selhal s "Failed authorization"

**Příčina:** Certbot nemůže ověřit vlastnictví domény.

**Řešení:**

```bash
# 1. Zkontroluj DNS
dig +short infer-forge.example.com
# Mělo by vrátit IP adresu tohoto serveru

# 2. Zkontroluj port 80
curl -I http://infer-forge.example.com/.well-known/acme-challenge/test
# Mělo by vrátit 404 (ne connection refused)

# 3. Zkontroluj firewall
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 4. Zkontroluj nginx logs
docker compose -f docker-compose.prod.yml logs nginx

# 5. Zkontroluj certbot logs
cat docker/certbot/log/letsencrypt.log
```

### Nginx nenaběhne po aktivaci SSL

**Příčina:** Chybějící certifikáty nebo nevalidní konfigurace.

**Řešení:**

```bash
# 1. Zkontroluj, zda certifikáty existují
ls -la docker/nginx/ssl/

# 2. Pokud chybí, vygeneruj self-signed
./scripts/setup-ssl.sh --self-signed

# 3. Test nginx konfigurace
docker compose -f docker-compose.prod.yml exec nginx nginx -t

# 4. Zkontroluj logy
docker compose -f docker-compose.prod.yml logs nginx
```

### Prohlížeč zobrazuje "Not Secure" nebo varování

**Self-signed certifikát:**
- Očekávané chování pro development
- Prohlížeč zobrazí varování
- Musíš manuálně přidat výjimku

**Let's Encrypt:**
- Zkontroluj, zda certifikát není expirovaný:
  ```bash
  openssl x509 -in docker/nginx/ssl/cert.pem -noout -dates
  ```
- Obnov certifikát:
  ```bash
  ./scripts/setup-ssl.sh --renew
  docker compose -f docker-compose.prod.yml restart nginx
  ```

**Mixed Content:**
- Všechny zdroje (CSS, JS, API) musí používat HTTPS
- Zkontroluj browser console pro mixed content errors

### Certifikát expiruje brzy

**Kontrola:**

```bash
./scripts/test-ssl.sh
# Zobrazí: "Certifikát vyprší za X dní"
```

**Obnova:**

```bash
./scripts/setup-ssl.sh --renew
docker compose -f docker-compose.prod.yml restart nginx
```

**Prevence:**

Zapni automatické obnovování (viz sekce "Automatické Obnovování").

## SSL Labs Test

Pro produkční nasazení doporučujeme test na SSL Labs:

1. Otevři: https://www.ssllabs.com/ssltest/
2. Zadej doménu: `infer-forge.example.com`
3. Počkej na analýzu (2-3 minuty)
4. **Cílová známka: A+**

Pokud nedosáhneš A+, zkontroluj:
- TLS protokoly (pouze 1.2 a 1.3)
- Cipher suite (moderní ciphers)
- HSTS header (max-age min. 31536000)
- Certificate chain (musí obsahovat intermediate cert)

## Migrace z HTTP na HTTPS

Pokud už máš běžící produkční instanci na HTTP:

```bash
# 1. Backup!
./scripts/backup_db.sh

# 2. Vygeneruj self-signed certifikát (pro první start)
./scripts/setup-ssl.sh --self-signed

# 3. Aktualizuj docker-compose.prod.yml
# (přidej port 443, SSL volume mount - viz docs/deployment.md)

# 4. Restartuj stack
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# 5. Získej Let's Encrypt certifikát
./scripts/setup-ssl.sh --letsencrypt infer-forge.example.com

# 6. Restartuj nginx
docker compose -f docker-compose.prod.yml restart nginx

# 7. Aktualizuj CORS_ORIGINS v .env.prod
# CORS_ORIGINS=https://infer-forge.example.com

# 8. Restartuj backend
docker compose -f docker-compose.prod.yml restart backend

# 9. Test
./scripts/test-ssl.sh infer-forge.example.com
```

## Poznámky

- **Backup:** Před jakoukoli změnou SSL certifikátů proveď backup
- **Downtime:** Migrace na HTTPS může způsobit krátké přerušení služby (1-2 minuty)
- **CORS:** Po aktivaci HTTPS nezapomeň aktualizovat `CORS_ORIGINS` v `.env.prod`
- **Monitoring:** Nastav monitoring pro expiraci certifikátů (alerting 30 dní před expirací)
- **Rate limiting:** Let's Encrypt má rate limity (50 certifikátů/týden na doménu) - netlač to 🙂

## Reference

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)
- [Nginx SSL Module](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)
- [OWASP Transport Layer Protection Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)

---

**Poslední update:** 2026-02-08
**Next review:** 2026-05-08 (za 3 měsíce)
