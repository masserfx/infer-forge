#!/bin/bash
# INFER FORGE Security Audit Script
# Performs comprehensive security checks on Docker stack
# Usage: ./scripts/security-audit.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

print_header() {
    echo -e "\n========================================="
    echo -e "$1"
    echo -e "=========================================\n"
}

print_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
    ((PASS_COUNT++))
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARN_COUNT++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL_COUNT++))
}

print_header "INFER FORGE Security Audit"
echo "Date: $(date)"
echo "Project: $PROJECT_ROOT"

# 1. Python Dependencies Audit
print_header "1. Python Dependencies (pip-audit)"
if docker compose ps backend | grep -q "Up"; then
    if docker compose exec -T backend pip-audit --desc > /dev/null 2>&1; then
        print_ok "No Python dependency vulnerabilities found"
    else
        VULNS=$(docker compose exec -T backend pip-audit --format json 2>/dev/null | grep -c '"name"' || echo "0")
        if [ "$VULNS" -gt 0 ]; then
            print_fail "Found $VULNS Python dependency vulnerabilities (run 'docker compose exec backend pip-audit' for details)"
        else
            print_warn "pip-audit check failed (check if pip-audit is installed)"
        fi
    fi
else
    print_warn "Backend container not running, skipping pip-audit"
fi

# 2. Node Dependencies Audit
print_header "2. Node.js Dependencies (npm audit)"
if docker compose ps frontend | grep -q "Up"; then
    AUDIT_OUTPUT=$(docker compose exec -T frontend npm audit --json 2>/dev/null || echo '{"error": true}')
    VULNS=$(echo "$AUDIT_OUTPUT" | grep -c '"severity"' || echo "0")
    if [ "$VULNS" -eq 0 ]; then
        print_ok "No Node.js dependency vulnerabilities found"
    else
        HIGH=$(echo "$AUDIT_OUTPUT" | grep -c '"severity": "high"' || echo "0")
        CRITICAL=$(echo "$AUDIT_OUTPUT" | grep -c '"severity": "critical"' || echo "0")
        if [ "$CRITICAL" -gt 0 ] || [ "$HIGH" -gt 0 ]; then
            print_fail "Found $VULNS Node.js vulnerabilities ($CRITICAL critical, $HIGH high)"
        else
            print_warn "Found $VULNS Node.js vulnerabilities (low/moderate severity)"
        fi
    fi
else
    print_warn "Frontend container not running, skipping npm audit"
fi

# 3. Open Ports Check
print_header "3. Open Network Ports"
if command -v ss &> /dev/null; then
    OPEN_PORTS=$(ss -tlnp 2>/dev/null | grep LISTEN | awk '{print $4}' | awk -F: '{print $NF}' | sort -u)
elif command -v netstat &> /dev/null; then
    OPEN_PORTS=$(netstat -tlnp 2>/dev/null | grep LISTEN | awk '{print $4}' | awk -F: '{print $NF}' | sort -u)
else
    print_warn "Neither 'ss' nor 'netstat' available, skipping port check"
    OPEN_PORTS=""
fi

if [ -n "$OPEN_PORTS" ]; then
    echo "Listening ports:"
    echo "$OPEN_PORTS" | while read -r port; do
        case $port in
            22) print_ok "Port $port (SSH)" ;;
            80|443) print_ok "Port $port (HTTP/HTTPS)" ;;
            3000|3001|3002|8000|5432|5433|6379|9090) print_ok "Port $port (INFER FORGE stack)" ;;
            *) print_warn "Port $port (unexpected, verify if needed)" ;;
        esac
    done
fi

# 4. Docker Image Vulnerabilities (if docker scout available)
print_header "4. Docker Image Vulnerabilities"
if command -v docker &> /dev/null && docker scout version &> /dev/null 2>&1; then
    for image in infer-forge-backend infer-forge-frontend; do
        if docker images | grep -q "$image"; then
            SCOUT_OUTPUT=$(docker scout cves "$image" 2>&1 || echo "scan_failed")
            if echo "$SCOUT_OUTPUT" | grep -q "0C.*0H.*0M.*0L"; then
                print_ok "Docker image '$image' has no known CVEs"
            elif echo "$SCOUT_OUTPUT" | grep -q "scan_failed"; then
                print_warn "Docker Scout scan failed for '$image'"
            else
                print_fail "Docker image '$image' has vulnerabilities (run 'docker scout cves $image' for details)"
            fi
        else
            print_warn "Docker image '$image' not found locally"
        fi
    done
