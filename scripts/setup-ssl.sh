#!/bin/bash
# SSL/TLS Certificate Setup Script for inferbox
# Usage:
#   ./scripts/setup-ssl.sh --self-signed              # Generate self-signed cert for dev/testing
#   ./scripts/setup-ssl.sh --letsencrypt example.com  # Get Let's Encrypt cert for production

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSL_DIR="$PROJECT_ROOT/docker/nginx/ssl"
CERTBOT_DATA="$PROJECT_ROOT/docker/certbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Ensure SSL directory exists
mkdir -p "$SSL_DIR"
mkdir -p "$CERTBOT_DATA"

generate_self_signed() {
    log_info "Generuji self-signed SSL certifikát..."

    # Remove old certificates
    rm -f "$SSL_DIR/cert.pem" "$SSL_DIR/key.pem"

    # Generate new self-signed certificate (valid 365 days)
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/key.pem" \
        -out "$SSL_DIR/cert.pem" \
        -subj "/C=CZ/ST=Czech Republic/L=Prague/O=Infer s.r.o./OU=IT/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1,IP:91.99.126.53"

    chmod 600 "$SSL_DIR/key.pem"
    chmod 644 "$SSL_DIR/cert.pem"

    log_info "Self-signed certifikát vytvořen:"
    log_info "  Cert: $SSL_DIR/cert.pem"
    log_info "  Key:  $SSL_DIR/key.pem"
    log_warn "POZOR: Self-signed certifikát není důvěryhodný pro produkci!"
    log_warn "Pro produkci použij: ./scripts/setup-ssl.sh --letsencrypt DOMAIN"
}

setup_letsencrypt() {
    local DOMAIN="$1"

    if [ -z "$DOMAIN" ]; then
        log_error "Musíš zadat doménu!"
        echo "Usage: $0 --letsencrypt example.com"
        exit 1
    fi

    log_info "Nastavuji Let's Encrypt certifikát pro doménu: $DOMAIN"

    # Check if docker and docker-compose are available
    if ! command -v docker &> /dev/null; then
        log_error "Docker není nainstalován!"
        exit 1
    fi

    # Create webroot directory for ACME challenge
    mkdir -p "$CERTBOT_DATA/www"

    log_info "Spouštím certbot pro získání certifikátu..."
    log_warn "Ujisti se, že:"
    log_warn "  1. Doména $DOMAIN směřuje na tento server (91.99.126.53)"
    log_warn "  2. Port 80 je otevřený a dostupný z internetu"
    log_warn "  3. Nginx běží a má přístup k /.well-known/acme-challenge/"

    read -p "Pokračovat? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Přerušeno uživatelem."
        exit 0
    fi

    # Run certbot in Docker
    docker run --rm \
        -v "$CERTBOT_DATA/etc:/etc/letsencrypt" \
        -v "$CERTBOT_DATA/www:/var/www/certbot" \
        -v "$CERTBOT_DATA/log:/var/log/letsencrypt" \
        certbot/certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "admin@${DOMAIN}" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN"

    # Copy certificates to nginx ssl directory
    if [ -f "$CERTBOT_DATA/etc/live/$DOMAIN/fullchain.pem" ]; then
        cp "$CERTBOT_DATA/etc/live/$DOMAIN/fullchain.pem" "$SSL_DIR/cert.pem"
        cp "$CERTBOT_DATA/etc/live/$DOMAIN/privkey.pem" "$SSL_DIR/key.pem"
        chmod 600 "$SSL_DIR/key.pem"
        chmod 644 "$SSL_DIR/cert.pem"

        log_info "Let's Encrypt certifikát úspěšně nainstalován!"
        log_info "  Cert: $SSL_DIR/cert.pem"
        log_info "  Key:  $SSL_DIR/key.pem"
        log_info ""
        log_info "Nyní restartuj nginx:"
        log_info "  docker compose -f docker-compose.prod.yml restart nginx"
        log_info ""
        log_info "Pro automatické obnovování certifikátu (každých 12h) použij:"
        log_info "  docker compose -f docker-compose.prod.yml up -d certbot"
    else
        log_error "Certbot selhal! Zkontroluj logy:"
        log_error "  $CERTBOT_DATA/log/"
        exit 1
    fi
}

renew_letsencrypt() {
    log_info "Obnovuji Let's Encrypt certifikát..."

    docker run --rm \
        -v "$CERTBOT_DATA/etc:/etc/letsencrypt" \
        -v "$CERTBOT_DATA/www:/var/www/certbot" \
        -v "$CERTBOT_DATA/log:/var/log/letsencrypt" \
        certbot/certbot renew

    # Find the most recent certificate and copy to nginx
    LATEST_CERT=$(find "$CERTBOT_DATA/etc/live" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    if [ -n "$LATEST_CERT" ] && [ -f "$LATEST_CERT/fullchain.pem" ]; then
        cp "$LATEST_CERT/fullchain.pem" "$SSL_DIR/cert.pem"
        cp "$LATEST_CERT/privkey.pem" "$SSL_DIR/key.pem"
        chmod 600 "$SSL_DIR/key.pem"
        chmod 644 "$SSL_DIR/cert.pem"

        log_info "Certifikát obnoven. Restartuj nginx:"
        log_info "  docker compose -f docker-compose.prod.yml restart nginx"
    fi
}

show_usage() {
    cat << EOF
SSL/TLS Setup Script pro inferbox

Usage:
  $0 --self-signed                  # Vygeneruje self-signed certifikát pro dev/testing
  $0 --letsencrypt DOMAIN          # Získá Let's Encrypt certifikát pro produkci
  $0 --renew                       # Obnoví existující Let's Encrypt certifikát

Příklady:
  # Development (self-signed)
  $0 --self-signed

  # Production (Let's Encrypt)
  $0 --letsencrypt forge.infer.cz

  # Obnovení certifikátu
  $0 --renew

Poznámky:
  - Self-signed certifikáty jsou pouze pro dev/testing
  - Let's Encrypt vyžaduje:
    * Platnou doménu směřující na tento server
    * Otevřený port 80 (HTTP) pro ACME challenge
    * Běžící nginx s konfigurací pro /.well-known/acme-challenge/
  - Certifikáty jsou uloženy v: $SSL_DIR/
EOF
}

# Main
case "${1:-}" in
    --self-signed)
        generate_self_signed
        ;;
    --letsencrypt)
        setup_letsencrypt "${2:-}"
        ;;
    --renew)
        renew_letsencrypt
        ;;
    -h|--help)
        show_usage
        ;;
    *)
        log_error "Neznámá volba: ${1:-}"
        echo ""
        show_usage
        exit 1
        ;;
esac

exit 0
