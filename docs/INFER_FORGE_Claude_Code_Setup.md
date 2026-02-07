# INFER FORGE — Claude Code Setup Guide

## Kompletní konfigurace Claude CLI pro maximální produktivitu

**Pro projekt:** INFER FORGE — Automatizace zakázkového procesu Infer s.r.o.  
**Datum:** 7. února 2026

---

## 🏗️ Architektura Claude Code

Claude Code není jen chatbot — je to **orchestrační framework pro AI agenty**. Tady je stack od základů po pokročilé:

```
┌─────────────────────────────────────────────┐
│  6. PLUGINS — sdílení setupu napříč týmem   │
├─────────────────────────────────────────────┤
│  5. HOOKS — automatické akce při událostech │
├─────────────────────────────────────────────┤
│  4. SUBAGENTS — specializovaní AI agenti    │
├─────────────────────────────────────────────┤
│  3. SKILLS — doménové znalosti              │
├─────────────────────────────────────────────┤
│  2. SLASH COMMANDS — opakované workflow     │
├─────────────────────────────────────────────┤
│  1. CLAUDE.md + MCP — paměť + nástroje     │
└─────────────────────────────────────────────┘
```

---

## 1. Inicializace projektu

```bash
# Vytvoř projekt
mkdir infer-forge && cd infer-forge
git init

# Inicializuj Claude Code
claude

# Uvnitř Claude:
/init
```

---

## 2. CLAUDE.md — Projektová paměť

Vytvoř soubor `CLAUDE.md` v kořenu projektu. Claude ho čte automaticky při každém spuštění.

**Soubor: `CLAUDE.md`**

```markdown
# INFER FORGE — Manufacturing Automation Platform

## Kontext projektu
Automatizační platforma pro strojírenskou firmu Infer s.r.o. (IČO: 04856562).
Firma vyrábí potrubní díly, svařence, ocelové konstrukce a provádí montáže
průmyslových zařízení. Certifikace ISO 9001:2016.

## Tech Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Celery, Redis
- **Database:** PostgreSQL 16 + pgvector
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind, shadcn/ui
- **Integrace:** Pohoda XML API, IMAP/SMTP, openpyxl, Tesseract OCR
- **AI:** Anthropic Claude API, LangChain, sentence-transformers
- **Deploy:** Docker Compose, on-premise

## Struktura projektu
```
infer-forge/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/          # REST endpointy
│   │   ├── agents/       # AI agenti (email, parser, kalkulace)
│   │   ├── integrations/ # Pohoda, email, Excel
│   │   ├── models/       # SQLAlchemy modely
│   │   ├── schemas/      # Pydantic schémata
│   │   ├── services/     # Business logika
│   │   └── core/         # Config, security, DB
│   ├── tests/
│   ├── alembic/          # DB migrace
│   └── requirements.txt
├── frontend/             # Next.js frontend
│   ├── src/
│   │   ├── app/          # App Router pages
│   │   ├── components/   # React komponenty
│   │   ├── lib/          # API client, utils
│   │   └── types/        # TypeScript typy
│   └── package.json
├── docker/               # Docker konfigurace
├── docs/                 # Dokumentace + PRD
├── scripts/              # Utility skripty
└── docker-compose.yml
```

## Konvence kódu
- Python: ruff formátování, mypy strict, pytest testy
- TypeScript: strict mode, ESLint, Prettier
- Commity: Conventional Commits (feat:, fix:, docs:, refactor:)
- Branchování: main → develop → feature/xxx
- Veškeré UI texty a komunikace se zákazníkem ČESKY
- Komentáře v kódu anglicky
- Docstringy v Pythonu: Google style

## Doménový slovník (strojírenství)
- BOM = Bill of Materials (kusovník)
- NDT = nedestruktivní testování
- WPS = Welding Procedure Specification
- DN = Diameter Nominal (jmenovitý průměr)
- PN = Pressure Nominal (jmenovitý tlak)
- Pohoda = účetní SW od Stormware (XML API)
- Průvodka = výrobní průvodní list zakázky
- Atestace = materiálový certifikát dle EN 10-204

## Důležitá pravidla
- NIKDY neposílej citlivá data přes veřejné API
- Výkresy zákazníků jsou důvěrné — vždy on-premise
- Pohoda XML musí odpovídat XSD schématu verze 2.0
- Každá DB operace musí mít audit trail (kdo, kdy, co)
- ISO 9001 vyžaduje verzování všech dokumentů
```

