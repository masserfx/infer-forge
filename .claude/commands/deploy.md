Deploy na produkční server (Hetzner): $ARGUMENTS

Proveď kompletní deployment pipeline v tomto pořadí:

## 1. Pre-flight kontroly (lokálně)
- `git status` — ověř, že nejsou uncommitted změny (pokud jsou, zeptej se uživatele zda commitnout)
- `git log --oneline -1` — zobraz poslední commit
- Pokud uživatel zadal argument "skip-tests", přeskoč testy. Jinak:
  - `cd backend && uv run pytest tests/ -x -q` — backend testy musí projít
  - `cd frontend && npm run build` — frontend build musí projít

## 2. Commit + Push (pokud jsou změny)
- Pokud jsou unstaged/staged změny:
  - Analyzuj diff a vytvoř Conventional Commit zprávu
  - `git add` relevantní soubory (ne .env, credentials)
  - `git commit` s popisnou zprávou + Co-Authored-By
  - `git push origin main`
- Pokud nejsou změny, přeskoč na krok 3

## 3. Deploy na server
Spoj se na server přes `ssh hetzner-root` a proveď:

```bash
# Proměnné
PROJ_DIR=/home/leos/inferbox
COMPOSE="docker compose -f docker-compose.prod.yml"

# Pull
cd $PROJ_DIR && git pull origin main

# Build pouze změněných služeb
$COMPOSE build backend frontend

# Restart služeb (zero-downtime: backend a frontend se restartují, db/redis zůstávají)
$COMPOSE up -d backend frontend celery-worker celery-beat

# Alembic migrace
$COMPOSE exec backend alembic upgrade head

# Počkej na zdraví kontejnerů
sleep 5
```

## 4. Smoke testy na serveru
Po deployi ověř přes SSH:

```bash
# Backend health
curl -sf http://localhost:8000/health || echo "FAIL: backend health"

# API response
curl -sf http://localhost:8000/api/v1/orchestrace/stats | python3 -m json.tool | head -5

# Frontend response
curl -sf http://localhost:3000 -o /dev/null && echo "OK: frontend" || echo "FAIL: frontend"

# Container status
docker ps --format "table {{.Names}}\t{{.Status}}" | grep inferbox
```

## 5. Výstup
Na konci zobraz přehledný report:
- Který commit byl deploynut (hash + message)
- Které služby byly restartovány
- Zda migrace proběhla
- Výsledky smoke testů (OK/FAIL)
- Upozornění na EMAIL_SENDING_ENABLED a IMAP_POLLING_ENABLED (safety switche)

## Důležité bezpečnostní pravidla
- NIKDY nerestartuj db nebo redis (ztráta dat)
- NIKDY nemaž volumes
- Pokud build selže, NERESTARTUJ kontejnery — ohlás chybu
- Pokud migrace selže, proveď `alembic downgrade -1` a ohlás
- Vždy kontroluj, že EMAIL_SENDING_ENABLED=false a IMAP_POLLING_ENABLED=false (pokud uživatel explicitně neřekne jinak)
