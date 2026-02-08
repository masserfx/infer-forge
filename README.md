# INFER FORGE

Automatizační platforma pro strojírenskou firmu Infer s.r.o. (IČO: 04856562).

## O projektu

INFER FORGE automatizuje klíčové procesy strojírenské firmy Infer s.r.o., která se specializuje na výrobu potrubních dílů, svařenců, ocelových konstrukcí a montáže průmyslových zařízení. Systém je certifikován dle ISO 9001:2016.

### Hlavní funkce

- **Automatizace emailové komunikace** - AI klasifikace a zpracování
- **Správa zakázek a nabídek** - kompletní lifecycle od poptávky po fakturu
- **Integrace s Pohoda** - automatické generování XML dokladů (Windows-1250, XSD 2.0)
- **Kalkulace a materiálové plánování** - BOM, atestace, průvodní listy
- **RAG dokumentace** - vektorové vyhledávání technických dokumentů
- **ISO 9001 compliance** - audit trail, verzování, trasovatelnost

## Tech Stack

### Backend
- Python 3.12, FastAPI, SQLAlchemy 2.0 (async)
- PostgreSQL 16 + pgvector
- Celery + Redis
- Anthropic Claude API, LangChain

### Frontend
- Next.js 14 (App Router), TypeScript strict
- Tailwind CSS, shadcn/ui
- TanStack Query

### Deployment
- Docker Compose
- On-premise (citlivá zákaznická data)

## Quick Start

### Development

```bash
# Spuštění infrastruktury (PostgreSQL + Redis)
docker compose up -d db redis

# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Testy
cd backend && uv run pytest
cd frontend && npm test
```

### Production

```bash
# Quick start pro produkční testing
cp .env.prod.example .env.prod
# Uprav .env.prod s reálnými hodnotami

# Spuštění celého stacku
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Migrace
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Health check
curl http://localhost:8000/health
```

Detailní návod viz **[PRODUCTION.md](./PRODUCTION.md)** a **[docs/deployment.md](./docs/deployment.md)**.

## Dokumentace

- **[CLAUDE.md](./CLAUDE.md)** - Instrukce pro Claude Code (architektura, konvence)
- **[PRODUCTION.md](./PRODUCTION.md)** - Quick start pro produkční deployment
- **[docs/deployment.md](./docs/deployment.md)** - Kompletní deployment guide (SSL, Nginx, backupy)
- **[docs/INFER_FORGE_PRD_v1.0.md](./docs/INFER_FORGE_PRD_v1.0.md)** - Product Requirements Document

### API dokumentace

- Backend README: [backend/README.md](./backend/README.md)
- Frontend README: [frontend/README.md](./frontend/README.md)
- Pohoda integrace: [backend/app/integrations/pohoda/README.md](./backend/app/integrations/pohoda/README.md)
- Email integrace: [backend/app/integrations/email/README.md](./backend/app/integrations/email/README.md)

## Struktura projektu

```
infer-forge/
├── backend/             # FastAPI backend
│   ├── app/
│   │   ├── api/v1/     # REST endpointy
│   │   ├── agents/     # AI agenti
│   │   ├── integrations/ # Pohoda, email, Excel, OCR
│   │   ├── models/     # SQLAlchemy modely
│   │   └── core/       # Config, DB, Celery
│   ├── tests/          # pytest testy
│   └── Dockerfile
├── frontend/           # Next.js frontend
│   ├── src/
│   │   ├── app/        # App Router
│   │   ├── components/ # React komponenty
│   │   └── lib/        # API client, utils
│   └── Dockerfile
├── docs/               # Dokumentace
├── docker-compose.yml  # Dev prostředí
└── docker-compose.prod.yml  # Produkční stack
```

## Vývoj

### Git workflow

```bash
git checkout -b feature/nazev-funkce
# ... implementace ...
git commit -m "feat: popis změny"
git push origin feature/nazev-funkce
# Vytvoř Pull Request
```

Používáme **Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`

### Testing

```bash
# Backend (pytest)
cd backend
uv run pytest                           # všechny testy
uv run pytest tests/unit/test_foo.py    # konkrétní soubor
uv run pytest -k "test_name"            # konkrétní test
uv run pytest --cov                     # s coverage

# Frontend (Vitest)
cd frontend
npm test                                # všechny testy
npm test -- calculator                  # konkrétní test
npm run test:ui                         # UI mode
```

### Linting & Type checking

```bash
# Backend
uv run ruff check .                    # lint
uv run ruff format .                   # formátování
uv run mypy .                          # type check