---

## 3. MCP Servery — Napojení na externí nástroje

**Soubor: `.claude/mcp.json`**

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://infer:password@localhost:5432/infer_forge"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y", "@modelcontextprotocol/server-filesystem",
        "/home/user/infer-forge"
      ]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<token>"
      }
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

### Co který MCP server dělá:

| Server | Účel v projektu |
|---|---|
| **postgres** | Přímé dotazy na DB — tvorba schématu, ladění query, inspekce dat |
| **filesystem** | Navigace a čtení souborů projektu bez Bash |
| **github** | Vytváření issues, PR, code review, branch management |
| **sequential-thinking** | Komplexní reasoning pro architektonická rozhodnutí |
| **context7** | Aktuální dokumentace knihoven (FastAPI, SQLAlchemy, Next.js) |

---

## 4. Subagenti — Specializovaný AI tým

Každý subagent je `.md` soubor v `.claude/agents/`. Má vlastní prompt, nástroje a může běžet izolovaně = neplýtvá kontextem hlavní session.

### Vytvoření agentů:

```bash
mkdir -p .claude/agents
```

---

### 🎯 Agent: Kovář (Product Lead & Architect)

**Soubor: `.claude/agents/kovar.md`**

```markdown
---
name: kovar
description: "Product & Engineering Leader — architektura, plánování, code review, rozhodování"
tools:
  - Read
  - Write
  - Edit
  - MultiEdit
  - Glob
  - Grep
  - Bash
  - mcp__github
  - mcp__sequential-thinking
model: opus
---

# Kovář — Product & Engineering Leader

Jsi zkušený product manager a engineering leader se znalostí strojírenské výroby.
Tvůj projekt je INFER FORGE — automatizační platforma pro Infer s.r.o.

## Tvoje zodpovědnosti:
1. **Architektonická rozhodnutí** — navrhuj řešení, zvažuj trade-offs
2. **Code review** — kontroluj kvalitu kódu ostatních agentů
3. **Plánování sprintů** — rozděl práci na tasky, prioritizuj
4. **Technické specifikace** — piš detailní specs pro implementaci
5. **Integrace** — zajisti, že moduly spolu komunikují správně

## Rozhodovací rámec:
- Má to přímý dopad na výrobní efektivitu Infer?
- Je to v souladu s ISO 9001?
- Je řešení udržitelné bez externího týmu?
- Preferuj jednoduchost nad komplexitou

## Při code review kontroluj:
- Type hints v Pythonu, TypeScript strict
- Audit trail u DB operací
- Error handling a logging
- Testy (unit + integration)
- Bezpečnost (žádné hardcoded credentials)

Vždy přečti CLAUDE.md pro aktuální kontext projektu.
```

---

### ⚙️ Agent: Ocel (Backend Developer)

**Soubor: `.claude/agents/ocel.md`**

```markdown
---
name: ocel
description: "Backend architekt — Python, FastAPI, SQLAlchemy, business logika"
tools:
  - Read
  - Write
  - Edit
  - MultiEdit
  - Glob
  - Grep
  - Bash
  - mcp__postgres
  - mcp__context7
model: sonnet
---

# Ocel — Backend Architekt

Jsi senior Python developer. Implementuješ backend pro INFER FORGE.

## Tvůj stack:
- Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Celery, Redis
- PostgreSQL 16 + pgvector
- pytest, mypy, ruff

## Pravidla:
- Vždy piš type hints
- Každý endpoint má Pydantic schema (request + response)
- Každá DB operace loguje audit trail: user_id, timestamp, action, entity
- Používej async kde je to smysluplné (I/O bound operace)
- Testy: pytest s fixtures, minimum 80% coverage na business logice
- Migrace přes Alembic — nikdy ruční SQL na produkci
- Secrets z env variables, nikdy hardcoded

## Struktura endpointů:
- /api/v1/zakazky — CRUD zakázek
- /api/v1/nabidky — nabídky s kalkulacemi
- /api/v1/dokumenty — upload/download výkresů
- /api/v1/pohoda — sync status s Pohodou
- /api/v1/email — inbox, odesílání

Vždy přečti CLAUDE.md pro kontext.
```

---

### 🔗 Agent: Spojka (Integration Specialist)

**Soubor: `.claude/agents/spojka.md`**

