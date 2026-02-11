.PHONY: help dev prod up down logs build test clean health backup secrets

# Barvy pro výstup
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)

help: ## Zobrazí nápovědu
	@echo "$(GREEN)inferbox - Makefile příkazy$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# Development
dev: ## Spustí development prostředí
	@echo "$(GREEN)Spouštím development stack...$(RESET)"
	docker compose up -d db redis
	@echo "$(YELLOW)Backend:$(RESET)  cd backend && uv run uvicorn app.main:app --reload"
	@echo "$(YELLOW)Frontend:$(RESET) cd frontend && npm run dev"

dev-backend: ## Spustí pouze backend development server
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-frontend: ## Spustí pouze frontend development server
	cd frontend && npm run dev

# Production
prod: ## Spustí produkční stack
	@echo "$(GREEN)Spouštím produkční stack...$(RESET)"
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

prod-logs: ## Sleduje logy produkčního stacku
	docker compose -f docker-compose.prod.yml logs -f

prod-down: ## Zastaví produkční stack
	docker compose -f docker-compose.prod.yml down

prod-restart: ## Restartuje produkční stack
	docker compose -f docker-compose.prod.yml restart

# Common
up: ## Spustí development stack (alias pro dev)
	docker compose up -d

down: ## Zastaví development stack
	docker compose down

logs: ## Sleduje logy development stacku
	docker compose logs -f

build: ## Rebuild Docker images
	docker compose build

# Database
migrate: ## Spustí Alembic migrace
	cd backend && uv run alembic upgrade head

migrate-create: ## Vytvoří novou migraci (použij: make migrate-create MSG="popis")
	cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Vrátí poslední migraci
	cd backend && uv run alembic downgrade -1

db-shell: ## Připojí se do PostgreSQL shell
	docker compose exec db psql -U infer -d infer_forge

# Testing
test: ## Spustí všechny testy
	@echo "$(GREEN)Backend testy...$(RESET)"
	cd backend && uv run pytest
	@echo "$(GREEN)Frontend testy...$(RESET)"
	cd frontend && npm test

test-backend: ## Spustí backend testy
	cd backend && uv run pytest

test-frontend: ## Spustí frontend testy
	cd frontend && npm test

test-cov: ## Spustí testy s coverage reportem
	cd backend && uv run pytest --cov --cov-report=html
	cd frontend && npm run test:coverage

# Linting
lint: ## Spustí lintery
	@echo "$(GREEN)Backend lint...$(RESET)"
	cd backend && uv run ruff check .
	@echo "$(GREEN)Frontend lint...$(RESET)"
	cd frontend && npm run lint

lint-fix: ## Opraví automaticky opravitelné lint errory
	cd backend && uv run ruff check --fix .
	cd frontend && npm run lint -- --fix

format: ## Naformátuje kód
	cd backend && uv run ruff format .
	cd frontend && npm run format

typecheck: ## Zkontroluje typy
	@echo "$(GREEN)Backend typecheck...$(RESET)"
	cd backend && uv run mypy .
	@echo "$(GREEN)Frontend typecheck...$(RESET)"
	cd frontend && npm run type-check

# Health & Monitoring
health: ## Zkontroluje health všech služeb
	@./scripts/health-check.sh

health-quick: ## Rychlý health check (pouze API)
	@curl -sf http://localhost:8000/health | jq '.' || echo "❌ Backend nedostupný"

stats: ## Zobrazí Docker stats
	docker stats --no-stream

# Backup & Recovery
backup: ## Vytvoří backup databáze
	@echo "$(GREEN)Vytvářím backup...$(RESET)"
	@mkdir -p backups
	docker compose exec -T db pg_dump -U infer infer_forge | gzip > backups/db_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)Backup vytvořen v backups/$(RESET)"

restore: ## Obnoví databázi z backupu (použij: make restore FILE=backups/db_xxx.sql.gz)
	@echo "$(YELLOW)Obnovuji databázi z $(FILE)...$(RESET)"
	gunzip -c $(FILE) | docker compose exec -T db psql -U infer infer_forge
	@echo "$(GREEN)Databáze obnovena$(RESET)"

# Security
secrets: ## Vygeneruje nové secrets
	python scripts/generate-secrets.py --quick

secrets-file: ## Vygeneruje .env.prod soubor
	python scripts/generate-secrets.py --output .env.prod

test-cors: ## Testuje CORS konfiguraci
	./scripts/test-cors.sh http://localhost:8000

# Celery
celery-worker: ## Spustí Celery worker
	cd backend && uv run celery -A app.core.celery_app worker -l info

celery-beat: ## Spustí Celery beat scheduler
	cd backend && uv run celery -A app.core.celery_app beat -l info

celery-inspect: ## Zobrazí stav Celery workerů
	cd backend && uv run celery -A app.core.celery_app inspect active

# Cleanup
clean: ## Vyčistí cache a build artefakty
	@echo "$(YELLOW)Čistím cache...$(RESET)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -prune -o -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cache vyčištěn$(RESET)"

clean-docker: ## Smaže Docker containers a volumes (NEBEZPEČNÉ!)
	@echo "$(YELLOW)VAROVÁNÍ: Smaže všechna Docker data!$(RESET)"
	@read -p "Opravdu chceš pokračovat? (ano/ne): " confirm; \
	if [ "$$confirm" = "ano" ]; then \
		docker compose down -v; \
		echo "$(GREEN)Docker data smazána$(RESET)"; \
	else \
		echo "$(YELLOW)Operace zrušena$(RESET)"; \
	fi

# Install
install-backend: ## Nainstaluje backend dependencies
	cd backend && uv sync

install-frontend: ## Nainstaluje frontend dependencies
	cd frontend && npm install

install: install-backend install-frontend ## Nainstaluje všechny dependencies

# Development helpers
shell-backend: ## Otevře Python shell s app contextem
	cd backend && uv run python -i -c "from app.core import get_db, get_settings; settings = get_settings(); print('Settings loaded')"

shell-redis: ## Připojí se do Redis CLI
	docker compose exec redis redis-cli

watch-logs: ## Sleduje logy s filtrem (použij: make watch-logs FILTER="error")
	docker compose logs -f | grep -i "$(FILTER)"

# Quick commands
qq: health ## Quick check (alias pro health)