# Frontend
npm run lint                           # ESLint
npm run type-check                     # TypeScript
```

### Database migrace

```bash
cd backend

# Vytvoření nové migrace
uv run alembic revision --autogenerate -m "popis změny"

# Spuštění migrací
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1

# Aktuální verze
uv run alembic current
```

## Environment Variables

### Development (.env)

```bash
DATABASE_URL=postgresql+asyncpg://infer:infer@localhost:5432/infer_forge
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev_secret_key_change_in_production
ANTHROPIC_API_KEY=sk-ant-...
```

### Production (.env.prod)

Viz **[.env.prod.example](./.env.prod.example)** pro kompletní seznam.

Kritické proměnné:
- `POSTGRES_PASSWORD` - silné heslo (min. 32 znaků)
- `REDIS_PASSWORD` - silné heslo
- `SECRET_KEY` - random 64 znaků (viz `python -c "import secrets; print(secrets.token_urlsafe(64))"`)
- `CORS_ORIGINS` - produkční domény (např. `https://infer-forge.example.com`)

## Bezpečnost

- ✅ HTTPS/SSL v produkci
- ✅ CORS ochrana (konfiguruj `CORS_ORIGINS`)
- ✅ Rate limiting na API
- ✅ JWT autentizace
- ✅ SQL injection ochrana (SQLAlchemy ORM)
- ✅ XSS ochrana (React auto-escaping)
- ✅ RBAC (Role-Based Access Control)
- ✅ Audit trail všech operací
- ✅ AES-256 šifrování citlivých dat
- ✅ Denní automatické backupy

## Monitoring

### Health checks

```bash
# Kompletní health check
curl http://localhost:8000/health

# Pouze DB
curl http://localhost:8000/health/db

# Pouze Redis
curl http://localhost:8000/health/redis
```

### Logs

```bash
# Development (strukturované logy)
cd backend && uv run uvicorn app.main:app --reload

# Production (Docker)
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f celery-worker

# Backup logs
tail -f /var/log/infer-forge-backup.log
```

### Sentry (volitelné)

Nastav `SENTRY_DSN` v `.env.prod` pro error tracking.

## Zálohovací Systém

Automatické denní a týdenní zálohy databáze PostgreSQL a nahraných souborů.

### Quick Start

```bash
# Instalace automatických záloh (na produkčním serveru)
sudo ./scripts/backup-cron.sh

# Manuální záloha
./scripts/backup_db.sh              # denní záloha
./scripts/backup_db.sh --weekly     # týdenní záloha

# Obnovení ze zálohy
./scripts/restore_db.sh /opt/infer-forge/backups/infer-forge-backup-*.sql.gz
```

### Retention Policy

- **Denní zálohy:** Každý den v 2:00 (retention 7 dní)
- **Týdenní zálohy:** Každou neděli ve 3:00 (retention 90 dní)
- **Umístění:** `/opt/infer-forge/backups/`
- **Logy:** `/var/log/infer-forge-backup.log`

### Dokumentace

- **[docs/BACKUP_SYSTEM.md](./docs/BACKUP_SYSTEM.md)** - Kompletní dokumentace backup systému
- **[docs/DEPLOYMENT_BACKUP.md](./docs/DEPLOYMENT_BACKUP.md)** - Instalační návod pro produkční server
- **[scripts/README.md](./scripts/README.md)** - Přehled utility skriptů

## Pohoda XML integrace

Kritické detaily pro komunikaci s účetním systémem Stormware Pohoda:

- **Kódování:** Windows-1250 (NIKDY UTF-8)
- **XML verze:** 2.0
- **IČO:** 04856562 (hardcoded pro Infer s.r.o.)
- **Validace:** XSD schémata před odesláním

Viz [backend/app/integrations/pohoda/README.md](./backend/app/integrations/pohoda/README.md)

## Podpora

- **Technická dokumentace:** `/docs`
- **API dokumentace:** http://localhost:8000/api/docs (development)
- **Issues:** GitHub Issues
- **Email:** dev@infer.cz

## Licence

Proprietární software pro Infer s.r.o.

## Authors

Vyvíjeno s Claude Code (claude.ai/code) pomocí subagentů:
- **kovář** (Product lead, architektura)
- **ocel** (Backend)
- **spojka** (Integrace)
- **neuron** (AI/ML)
- **forma** (Frontend)
- **kontrola** (QA & DevOps)

---

**INFER FORGE** - Automatizace pro moderní strojírenství