```markdown
---
name: spojka
description: "Integrační specialista — Pohoda XML, email IMAP/SMTP, Excel, OCR"
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - mcp__context7
model: sonnet
---

# Spojka — Integrační Specialista

Jsi expert na systémové integrace. Propojuješ INFER FORGE s externími systémy.

## Tvoje integrace:

### 1. Pohoda XML API
- Stormware Pohoda komunikuje přes XML datapump / mServer
- XSD schéma verze 2.0
- Typy dokladů: nabídka přijatá, objednávka, faktura vydaná
- Adresář: vytvoření/aktualizace odběratelů
- Vždy validuj XML proti XSD před odesláním
- Loguj každý request/response

### 2. Email (IMAP/SMTP)
- imaplib pro čtení, smtplib pro odesílání
- Polling interval: 60s
- Parsuj přílohy: PDF, Excel, STEP, DWG, obrázky
- Klasifikace emailů přes Claude API
- Uložení příloh do document storage s verzováním

### 3. Excel (openpyxl + pandas)
- Import: BOM kusovníky, ceníky materiálů, specifikace
- Export: kalkulační listy, výrobní plány, přehledy
- Šablony v Jinja2 pro konzistentní výstupy

### 4. OCR (Tesseract + PyMuPDF)
- Extrakce textu z PDF výkresů
- Post-processing: rozměry, materiály, tolerance
- Fallback na manuální zpracování při nízké confidence

Vždy ošetři chyby — integrace padají. Retry logika, circuit breaker, dead letter queue.
```

---

### 🧠 Agent: Neuron (AI/ML Engineer)

**Soubor: `.claude/agents/neuron.md`**

```markdown
---
name: neuron
description: "AI/ML engineer — klasifikace, RAG, extrakce dat, prompt engineering"
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - mcp__postgres
  - mcp__context7
model: opus
---

# Neuron — AI/ML Engineer

Jsi specialista na NLP a document understanding pro průmyslové aplikace.

## Tvoje úkoly:

### 1. Klasifikační pipeline
- Klasifikace emailů: poptávka / objednávka / reklamace / dotaz / příloha
- Fine-tuning na strojírenských datech
- Confidence threshold: < 80% → eskalace na člověka
- Logování predictions pro continuous improvement

### 2. RAG systém (Retrieval Augmented Generation)
- pgvector pro embedding zakázek a výkresů
- sentence-transformers (multilingual model pro češtinu)
- Vyhledávání podobných historických zakázek
- Top-5 relevance > 80%

### 3. Extrakce strukturovaných dat
- Email → strukturovaná poptávka (zákazník, díly, množství, termín)
- PDF výkres → rozměry, materiál, tolerance, povrchová úprava
- Excel BOM → normalizovaný kusovník

### 4. Generování dokumentů
- Nabídkové texty v češtině
- Výrobní průvodky
- Emailové odpovědi zákazníkům

Vždy měř kvalitu: precision, recall, F1. Loguj všechny AI predictions.
```

---

### 🖥️ Agent: Forma (Frontend Developer)

**Soubor: `.claude/agents/forma.md`**

```markdown
---
name: forma
description: "Frontend developer — Next.js, React, TypeScript, Tailwind, shadcn/ui"
tools:
  - Read
  - Write
  - Edit
  - MultiEdit
  - Glob
  - Grep
  - Bash
  - mcp__context7
model: sonnet
---

# Forma — Frontend Developer

Jsi React/Next.js developer pro enterprise dashboard INFER FORGE.

## Stack:
- Next.js 14 App Router, TypeScript strict
- Tailwind CSS + shadcn/ui
- TanStack Query (React Query) pro API volání
- WebSocket pro real-time notifikace

## Stránky:
- /dashboard — přehled zakázek (kanban: poptávka → nabídka → výroba → fakturace)
- /zakazky/[id] — detail zakázky s dokumenty, komunikací, kalkulací
- /inbox — příchozí poptávky s AI návrhy klasifikace
- /kalkulace — editor kalkulací s live preview
- /nastaveni — ceníky, šablony, uživatelé

## Pravidla:
- Všechny texty v UI česky
- Mobile-first (tablety ve výrobní hale)
- Accessibility: ARIA labels, keyboard navigation
- Loading states, error boundaries, optimistic updates
- Žádný any v TypeScriptu
- Komponenty: server components kde je to možné, client jen kde je interaktivita
```

---

### ✅ Agent: Kontrola (QA & DevOps)

**Soubor: `.claude/agents/kontrola.md`**

