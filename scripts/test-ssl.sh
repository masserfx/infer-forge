#!/bin/bash
# SSL/TLS Configuration Test Script for INFER FORGE
# Usage: ./scripts/test-ssl.sh [domain]

set -euo pipefail

DOMAIN="${1:-localhost}"
SSL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docker/nginx/ssl"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_test() {
    echo -e "${BLUE}[→]${NC} $1"
}

echo "=========================================="
echo "  INFER FORGE SSL/TLS Configuration Test"
echo "=========================================="
echo ""

# 1. Check if SSL certificates exist
log_test "Kontrola SSL certifikátů..."
if [ -f "$SSL_DIR/cert.pem" ] && [ -f "$SSL_DIR/key.pem" ]; then
    log_info "Certifikáty nalezeny"

    # Check certificate validity
    EXPIRY_DATE=$(openssl x509 -in "$SSL_DIR/cert.pem" -noout -enddate | cut -d= -f2)
    DAYS_UNTIL_EXPIRY=$(( ($(date -j -f "%b %d %T %Y %Z" "$EXPIRY_DATE" +%s) - $(date +%s)) / 86400 ))

    if [ "$DAYS_UNTIL_EXPIRY" -lt 0 ]; then
        log_error "Certifikát expiroval před $((0 - DAYS_UNTIL_EXPIRY)) dny!"
    elif [ "$DAYS_UNTIL_EXPIRY" -lt 30 ]; then
        log_warn "Certifikát vyprší za $DAYS_UNTIL_EXPIRY dní (obnov ho)"
    else
        log_info "Certifikát je platný ještě $DAYS_UNTIL_EXPIRY dní"
    fi

    # Check certificate details
    CERT_ISSUER=$(openssl x509 -in "$SSL_DIR/cert.pem" -noout -issuer | sed 's/issuer=//')
    CERT_SUBJECT=$(openssl x509 -in "$SSL_DIR/cert.pem" -noout -subject | sed 's/subject=//')

    echo ""
    echo "  Issuer:  $CERT_ISSUER"
    echo "  Subject: $CERT_SUBJECT"
    echo "  Expires: $EXPIRY_DATE"
    echo ""
else
    log_error "SSL certifikáty nenalezeny v $SSL_DIR/"
    log_warn "Spusť: ./scripts/setup-ssl.sh --self-signed"
    exit 1
fi

# 2. Check certificate and key match
log_test "Kontrola shody certifikátu a privátního klíče..."
CERT_MD5=$(openssl x509 -noout -modulus -in "$SSL_DIR/cert.pem" | openssl md5)
KEY_MD5=$(openssl rsa -noout -modulus -in "$SSL_DIR/key.pem" 2>/dev/null | openssl md5)

if [ "$CERT_MD5" = "$KEY_MD5" ]; then
    log_info "Certifikát a privátní klíč jsou spárované"
else
    log_error "Certifikát a privátní klíč NESOUHLASÍ!"
    exit 1
fi

# 3. Check file permissions
log_test "Kontrola oprávnění souborů..."
CERT_PERMS=$(stat -f "%Lp" "$SSL_DIR/cert.pem" 2>/dev/null || stat -c "%a" "$SSL_DIR/cert.pem" 2>/dev/null)
KEY_PERMS=$(stat -f "%Lp" "$SSL_DIR/key.pem" 2>/dev/null || stat -c "%a" "$SSL_DIR/key.pem" 2>/dev/null)

if [ "$CERT_PERMS" = "644" ]; then
    log_info "cert.pem má správná oprávnění (644)"
else
    log_warn "cert.pem má oprávnění $CERT_PERMS (doporučeno: 644)"
fi

if [ "$KEY_PERMS" = "600" ]; then
    log_info "key.pem má správná oprávnění (600)"
else
    log_error "key.pem má oprávnění $KEY_PERMS (MUSÍ být 600!)"
    log_warn "Oprav: chmod 600 $SSL_DIR/key.pem"
fi

# 4. Check nginx configuration
log_test "Kontrola nginx konfigurace..."
if command -v docker &> /dev/null; then
    if docker compose -f "$(dirname "$SSL_DIR")/docker-compose.prod.yml" config -q 2>/dev/null; then
        log_info "docker-compose.prod.yml je validní"
    else
        log_warn "docker-compose.prod.yml má chyby (nebo není dostupný)"
    fi

    # Check if nginx is running
    if docker ps --format '{{.Names}}' | grep -q nginx; then
        log_info "Nginx container běží"

        # Test nginx config inside container
        if docker compose -f "$(dirname "$SSL_DIR")/docker-compose.prod.yml" exec -T nginx nginx -t &> /dev/null; then
            log_info "Nginx konfigurace je validní"
        else
            log_error "Nginx konfigurace má chyby!"
            docker compose -f "$(dirname "$SSL_DIR")/docker-compose.prod.yml" exec -T nginx nginx -t
        fi
    else
        log_warn "Nginx container neběží"
    fi
else
    log_warn "Docker není dostupný"
fi

# 5. Test HTTPS connection (if domain is accessible)
log_test "Test HTTPS připojení k $DOMAIN..."
if [ "$DOMAIN" = "localhost" ] || [ "$DOMAIN" = "127.0.0.1" ]; then
    PORT=443
    if nc -z "$DOMAIN" "$PORT" 2>/dev/null; then
        log_info "Port $PORT je otevřený"

        # Test SSL handshake
        if timeout 5 openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" </dev/null 2>&1 | grep -q "Verify return code: 0"; then
            log_info "SSL handshake úspěšný"
        else
            log_warn "SSL handshake selhal (očekávané pro self-signed certifikát)"
        fi
    else
        log_warn "Port $PORT není dostupný (nginx možná neběží)"
    fi
else
    # External domain
    if timeout 5 curl -sI "https://$DOMAIN" &>/dev/null; then
        log_info "HTTPS spojení k $DOMAIN úspěšné"

        # Check SSL Labs grade (if curl is available)
        log_test "Pro detailní SSL test navštiv:"
        echo "  https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
    else
        log_warn "HTTPS spojení k $DOMAIN selhalo"
        log_warn "Zkontroluj DNS a firewall"
    fi
fi

# 6. Check security headers
log_test "Kontrola bezpečnostních headers..."
if [ "$DOMAIN" = "localhost" ] || [ "$DOMAIN" = "127.0.0.1" ]; then
    if nc -z "$DOMAIN" 443 2>/dev/null; then
        HEADERS=$(timeout 5 curl -sI "https://$DOMAIN" --insecure 2>/dev/null || echo "")

        if echo "$HEADERS" | grep -q "Strict-Transport-Security"; then
            log_info "HSTS header nalezen"
        else
            log_warn "HSTS header chybí"
        fi

        if echo "$HEADERS" | grep -q "X-Frame-Options"; then
            log_info "X-Frame-Options header nalezen"
        else
            log_warn "X-Frame-Options header chybí"
        fi

        if echo "$HEADERS" | grep -q "X-Content-Type-Options"; then
            log_info "X-Content-Type-Options header nalezen"
        else
            log_warn "X-Content-Type-Options header chybí"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "  Test dokončen"
echo "=========================================="
echo ""

# Summary
if [ "$DAYS_UNTIL_EXPIRY" -lt 30 ]; then
    log_warn "DOPORUČENÍ: Obnov certifikát brzy!"
    echo "  ./scripts/setup-ssl.sh --renew"
fi

log_info "Pro více informací viz:"
echo "  - docs/security.md"
echo "  - docker/nginx/ssl/README.md"
echo ""

exit 0
