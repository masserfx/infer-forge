# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekt

**inferbox** — automatizační platforma pro strojírenskou firmu Infer s.r.o. (IČO: 04856562). Firma vyrábí potrubní díly, svařence, ocelové konstrukce a provádí montáže průmyslových zařízení. Certifikace ISO 9001:2016.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Celery + Redis, Alembic migrace
- **Database:** PostgreSQL 16 + pgvector (embedding vyhledávání)
- **Frontend:** Next.js 16 (App Router), TypeScript strict, Tailwind CSS 4, shadcn/ui, TanStack Query, lucide-react
- **Integrace:** Pohoda XML API (Windows-1250, XSD 2.0), IMAP/SMTP, openpyxl, Tesseract OCR
- **AI:** Anthropic Claude API, LangChain, sentence-transformers (multilingual pro češtinu)
- **Deploy:** Docker Compose, on-premise (citlivá data zákazníků nesmí do cloudu)

## Architektura

```
infer-forge/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpointy (/zakazky, /kalkulace, /dokumenty, /pohoda, /inbox, /gamifikace)
│   │   ├── agents/          # AI agenti (email klasifikace, parser, kalkulace)
│   │   ├── integrations/    # Pohoda XML, IMAP/SMTP, Excel, OCR
│   │   ├── models/          # SQLAlchemy modely (12 tabulek)
│   │   ├── schemas/         # Pydantic request/response schémata
│   │   ├── services/        # Business logika (order, calculation, gamification, reporting...)
│   │   └── core/            # Config, security, DB, Celery, logging, health, metrics
│   ├── alembic/             # Migrace (3 revize: init → embeddings → user_points)
│   └── tests/unit/          # 381 testů, 68% coverage
├── frontend/
│   ├── src/
│   │   ├── app/             # 15 routes: /dashboard, /zakazky/[id], /kalkulace/[id], /kanban, /zebricek...
│   │   ├── components/      # React komponenty (ui, layout, zakazky, inbox, kanban, gamification)
│   │   ├── lib/             # API client, utils, providers
│   │   └── types/           # TypeScript typy
│   └── e2e/                 # 8 Playwright E2E testů (auth, dashboard, orders, kanban, leaderboard, navigation)
├── docker/                  # Nginx, Prometheus, Grafana konfigurace
├── docs/                    # PRD (INFER_FORGE_PRD_v1.0.md)
├── screenshots/             # Browser screenshoty všech 12 stránek
├── scripts/                 # Backup, restore, health-check, CORS test
├── docker-compose.prod.yml  # 8 služeb: db, redis, backend, celery-worker, celery-beat, frontend, prometheus, grafana
└── docker-compose.yml       # Dev stack
```

## Příkazy pro vývoj

```bash
# Spuštění infrastruktury
docker compose up -d db redis

# Backend
cd backend && uv run uvicorn app.main:app --reload --port 8000
uv run pytest                              # všechny testy
uv run pytest tests/unit/test_foo.py -k "test_name"  # jeden test
uv run ruff check .                        # lint
uv run mypy .                              # type check
uv run alembic upgrade head                # migrace
uv run alembic revision --autogenerate -m "popis"  # nová migrace

# Frontend
cd frontend && npm run dev                 # dev server (port 3000)
npm run lint                               # ESLint
npm run test                               # Vitest
npm run build                              # production build

# Celery worker
uv run celery -A app.core.celery_app worker -l info

# Celý stack přes Docker
docker compose up --build
```

## Konvence kódu

- **Python:** ruff formátování, mypy strict, pytest, Google-style docstringy
- **TypeScript:** strict mode, ESLint, Prettier, žádný `any`
- **Commity:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- **Branchování:** `main` → `develop` → `feature/xxx`
- **Jazyk:** UI texty a zákaznická komunikace ČESKY, komentáře v kódu anglicky
- **Každá DB operace:** audit trail (`user_id`, `timestamp`, `action`, `entity`)
- **ISO 9001:** verzování všech dokumentů, trasovatelnost

## Pohoda XML integrace

Kritické detaily pro komunikaci s účetním systémem Pohoda (Stormware):
- Kódování **Windows-1250** (nikdy UTF-8)
- XML obaleno v `dat:dataPack version="2.0"`, `ico="04856562"`, `application="INFER_FORGE"`
- Typy dokladů: nabídka (`ofr:offer`), objednávka (`ord:order`), faktura (`inv:invoice`), adresář (`adb:addressbook`)
- Vždy validuj XML proti XSD schématu před odesláním
- Datum formát: `YYYY-MM-DD`, čísla dokladů s unikátním prefixem

## Doménový slovník

| Zkratka | Význam |
|---------|--------|
| BOM | Bill of Materials (kusovník) |
| NDT | Nedestruktivní testování |
| WPS | Welding Procedure Specification |
| DN/PN | Diameter/Pressure Nominal (jmenovitý průměr/tlak) |
| Průvodka | Výrobní průvodní list zakázky |
| Atestace | Materiálový certifikát dle EN 10-204 |

## Subagenti (.claude/agents/)

| Agent | Role | Model |
|-------|------|-------|
| **kovář** | Product lead, architektura, code review, plánování | opus |
| **ocel** | Backend (Python, FastAPI, SQLAlchemy) | sonnet |
| **spojka** | Integrace (Pohoda XML, email, Excel, OCR) | sonnet |
| **neuron** | AI/ML (klasifikace, RAG, extrakce dat) | opus |
| **forma** | Frontend (Next.js, TypeScript, Tailwind) | sonnet |
| **kontrola** | QA & DevOps (testy, Docker, CI/CD) | sonnet |

## Slash commands (.claude/commands/)

- `/plan` — analýza požadavku, implementační specifikace
- `/implement` — implementace s delegací na subagenty
- `/review` — code review (typy, testy, bezpečnost, audit trail, ISO)
- `/status` — stav projektu, testy, coverage, progres dle PRD fází F0-F6
- `/pohoda-test` — test Pohoda XML integrace proti XSD
