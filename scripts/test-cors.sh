#!/bin/bash
# Test CORS konfigurace pro různé původy

set -e

BACKEND_URL="${1:-http://localhost:8000}"

echo "=== CORS Test ==="
echo "Backend URL: $BACKEND_URL"
echo ""

# Funkce pro test CORS
test_cors() {
    local origin=$1
    local expected=$2

    echo "Testing origin: $origin"

    response=$(curl -s -I \
        -H "Origin: $origin" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type" \
        -X OPTIONS \
        "$BACKEND_URL/health")

    cors_header=$(echo "$response" | grep -i "access-control-allow-origin" || echo "")

    if [[ -n "$cors_header" ]]; then
        echo "  ✅ CORS allowed"
        echo "  Header: $cors_header"
    else
        echo "  ❌ CORS blocked"
    fi

    echo ""
}

# Test případy
echo "1. Povolený origin (localhost:3000)"
test_cors "http://localhost:3000" "allowed"

echo "2. Nepovolený origin"
test_cors "http://evil.com" "blocked"

echo "3. Produkční doména (pokud nastaveno)"
test_cors "https://infer-forge.example.com" "depends"

echo "=== Test dokončen ==="
echo ""
echo "Pro změnu CORS origins nastav v .env nebo .env.prod:"
echo "  CORS_ORIGINS=http://localhost:3000,https://your-domain.com"
