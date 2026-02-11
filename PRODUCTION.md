# inferbox - Produkční Quick Start

Rychlý návod pro spuštění produkční verze **inferbox**.

## Rychlé spuštění (Local testing)

```bash
# 1. Zkopíruj a uprav environment
cp .env.prod.example .env.prod

# 2. Vygeneruj bezpečná hesla
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))" >> .env.prod
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_hex(32))" >> .env.prod
python3 -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_hex(32))" >> .env.prod

# 3. Uprav .env.prod s reálnými hodnotami
nano .env.prod

# 4. Spusť produkční stack
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 5. Sleduj logy
docker compose -f docker-compose.prod.yml logs -f

# 6. Spusť migrace
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 7. Ověř health check
curl http://localhost:8000/health
```

## Minimální konfigurace pro testování

V `.env.prod` minimálně nastav:

```bash
# Database
POSTGRES_DB=infer_forge
POSTGRES_USER=infer
POSTGRES_PASSWORD=<vygenerované-heslo>

# Redis
REDIS_PASSWORD=<vygenerované-heslo>

# Application
SECRET_KEY=<vygenerované-heslo>
CORS_ORIGINS=http://localhost:3000

# Volitelné (můžeš nechat prázdné pro testing)
ANTHROPIC_API_KEY=
SENTRY_DSN=
```

## Správa služeb

```bash
# Zastavení všech služeb
docker compose -f docker-compose.prod.yml down

# Restart konkrétní služby
docker compose -f docker-compose.prod.yml restart backend

# Rebuild po změně kódu
docker compose -f docker-compose.prod.yml up -d --build

# Sledování logů
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f celery-worker

# Status služeb
docker compose -f docker-compose.prod.yml ps
```

## Přístup k službám

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/api/docs (pouze pokud DEBUG=true)
- **Health Check:** http://localhost:8000/health

## Databázové operace

```bash
# Připojení do PostgreSQL
docker compose -f docker-compose.prod.yml exec db psql -U infer -d infer_forge

# Vytvoření nové migrace
docker compose -f docker-compose.prod.yml exec backend alembic revision --autogenerate -m "popis"

# Spuštění migrací
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Rollback migrace
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1

# Aktuální revize
docker compose -f docker-compose.prod.yml exec backend alembic current
```

## Backup & Restore

```bash
# Backup databáze
docker compose -f docker-compose.prod.yml exec db pg_dump -U infer infer_forge > backup.sql

# Restore databáze
docker compose -f docker-compose.prod.yml exec -T db psql -U infer infer_forge < backup.sql

# Backup Docker volumes
docker run --rm \
  -v infer-forge_pgdata:/data \
  -v $(pwd):/backup \
  alpine tar -czf /backup/pgdata_backup.tar.gz -C /data .
```

## Monitoring

```bash
# CPU & Memory usage
docker stats

# Disk usage
docker system df

# Detailní info o containeru
docker compose -f docker-compose.prod.yml exec backend ps aux
docker compose -f docker-compose.prod.yml exec backend df -h
```

## Řešení problémů

### Port již používán

```bash
# Zjisti, co běží na portu
sudo lsof -i :8000
sudo lsof -i :3000
sudo lsof -i :5432

# Případně změň porty v docker-compose.prod.yml
```

### Databáze se nepřipojí

```bash
# Ověř, že DB container běží
docker compose -f docker-compose.prod.yml ps db

# Sleduj DB logy
docker compose -f docker-compose.prod.yml logs db

# Ověř připojení
docker compose -f docker-compose.prod.yml exec db pg_isready -U infer
```

### Redis nereaguje

```bash
# Test připojení
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping

# Mělo by vrátit: PONG
```

### Celery worker neběží

```bash
# Ověř worker status
docker compose -f docker-compose.prod.yml exec celery-worker celery -A app.core.celery_app inspect active

# Restart workeru
docker compose -f docker-compose.prod.yml restart celery-worker
```

## Úplné vyčištění (reset)

```bash
# VAROVÁNÍ: Smaže všechna data!

# Zastavení a smazání containers + volumes
docker compose -f docker-compose.prod.yml down -v

# Smazání images
docker compose -f docker-compose.prod.yml down --rmi all

# Smazání všech Docker dat (use with caution!)
docker system prune -a --volumes
```

## Produkční deployment

Pro plný produkční deployment (server, SSL, Nginx, backupy) viz:

📖 **[docs/deployment.md](./docs/deployment.md)**

## Bezpečnostní upozornění

- **NIKDY** nepoužívej výchozí hesla v produkci
- **NIKDY** necommituj `.env.prod` do Git
- **VŽDY** používej HTTPS v produkci
- **VŽDY** nastavuj správné CORS_ORIGINS (ne `*`)
- **PRAVIDELNĚ** aktualizuj dependencies a Docker images

---

**Další kroky:**
1. Konfigurace Pohoda XML integrace (viz `docs/pohoda-integration.md`)
2. Nastavení email účtů pro IMAP/SMTP
3. Integrace Anthropic Claude API
4. Konfigurace Sentry monitoringu