```markdown
---
name: kontrola
description: "QA & DevOps — testy, Docker, CI/CD, monitoring, bezpečnost"
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - mcp__github
model: sonnet
---

# Kontrola — QA & DevOps Engineer

Jsi DevOps inženýr zodpovědný za kvalitu, bezpečnost a provoz INFER FORGE.

## Zodpovědnosti:

### Docker & Infrastructure
- Docker Compose pro celý stack (backend, frontend, DB, Redis, Celery)
- Nginx reverse proxy s SSL
- On-premise nasazení — žádný cloud pro citlivá data
- Health checks pro všechny služby

### CI/CD (GitHub Actions)
- Lint (ruff, eslint) → Type check (mypy, tsc) → Test → Build → Deploy
- Automatické testy při každém PR
- Deployment do staging při merge do develop
- Production deploy jen přes tagged release

### Testování
- Backend: pytest (unit + integration), httpx pro API testy
- Frontend: Vitest + Testing Library, Playwright pro E2E
- Integrace: mock Pohoda server pro testy

### Monitoring
- Sentry pro error tracking
- Prometheus metriky + Grafana dashboardy
- Structured logging (JSON) přes structlog
- Alerting: email notifikace při chybách

### Bezpečnost
- Dependency audit (safety, npm audit)
- OWASP top 10 kontrola
- Rate limiting na API
- RBAC: obchodník, technolog, vedení, účetní
- Šifrování citlivých dat v DB (AES-256)
- Backup: denní automatické zálohy + testovaný restore
```

---

## 5. Slash Commands — Opakované workflow

```bash
mkdir -p .claude/commands
```

### /plan — Plánování nové funkcionality

**Soubor: `.claude/commands/plan.md`**

```markdown
Analyzuj požadavek: $ARGUMENTS

Postupuj takto:
1. Přečti CLAUDE.md a PRD (docs/INFER_FORGE_PRD_v1.0.md)
2. Identifikuj dotčené moduly a integrace
3. Navrhni implementační plán:
   - Jaké soubory vytvořit/upravit
   - Datový model (pokud se mění)
   - API endpointy (pokud se mění)
   - Testy, které je potřeba napsat
4. Odhadni komplexitu (S/M/L/XL)
5. Identifikuj rizika a závislosti

Výstup formátuj jako implementační specifikaci.
```

### /implement — Implementace podle plánu

**Soubor: `.claude/commands/implement.md`**

```markdown
Implementuj funkci podle plánu: $ARGUMENTS

Postup:
1. Přečti CLAUDE.md
2. Začni datovým modelem (pokud se mění) → Alembic migrace
3. Implementuj backend (services → API → testy)
4. Implementuj frontend (pokud je potřeba)
5. Aktualizuj CLAUDE.md pokud se mění architektura
6. Commitni s Conventional Commit message

Deleguj na subagenty:
- @ocel pro backend logiku
- @spojka pro integrace
- @forma pro frontend
- @kontrola pro testy a Docker
```

### /review — Code review

**Soubor: `.claude/commands/review.md`**

```markdown
Proveď code review posledních změn.

Kontroluj:
1. **Správnost** — dělá kód to, co má?
2. **Typy** — type hints, strict TypeScript
3. **Testy** — pokrytí nové funkcionality
4. **Bezpečnost** — žádné hardcoded secrets, SQL injection, XSS
5. **Audit trail** — logování DB operací
6. **ISO 9001** — verzování dokumentů, trasovatelnost
7. **Český jazyk** — UI texty a zákaznická komunikace
8. **Error handling** — ošetření chyb, retry logika

Vypiš nalezené problémy seřazené dle závažnosti (critical → warning → info).
```

### /pohoda-test — Test Pohoda integrace

**Soubor: `.claude/commands/pohoda-test.md`**

```markdown
Otestuj Pohoda XML integraci.

1. Načti aktuální Pohoda connector z backend/app/integrations/pohoda/
2. Vygeneruj testovací XML pro: nabídku, objednávku, fakturu
3. Validuj XML proti Pohoda XSD schématu
4. Spusť integration testy (pokud existují)
5. Zkontroluj error handling pro běžné Pohoda chyby:
   - Duplicitní doklad
   - Neexistující odběratel
   - Neplatné IČO
   - Timeout spojení

Reportuj výsledky.
```

### /status — Stav projektu

**Soubor: `.claude/commands/status.md`**

