# Changelog

Všechny významné změny v projektu **inferbox**.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.0.0/),
verzování podle [Semantic Versioning](https://semver.org/lang/cs/).

## [Unreleased]

### Added (2026-02-08)

#### Automatický zálohovací systém
- **scripts/backup_db.sh** - Hlavní zálohovací skript
  - Záloha PostgreSQL přes `docker compose exec db pg_dump`
  - Komprese gzip
  - Záloha uploads volume (docker cp + tar.gz)
  - Pojmenování: `inferbox-backup-YYYY-MM-DD-HHMMSS.sql.gz`
  - Exit code kontrola + error reporting
  - Logování do `/var/log/inferbox-backup.log`
- **scripts/backup-rotation.sh** - Retention policy management
  - 7 denních záloh (smaže starší)
  - 4 týdenní zálohy (smaže starší než 28 dní)
  - 3 měsíční zálohy (smaže starší než 90 dní)
  - Statistiky (počet záloh, celková velikost)
- **scripts/backup-cron.sh** - Instalace automatických cron jobs
  - Denní záloha každý den v 2:00
  - Týdenní záloha každou neděli ve 3:00
  - Nastavení oprávnění (755 pro adresář, 644 pro log)
- **scripts/restore_db.sh** - Vylepšené obnovení ze zálohy
  - Safety backup před restore (rollback při chybě)
  - Potvrzení uživatelem (yes/no prompt)
  - Podporuje `.sql.gz` (gzip) i `.sql` (plain)
  - Restore přes `docker compose exec db psql`
  - Restore uploads volume (pokud zadáno)
  - Spustí `alembic upgrade head` po restore
- **scripts/test-backup-system.sh** - Test zálohovacího systému
  - Kontrola existence skriptů
  - Kontrola oprávnění (executable)
  - Kontrola Docker Compose konfigurace
  - Kontrola .env.prod
  - Kontrola Docker daemon status
  - Kontrola backup directory
  - Kontrola cron jobs

#### Dokumentace zálohovacího systému
- **docs/BACKUP_SYSTEM.md** - Kompletní dokumentace backup systému
  - Přehled (denní/týdenní zálohy, retention policy)
  - Instalace a konfigurace
  - Manuální použití (backup, restore, monitoring)
  - Popis všech skriptů
  - Bezpečnostní doporučení (off-site, šifrování)
  - Monitoring a alerting
  - Testování (dry run, disaster recovery test)
  - Troubleshooting
  - ISO 9001 compliance checklist
- **docs/DEPLOYMENT_BACKUP.md** - Instalační návod pro produkční server
  - Krok-za-krokem instalace na serveru 91.99.126.53
  - Test manuální zálohy
  - Test týdenní zálohy
  - Test restore
  - Monitoring (live logy, kontrola chyb)
  - Troubleshooting
  - Bezpečnostní doporučení (off-site, šifrování, alerting)
  - Quarterly Disaster Recovery test
  - Checklist po instalaci
- **scripts/README.md** - Přehled utility skriptů
  - Quick start pro zálohy
  - Tabulka všech skriptů
  - Environment variables

### Changed (2026-02-08)
- **README.md** - Přidána sekce o zálohovacím systému
  - Quick start pro backup/restore
  - Retention policy přehled
  - Odkazy na kompletní dokumentaci

### Added (2026-02-07)

#### Produkční deployment stack
- **docker-compose.prod.yml** - Produkční Docker Compose konfigurace
  - PostgreSQL 16 + pgvector
  - Redis 7 s heslem
  - Backend (FastAPI) s health checks
  - Celery worker + beat scheduler
  - Frontend (Next.js) production build
  - Všechny porty bindované na localhost (bezpečnost)
  - Health checks pro všechny služby
  - Restart policy: `unless-stopped`

#### Konfigurace a dokumentace
- **.env.prod.example** - Šablona pro produkční environment variables
  - Všechny potřebné proměnné s popisem
  - Bezpečnostní poznámky
  - Příklady pro různé konfigurace
- **PRODUCTION.md** - Quick start guide pro produkční deployment
- **docs/deployment.md** - Kompletní deployment dokumentace
  - Server setup
  - SSL/TLS certifikáty (Let's Encrypt)
  - Nginx reverzní proxy konfigurace
  - Automatické backupy
  - Monitoring a alerting
  - Rollback procedura
  - Troubleshooting
- **docs/security.md** - Bezpečnostní dokumentace
  - CORS konfigurace
  - Secrets management
  - SSL/TLS best practices
  - Rate limiting
  - Firewall setup
  - SSH hardening
  - Audit trail
  - GDPR compliance
  - Incident response
- **README.md** - Hlavní README s přehledem projektu

#### Utility skripty
- **scripts/generate-secrets.py** - Generátor bezpečných hesel
  - SECRET_KEY (64+ znaků)
  - Database hesla (32+ znaků)
  - Redis hesla
  - Kompletní .env.prod generátor
- **scripts/health-check.sh** - Komplexní health check skript
  - Docker containers status
  - Backend API health
  - PostgreSQL connectivity
  - Redis connectivity
  - Frontend availability
  - Celery workers status
  - Disk usage monitoring
  - Memory usage
  - Recent errors v logs
- **scripts/test-cors.sh** - CORS konfigurace tester

#### Developer experience
- **Makefile** - Zjednodušené příkazy pro běžné operace
  - `make dev` - Development prostředí
  - `make prod` - Produkční stack
  - `make test` - Všechny testy
  - `make lint` - Lintery
  - `make migrate` - Databázové migrace
  - `make backup` - Backup databáze
  - `make health` - Health check
  - `make secrets` - Generování secrets
  - A mnoho dalších...

#### Backend změny
- **app/core/config.py**
  - Přidán `CORS_ORIGINS` konfigurační parametr
  - Podpora pro comma-separated list of origins
- **app/main.py**
  - CORS middleware nyní čte origins z konfigurace
  - Dynamická konfigurace místo hardcoded hodnot

#### Bezpečnost
- **.gitignore** - Aktualizace
  - `.env.prod` - produkční secrets
  - `*.sql`, `*.sql.gz` - databázové backupy
  - `*.pem`, `*.crt`, `*.key` - SSL certifikáty
  - `*.log` - log soubory
  - `backup/`, `backups/` - backup adresáře

### Security

- CORS origins nyní konfigurovatelné (ne hardcoded)
- Všechny Docker porty pouze na localhost v produkci
- Redis s povinným heslem v produkci
- Dokumentované best practices pro secrets management
- Health check endpoints pro monitoring
- Utility pro generování silných hesel

### Changed

- CORS middleware: z hardcoded seznamu na konfiguraci z .env
- Import v main.py: z `typing` na `collections.abc` (modernizace)

## [0.1.0] - 2026-02-06

### Added

- Iniciální projekt scaffold pro **inferbox**
- Backend: FastAPI, SQLAlchemy, Celery
- Frontend: Next.js 14, TypeScript, Tailwind
- Docker Compose pro development
- Základní API endpointy
- Database modely
- Authentication (JWT)
- Health check endpoints

---

## Konvence pro změny

### Typy změn
- **Added** - Nové funkce
- **Changed** - Změny existující funkcionality
- **Deprecated** - Brzy odstraněné funkce
- **Removed** - Odstraněné funkce
- **Fixed** - Opravy bugů
- **Security** - Bezpečnostní opravy

### Commit messages
Používáme [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - Nová funkce (Added)
- `fix:` - Oprava bugu (Fixed)
- `docs:` - Dokumentace
- `refactor:` - Refaktoring kódu
- `test:` - Přidání testů
- `chore:` - Údržba, build config
- `security:` - Bezpečnostní opravy