else
    print_warn "Docker Scout not available, skipping image CVE scan"
fi

# 5. File Permissions Check
print_header "5. File Permissions"

# Check .env files
if [ -f "backend/.env" ]; then
    PERMS=$(stat -f "%A" backend/.env 2>/dev/null || stat -c "%a" backend/.env 2>/dev/null)
    if [ "$PERMS" == "600" ] || [ "$PERMS" == "400" ]; then
        print_ok "backend/.env has secure permissions ($PERMS)"
    else
        print_fail "backend/.env has insecure permissions ($PERMS, should be 600 or 400)"
    fi
else
    print_warn "backend/.env not found"
fi

if [ -f "frontend/.env" ]; then
    PERMS=$(stat -f "%A" frontend/.env 2>/dev/null || stat -c "%a" frontend/.env 2>/dev/null)
    if [ "$PERMS" == "600" ] || [ "$PERMS" == "400" ]; then
        print_ok "frontend/.env has secure permissions ($PERMS)"
    else
        print_fail "frontend/.env has insecure permissions ($PERMS, should be 600 or 400)"
    fi
else
    print_warn "frontend/.env not found"
fi

# Check SSL certificates (if exist)
if [ -d "docker/nginx/ssl" ]; then
    for cert in docker/nginx/ssl/*.key; do
        if [ -f "$cert" ]; then
            PERMS=$(stat -f "%A" "$cert" 2>/dev/null || stat -c "%a" "$cert" 2>/dev/null)
            if [ "$PERMS" == "600" ] || [ "$PERMS" == "400" ]; then
                print_ok "SSL key $(basename "$cert") has secure permissions ($PERMS)"
            else
                print_fail "SSL key $(basename "$cert") has insecure permissions ($PERMS, should be 600 or 400)"
            fi
        fi
    done
else
    print_warn "SSL certificate directory not found"
fi

# 6. Docker Container Security
print_header "6. Docker Container Security"

# Check if containers are running as non-root
for container in $(docker compose ps -q backend frontend 2>/dev/null); do
    CONTAINER_NAME=$(docker inspect --format '{{.Name}}' "$container" | sed 's/\///')
    USER=$(docker inspect --format '{{.Config.User}}' "$container")
    if [ -n "$USER" ] && [ "$USER" != "root" ] && [ "$USER" != "0" ]; then
        print_ok "Container '$CONTAINER_NAME' runs as non-root user ($USER)"
    else
        print_fail "Container '$CONTAINER_NAME' runs as root"
    fi
done

# 7. Secrets in Git Check
print_header "7. Git Secrets Check"
if git rev-parse --git-dir > /dev/null 2>&1; then
    # Check if .env files are in .gitignore
    if git check-ignore backend/.env >/dev/null 2>&1 && git check-ignore frontend/.env >/dev/null 2>&1; then
        print_ok ".env files are properly ignored by git"
    else
        print_fail ".env files are NOT in .gitignore"
    fi

    # Check for accidentally committed secrets
    if git log --all --pretty=format: --name-only | grep -q "\.env$"; then
        print_fail ".env files found in git history (use git filter-branch to remove)"
    else
        print_ok "No .env files found in git history"
    fi
else
    print_warn "Not a git repository, skipping git secrets check"
fi

# 8. Database Backup Check
print_header "8. Database Backup Configuration"
if [ -f "scripts/backup_db.sh" ]; then
    print_ok "Database backup script exists"
    if [ -x "scripts/backup_db.sh" ]; then
        print_ok "Backup script is executable"
    else
        print_warn "Backup script is not executable (run 'chmod +x scripts/backup_db.sh')"
    fi
else
    print_fail "Database backup script not found (expected: scripts/backup_db.sh)"
fi

# Summary
print_header "Security Audit Summary"
TOTAL=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))
echo -e "${GREEN}PASSED:${NC}  $PASS_COUNT / $TOTAL"
echo -e "${YELLOW}WARNINGS:${NC} $WARN_COUNT / $TOTAL"
echo -e "${RED}FAILED:${NC}  $FAIL_COUNT / $TOTAL"

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "\n${RED}Action Required:${NC} Address $FAIL_COUNT critical security issues above."
    exit 1
elif [ "$WARN_COUNT" -gt 0 ]; then
    echo -e "\n${YELLOW}Attention:${NC} Review $WARN_COUNT warnings above."
    exit 0
else
    echo -e "\n${GREEN}All security checks passed!${NC}"
    exit 0
fi
