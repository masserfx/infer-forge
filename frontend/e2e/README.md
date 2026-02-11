# E2E Testy inferbox Frontend

Playwright E2E testovací framework pro **inferbox** aplikaci.

## Spuštění testů

```bash
# Spustit všechny testy
npm run test:e2e

# Spustit testy s UI módem
npm run test:e2e:ui

# Spustit specifický testovací soubor
npx playwright test e2e/auth.spec.ts

# Spustit testy s reportem
npx playwright test --reporter=html
```

## Testovací prostředí

- **Base URL:** `http://91.99.126.53:3000` (dev server)
- **Test účet:** `admin@infer.cz` / `admin123`
- **Browser:** Chromium
- **Timeout:** 30s pro načítání stránek, 10s pro elementy
- **Workers:** 1 (sekvenční běh kvůli sdílené auth)

## Testové soubory

### 1. `auth.spec.ts` - Autentizace
- ✅ Úspěšné přihlášení
- ✅ Chybné přihlašovací údaje

### 2. `dashboard.spec.ts` - Dashboard
- ✅ Zobrazení dashboard statistik
- ✅ Načtení grid layoutu se stat cards

### 3. `orders.spec.ts` - Zakázky
- ✅ Zobrazení seznamu zakázek (tabulka)
- ✅ Navigace na detail zakázky (kliknutí na řádek)
- ✅ Zobrazení detailu zakázky (číslo ZAK-*)

### 4. `kanban.spec.ts` - Kanban board
- ✅ Kontrola existence stránky `/kanban`
- ⏸️ Akceptuje 404 pokud stránka ještě není implementována

### 5. `leaderboard.spec.ts` - Žebříček
- ✅ Kontrola existence stránky `/zebricek`
- ⏸️ Akceptuje 404 pokud stránka ještě není implementována

### 6. `navigation.spec.ts` - Navigace
- ✅ Navigace napříč všemi hlavními stránkami
- ✅ Kontrola absence Application errors
- Testované stránky:
  - `/dashboard`
  - `/zakazky`
  - `/kalkulace`
  - `/reporting`
  - `/inbox`
  - `/dokumenty`
  - `/pohoda`
  - `/nastaveni`

## Helper funkce (`helpers.ts`)

### `login(page: Page)`
Provede přihlášení s admin účtem a čeká na redirect na dashboard.

### `expectNoConsoleErrors(page: Page)`
Zachytává console errors během testu (kromě ERR_ABORTED).

## Výsledky testů

```
8 passed (26.4s)
- Authentication: 2 testy
- Dashboard: 1 test
- Kanban Board: 1 test
- Leaderboard: 1 test
- Navigation: 1 test
- Orders: 2 testy
```

## Poznámky

- Testy běží sekvenčně (workers: 1) kvůli sdílené autentizaci
- Screenshots jsou pořízeny pouze při selhání testu
- Trace je zachycen při prvním opakování (retry)
- Stránky `/kanban` a `/zebricek` akceptují 404 (nejsou ještě nasazeny)
- Všechny timeouty jsou nastaveny na 30s kvůli pomalejšímu dev serveru

## Další vývoj

Potenciální rozšíření E2E testů:

1. **Kalkulace** - vytvoření nové kalkulace, editace, AI agent
2. **Dokumenty** - upload, OCR parsing, generování dokumentů
3. **Inbox** - klasifikace emailů, přiřazení k zakázkám
4. **Reporting** - kontrola grafů, filtrů
5. **Pohoda sync** - testování XML exportu
6. **Nastavení** - změna konfigurace, uživatelské profily

## Troubleshooting

### Timeout při přihlášení
- Zkontrolovat, zda dev server běží: `curl http://91.99.126.53:3000`
- Zvýšit timeout v `helpers.ts`

### Element not found
- Použít více specifický selector (např. `main h1` místo jen `h1`)
- Přidat `await page.waitForLoadState("networkidle")`
- Zkontrolovat screenshot v `test-results/`

### Strict mode violation
- Více elementů odpovídá selektoru
- Použít `.first()`, `.last()` nebo specifičtější selektor
