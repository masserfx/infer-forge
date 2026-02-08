# SSL/TLS Certificates

Tento adresář obsahuje SSL certifikáty pro HTTPS komunikaci.

## Struktura

```
ssl/
├── cert.pem        # SSL certifikát (fullchain)
├── key.pem         # Privátní klíč
└── README.md       # Tato dokumentace
```

## Setup

### Development (Self-Signed Certificate)

Pro lokální vývoj nebo testování použij self-signed certifikát:

```bash
./scripts/setup-ssl.sh --self-signed
```

Tento certifikát je platný 365 dní, ale není důvěryhodný pro prohlížeče (zobrazí varování).

### Production (Let's Encrypt)

Pro produkční nasazení s důvěryhodným certifikátem:

```bash
./scripts/setup-ssl.sh --letsencrypt forge.infer.cz
```

**Požadavky:**
- Doména musí směřovat na tento server (DNS A záznam)
- Port 80 (HTTP) musí být otevřený a dostupný z internetu
- Nginx musí běžet s konfigurací pro ACME challenge

### Obnovení Certifikátu

Let's Encrypt certifikáty jsou platné 90 dní. Pro manuální obnovení:

```bash
./scripts/setup-ssl.sh --renew
docker compose -f docker-compose.prod.yml restart nginx
```

### Automatické Obnovování

Pro automatické obnovování každých 12 hodin zapni certbot service:

```bash
# V docker-compose.prod.yml odkomentuj certbot service
# Pak spusť:
docker compose -f docker-compose.prod.yml up -d certbot
```

## Bezpečnost

- `key.pem` má práva `600` (čitelný pouze pro vlastníka)
- `cert.pem` má práva `644` (čitelný pro všechny)
- Nikdy necommituj privátní klíče do Git
- Tento adresář je v `.gitignore` (kromě README.md)

## Kontrola Certifikátu

```bash
# Zobraz detaily certifikátu
openssl x509 -in ssl/cert.pem -text -noout

# Zkontroluj platnost
openssl x509 -in ssl/cert.pem -noout -dates

# Ověř certifikát a klíč
openssl rsa -in ssl/key.pem -check
```

## Troubleshooting

### Nginx nenaběhne po aktivaci SSL

```bash
# Zkontroluj, zda certifikáty existují
ls -la docker/nginx/ssl/

# Zkontroluj nginx syntax
docker compose -f docker-compose.prod.yml exec nginx nginx -t

# Zkontroluj logy
docker compose -f docker-compose.prod.yml logs nginx
```

### Let's Encrypt selže s "Failed authorization"

- Zkontroluj DNS: `dig forge.infer.cz`
- Zkontroluj dostupnost portu 80: `curl -I http://forge.infer.cz/.well-known/acme-challenge/test`
- Zkontroluj firewall: `sudo ufw status` (nebo iptables)
- Zkontroluj certbot logy: `cat docker/certbot/log/letsencrypt.log`

### Prohlížeč zobrazuje "Not Secure"

- Self-signed certifikát: očekávané chování, musíš přidat výjimku
- Let's Encrypt: zkontroluj, zda certifikát není expirovaný
- Mixed content: ujisti se, že všechny zdroje (CSS, JS, API) používají HTTPS

## Konfigurace Nginx

Nginx konfigurace pro SSL/TLS:

```nginx
# HTTP → HTTPS redirect
server {
    listen 80;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

# HTTPS
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    # ... security headers ...
}
```

## Reference

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Nginx SSL Module](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)