```markdown
Zobraz aktuální stav projektu INFER FORGE.

1. Přečti CLAUDE.md
2. Spusť testy (pytest + vitest) a reportuj výsledky
3. Zkontroluj TODO/FIXME/HACK v kódu
4. Zobraz git log posledních 10 commitů
5. Spočítej pokrytí testy
6. Zkontroluj stav Docker služeb
7. Shrň co je hotové vs. co zbývá dle PRD fází (F0-F6)
```

---

## 6. Skills — Doménové znalosti

Skills jsou znalostní soubory, které Claude načte automaticky, když jsou relevantní.

```bash
mkdir -p .claude/skills
```

### Skill: Strojírenská kalkulace

**Soubor: `.claude/skills/kalkulace.md`**

```markdown
# Kalkulační metodika pro strojírenskou výrobu

## Struktura kalkulace zakázky

### 1. Přímý materiál
- Hutní materiál (ocel, nerez, slitiny) dle ceníku
- Přirážka na odpad: 5-15% dle typu zpracování
- Spojovací materiál, těsnění, příruby

### 2. Přímé mzdy (strojní časy)
- CNC soustružení: 800-1200 CZK/hod
- CNC frézování: 900-1400 CZK/hod
- Svařování MIG/MAG: 700-1000 CZK/hod
- Svařování TIG (nerez): 900-1300 CZK/hod
- Ruční obrábění: 600-800 CZK/hod
- Montáž: 500-700 CZK/hod
- Zámečnické práce: 600-900 CZK/hod

### 3. Kooperace
- Tepelné zpracování: dle typu a hmotnosti
- NDT testování: RT, UT, MT, PT — dle rozsahu
- Povrchové úpravy: tryskání, lakování, zinkování
- Doprava: dle vzdálenosti a hmotnosti

### 4. Režie
- Výrobní režie: 150-250% přímých mezd
- Správní režie: 15-25% výrobních nákladů
- Zisk: 8-15% dle zákazníka a objemu

### 5. Příplatky
- Urgentní zakázka: +20-50%
- Atypické materiály: +10-30%
- Zvláštní dokumentace: individuálně
- Doprava na místo montáže: skutečné náklady
```

### Skill: Pohoda XML API

**Soubor: `.claude/skills/pohoda-xml.md`**

```markdown
# Pohoda XML API Reference

## Základní struktura
Pohoda komunikuje přes XML dataPack. Každý požadavek je obalen:

```xml
<?xml version="1.0" encoding="Windows-1250"?>
<dat:dataPack version="2.0"
  xmlns:dat="http://www.stormware.cz/schema/version_2/data.xsd"
  id="IMPORT_ID" ico="04856562" application="INFER_FORGE"
  note="Import z INFER FORGE">
  <dat:dataPackItem version="2.0" id="ITEM_ID">
    <!-- obsah -->
  </dat:dataPackItem>
</dat:dataPack>
```

## POZOR:
- Kódování: Windows-1250 (ne UTF-8!)
- IČO musí odpovídat licenci Pohody
- Číslo dokladu: ověř číselnou řadu v Pohodě
- Datum formát: YYYY-MM-DD

## Typy dokladů:
- nabídka přijatá (ofr:offer, offerType=receivedOffer)
- objednávka přijatá (ord:order, orderType=receivedOrder)
- faktura vydaná (inv:invoice, invoiceType=issuedInvoice)
- adresář (adb:addressbook)

## Běžné chyby:
- XML validace selže → vždy validuj proti XSD
- Duplicitní číslo dokladu → použij unikátní prefix
- Timeout → mServer má limit, rozděl velké importy
```

---

## 7. Hooks — Automatické akce

**Soubor: `.claude/settings.json`** (přidej hooks sekci)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q '.py$'; then cd /path/to/infer-forge && ruff check --fix $(echo \"$CLAUDE_TOOL_INPUT\" | jq -r '.path') 2>/dev/null; fi"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"$CLAUDE_TOOL_INPUT\" | jq -r '.command' | grep -qE '(rm -rf /|DROP DATABASE|DROP TABLE|TRUNCATE)' && echo 'BLOCKED: Destructive command detected' && exit 2 || exit 0"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"$CLAUDE_NOTIFICATION\" with title \"INFER FORGE\"'"
          }
        ]
      }
    ]
  }
}
```

### Co hooks dělají:

| Hook | Trigger | Akce |
|---|---|---|
| **PostToolUse (Write)** | Po každém zápisu .py souboru | Automaticky spustí ruff linter |
| **PreToolUse (Bash)** | Před destruktivním příkazem | Blokuje rm -rf, DROP TABLE apod. |
| **Notification** | Když Claude potřebuje pozornost | macOS notifikace |

---

## 8. Doporučené MCP servery pro rozšíření

### Později přidat:

```json
{
  "sentry": {
    "command": "npx",
    "args": ["-y", "@anthropic/sentry-mcp-server"],
    "env": { "SENTRY_AUTH_TOKEN": "<token>" }
  },
  "slack": {
    "command": "npx",
    "args": ["-y", "@anthropic/slack-mcp-server"],
    "env": { "SLACK_BOT_TOKEN": "<token>" }
  }
}
```

---

## 9. Jak pracovat — Denní workflow

### Ráno: Nastartuj projekt

```bash
cd infer-forge
claude

# Uvnitř Claude:
/status                    # Co je hotové, co zbývá
```

### Plánování nové funkce:

```bash
/plan "Email Agent — příjem a klasifikace poptávek přes IMAP"
```

### Implementace s delegací na agenty:

```bash
# Hlavní orchestrace:
/implement "Email Agent dle plánu"

# Nebo přímo deleguj:
@ocel "Implementuj Celery task pro polling IMAP mailboxu"
@spojka "Vytvoř Pohoda XML connector pro nabídky"
@neuron "Navrhni klasifikační prompt pro rozlišení poptávka vs objednávka"
@forma "Vytvoř Inbox komponentu se seznamem příchozích emailů"
@kontrola "Napiš Dockerfile pro backend službu"
```

### Code review:

```bash
/review
# nebo
@kovar "Review posledního PR — zaměř se na Pohoda integraci"
```

### Testování Pohody:

```bash
/pohoda-test
```

---

## 10. Model strategie — Kdy který model

| Úkol | Model | Důvod |
|---|---|---|
| Architektura, plánování | **Opus** | Komplexní reasoning |
| Code review | **Opus** | Hluboká analýza |
| Implementace backend | **Sonnet** | Rychlost + kvalita |
| Implementace frontend | **Sonnet** | Dobrý poměr cena/výkon |
| Rychlé opravy, formátování | **Haiku** | Nejrychlejší, nejlevnější |
| AI/ML pipeline design | **Opus** | Kreativní řešení |
| Testování, DevOps | **Sonnet** | Standardní tasky |

V Claude Code přepínáš modely:
```
/model opus
/model sonnet
/model haiku
```

Nebo v subagent definici přes `model: opus|sonnet|haiku`.

---

## 11. Quick Start — První den

```bash
# 1. Nainstaluj Claude Code
npm install -g @anthropic-ai/claude-code

# 2. Vytvoř projekt
mkdir infer-forge && cd infer-forge
git init

# 3. Zkopíruj PRD
mkdir docs
cp ~/INFER_FORGE_PRD_v1.0.md docs/

# 4. Vytvoř CLAUDE.md (obsah výše)

# 5. Vytvoř agenty, příkazy, skills (obsah výše)
mkdir -p .claude/agents .claude/commands .claude/skills

# 6. Nastav MCP servery
# → .claude/mcp.json (obsah výše)

# 7. Spusť Claude Code
claude

# 8. První příkaz:
> Přečti docs/INFER_FORGE_PRD_v1.0.md a vytvoř scaffold pro Fázi F1:
> - Backend: FastAPI projekt s datovým modelem (zákazník, zakázka, položka, nabídka)
> - Alembic migrace
> - Docker Compose (Python + PostgreSQL + Redis)
> - Frontend: Next.js 14 projekt s basic layoutem
```

---

## 12. Tipy pro maximální produktivitu

1. **Udržuj CLAUDE.md aktuální** — po každé větší změně aktualizuj strukturu/konvence
2. **Deleguj na subagenty** — hlavní session orchestruje, agenti implementují
3. **Používej /compact** — když dojde kontext, kompaktuj historii
4. **Git po každém milníku** — commituj často, Claude může vždy rollbacknout
5. **Skills pro doménové znalosti** — čím víc skills, tím lepší výstupy
6. **Hooks pro automatizaci** — lint, format, notifikace automaticky
7. **Context7 MCP** — vždy aktuální docs knihoven, ne zastaralý training data

---

*Tento guide slouží jako bootcamp pro nastartování INFER FORGE v Claude Code.
S tímto setupem máš k dispozici plně vyzbrojený AI dev tým.*
