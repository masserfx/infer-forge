# INFER s.r.o. — Manufacturing Automation Platform

## Product Document (PRD) pro AI Agentní Developerský Tým

**Verze:** 1.0  
**Datum:** 7. února 2026  
**Kódový název projektu:** inferbox  
**Klasifikace:** Interní — Strategický dokument

---

## 1. Executive Summary

Infer s.r.o. je výrobně orientovaná strojírenská společnost se sídlem v Praze, specializující se na komplexní dodávky v oblasti potrubních dílů a systémů, obrábění, svařování, montáží průmyslových zařízení a ocelových konstrukcí. Firma je certifikována dle ČSN EN ISO 9001:2016 a dodává produkty s plnou kvalitativní dokumentací (WPQR, WPS, NDT).

Cílem projektu **inferbox** je vybudovat automatizační platformu, která digitalizuje klíčové obchodní a výrobní procesy — od příjmu poptávky přes tvorbu nabídky, zpracování výkresové dokumentace, generování výrobních sestav, až po fakturaci v ekonomickém systému Pohoda. Platforma bude řízena AI agenty orchestrovanými zkušeným Product & Engineering Leaderem.

---

## 2. Profil společnosti Infer s.r.o.

### 2.1 Klíčové obchodní činnosti

| Oblast | Detail |
|---|---|
| **Potrubní díly** | Výroba, dodávka a montáž potrubních tras, distribučních systémů a technologií |
| **Obrábění** | CNC obrábění, soustružení, frézování — kusová i malosériová výroba |
| **Svařování** | Svařence z uhlíkových, legovaných a korozivzdorných ocelí |
| **Montáže** | Turbíny, kompresory, potrubní trasy, kabeláže, ocelové konstrukce |
| **Tlaková zařízení** | Výroba, montáž, opravy, rekonstrukce a revize vyhrazených tlakových zařízení |
| **Inženýring** | Zpracování projektů, návrhů a výpočtů pro technologická zařízení a konstrukce |
| **Kontrola kvality** | XRF spektrometrie, kompletní svářečská dokumentace, NDT testování |

### 2.2 Certifikace a standardy

- ČSN EN ISO 9001:2016
- Atestace dle EN 10-204 (2.1, 2.2, 3.1, 3.2)
- WPQR, WPS, NDT dokumentace
- DELTA ED-XRF rentgenový spektrometr pro strukturální kontrolu

### 2.3 Klíčoví zákazníci

Průmyslové podniky v oblasti energetiky, petrochemie, hutnictví a těžkého strojírenství v ČR a střední Evropě.

---

## 3. Problémová analýza — Současný stav

### 3.1 Identifikované bolesti

1. **Manuální zpracování poptávek** — příchozí emaily s technickými specifikacemi, výkresy (DWG/PDF/STEP) a textovými požadavky jsou zpracovávány ručně
2. **Fragmentovaná dokumentace** — výkresy, kalkulace, nabídky a objednávky žijí v oddělených Excel souborech a emailových schránkách
3. **Odpojený účetní systém** — data se do Pohody přepisují manuálně, vznikají chyby a zpoždění
4. **Absence trasovatelnosti** — nelze snadno dohledat historii zakázky od poptávky po fakturaci
5. **Časová náročnost nabídkového procesu** — technolog musí ručně kalkulovat materiál, práci, kooperace
6. **Duplicitní práce** — stejné díly se kalkulují opakovaně bez využití historických dat

### 3.2 Současný tech stack (odhad)

- **Email:** Outlook / firemní SMTP
- **Účetnictví:** Stormware Pohoda (XML API / mDB)
- **Dokumentace:** Excel, PDF výkresy, papírové výrobní průvodky
- **CAD:** pravděpodobně AutoCAD / SolidWorks / Inventor pro inženýring
- **ERP:** žádný dedikovaný systém

---

## 4. Architektura řešení inferbox

### 4.1 Přehled systému

```
┌─────────────────────────────────────────────────────────────────┐
│                        inferbox                                  │
│                   Orchestrační vrstva (AI)                      │
├─────────┬──────────┬───────────┬────────────┬──────────────────┤
│  EMAIL  │  PARSER  │ KALKULACE │  POHODA    │  DOKUMENTY       │
│  Agent  │  Agent   │  Agent    │  Agent     │  Agent           │
├─────────┴──────────┴───────────┴────────────┴──────────────────┤
│                    Datová vrstva (PostgreSQL)                    │
├─────────────────────────────────────────────────────────────────┤
│              Integrační vrstva (API Gateway)                    │
├─────────┬──────────┬───────────┬────────────┬──────────────────┤
│ IMAP/   │ OCR /    │ Excel /   │ Pohoda     │ FileSystem /     │
│ SMTP    │ PDF      │ CSV       │ XML API    │ S3 Storage       │
│ Server  │ Engine   │ Templates │ mServer    │                  │
└─────────┴──────────┴───────────┴────────────┴──────────────────┘
```

### 4.2 Moduly systému

#### Modul 1: EMAIL AGENT — Příjem a klasifikace komunikace

**Funkce:**
- Napojení na firemní email (IMAP/SMTP) — monitoruje příchozí zprávy
- AI klasifikace: poptávka / objednávka / reklamace / dotaz / příloha k existující zakázce
- Extrakce příloh (PDF výkresy, DWG, STEP, Excel specifikace)
- Automatické přiřazení k existující zakázce nebo vytvoření nové
- Generování potvrzovacích odpovědí s odkazem na zakázku

**Technologie:** IMAP listener, LLM klasifikátor, pravidlový engine

#### Modul 2: PARSER AGENT — Analýza technické dokumentace

**Funkce:**
- OCR a extrakce dat z PDF výkresů (rozměry, materiály, tolerance, povrchové úpravy)
- Parsování Excel tabulek s kusovníky (BOM — Bill of Materials)
- Rozpoznání STEP/DWG souborů — extrakce metadat
- Strukturování dat do standardizovaného formátu zakázky
- Identifikace podobných historických zakázek pro referenční kalkulaci

**Technologie:** Tesseract OCR, pdf-parse, openpyxl, CAD metadata reader, vector search (pgvector)

#### Modul 3: KALKULACE AGENT — Automatické nacenění

**Funkce:**
- Výpočet materiálových nákladů dle aktuálních ceníků (ocel, nerez, slitiny)
- Kalkulace strojního času (CNC, svařování, montáž) dle normativů
- Přirážky za kooperace (tepelné zpracování, NDT, povrchové úpravy)
- Marže a slevy dle zákaznické kategorie
- Generování nabídkového listu (PDF) s technickou specifikací
- Porovnání s historickými kalkulacemi podobných dílů

**Technologie:** Python kalkulační engine, Excel šablony, Jinja2 PDF generátor

#### Modul 4: POHODA AGENT — Integrace s účetním systémem

**Funkce:**
- Vytvoření odběratele v Pohoda (pokud neexistuje)
- Generování nabídky (typ dokladu "Nabídka přijatá")
- Konverze nabídky na objednávku po potvrzení zákazníkem
- Vytvoření faktur (zálohová, konečná)
- Synchronizace skladových položek a materiálu
- Export/import přes Pohoda XML API (mServer / XML datapump)

**Technologie:** Pohoda XML API, lxml, requests, scheduled sync jobs

#### Modul 5: DOKUMENTY AGENT — Správa výrobní dokumentace

**Funkce:**
- Generování výrobních průvodek z kalkulace
- Sestavení výrobního plánu s operacemi a termíny
- Správa verzí výkresové dokumentace
- Archivace kompletní zakázkové dokumentace
- Generování protokolů (rozměrový protokol, materiálový atest)
- Export do Excel pro výrobní plánování

**Technologie:** python-docx, openpyxl, reportlab, file versioning system

### 4.3 Datový model — Jádro systému

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   ZÁKAZNÍK   │────▸│   ZAKÁZKA    │────▸│   POLOŽKA        │
│              │     │              │     │                  │
│ ico          │     │ cislo        │     │ nazev            │
│ nazev        │     │ stav         │     │ material         │
│ kontakt      │     │ datum_prijmu │     │ pocet_ks         │
│ pohoda_id    │     │ termin       │     │ vykres_cislo     │
│ kategorie    │     │ zakaznik_id  │     │ operace[]        │
└──────────────┘     │ priorita     │     │ kalkulace        │
                     │ poznamky     │     │ stav_vyroby      │
                     └──────┬───────┘     └──────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
      ┌──────────────┐ ┌─────────┐ ┌───────────────┐
      │   NABÍDKA    │ │ VÝKRES  │ │   FAKTURA     │
      │              │ │         │ │               │
      │ cislo        │ │ soubor  │ │ pohoda_cislo  │
      │ castka_czk   │ │ verze   │ │ typ           │
      │ platnost     │ │ format  │ │ castka        │
      │ stav         │ │ revize  │ │ splatnost     │
      └──────────────┘ └─────────┘ └───────────────┘
```

---

## 5. Integrace — Technické specifikace

### 5.1 Email integrace

```yaml
protokol: IMAP4_SSL / SMTP_SSL
polling_interval: 60s
supported_attachments:
  - application/pdf
  - application/vnd.ms-excel
  - application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  - application/step
  - application/acad (DWG)
  - image/png, image/jpeg
max_attachment_size: 50MB
classification_model: fine-tuned LLM na strojírenských poptávkách
```

### 5.2 Pohoda XML API

```xml
<!-- Příklad: Vytvoření nabídky v Pohoda -->
<dat:dataPack version="2.0" id="NFE001"
  ico="04856562" application="INFER_FORGE">
  <dat:dataPackItem version="2.0" id="NFE001">
    <ofr:offer version="2.0">
      <ofr:offerHeader>
        <ofr:offerType>receivedOffer</ofr:offerType>
        <ofr:numberOrder>
          <typ:numberRequested>NFE-2026-0001</typ:numberRequested>
        </ofr:numberOrder>
        <ofr:date>2026-02-07</ofr:date>
        <ofr:dateValid>2026-03-07</ofr:dateValid>
        <ofr:partnerIdentity>
          <typ:address>
            <typ:company>Zákazník XY s.r.o.</typ:company>
            <typ:ico>12345678</typ:ico>
          </typ:address>
        </ofr:partnerIdentity>
        <ofr:text>Nabídka — potrubní díly dle specifikace</ofr:text>
      </ofr:offerHeader>
      <ofr:offerDetail>
        <ofr:offerItem>
          <ofr:text>Koleno 90° DN150 PN16 — ocel 11 523</ofr:text>
          <ofr:quantity>24</ofr:quantity>
          <ofr:unit>ks</ofr:unit>
          <ofr:rateVAT>high</ofr:rateVAT>
          <ofr:homeCurrency>
            <typ:unitPrice>2850.00</typ:unitPrice>
          </ofr:homeCurrency>
        </ofr:offerItem>
      </ofr:offerDetail>
    </ofr:offer>
  </dat:dataPackItem>
</dat:dataPack>
```

### 5.3 Excel integrace

```yaml
vstupní_formáty:
  - BOM (Bill of Materials) — kusovníky od zákazníků
  - Ceníky materiálů — aktualizace z hutních skladů
  - Specifikační tabulky — rozměry, materiály, počty

výstupní_formáty:
  - Kalkulační list zakázky
  - Výrobní plán s operacemi
  - Přehled zakázek (dashboard)
  - Materiálová potřeba (nákupní list)

knihovna: openpyxl + pandas
šablony: Jinja2 Excel templates
```

---

## 6. Workflow — End-to-End zpracování zakázky

```
ZÁKAZNÍK                  inferbox                       INFER TÝM
   │                          │                              │
   │── Email s poptávkou ────▸│                              │
   │   (výkresy, BOM, spec)   │                              │
   │                          │── EMAIL AGENT ──────────────▸│
   │                          │   ✓ Klasifikace              │ Notifikace
   │                          │   ✓ Extrakce příloh          │ obchodníkovi
   │                          │   ✓ Vytvoření zakázky        │
   │                          │                              │
   │                          │── PARSER AGENT              │
   │                          │   ✓ OCR výkresů              │
   │                          │   ✓ Parsování BOM            │
   │                          │   ✓ Strukturování dat        │
   │                          │                              │
   │                          │── KALKULACE AGENT           │
   │                          │   ✓ Materiálový výpočet      │
   │                          │   ✓ Strojní časy             │
   │                          │   ✓ Kooperace + režie        │
   │                          │   ✓ Generování PDF nabídky   │
   │                          │                              │
   │                          │                     REVIEW ◀─┤
   │                          │                   Technolog   │
   │                          │                   schvaluje   │
   │                          │                              │
   │                          │── POHODA AGENT              │
   │                          │   ✓ Nabídka do Pohody        │
   │                          │                              │
   │◀─ Nabídka (PDF+email) ──│                              │
   │                          │                              │
   │── Potvrzení objednávky ─▸│                              │
   │                          │                              │
   │                          │── DOKUMENTY AGENT           │
   │                          │   ✓ Výrobní průvodka         │
   │                          │   ✓ Materiálová potřeba      │
   │                          │   ✓ Výrobní plán             │
   │                          │                              │
   │                          │── POHODA AGENT              │
   │                          │   ✓ Objednávka               │
   │                          │   ✓ Zálohová faktura         │
   │                          │   ✓ Konečná faktura          │
   │                          │                              │
   │◀─ Faktura ──────────────│                              │
   │                          │                              │
```

---

## 7. Tech Stack — Doporučený

| Vrstva | Technologie | Důvod |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | Rychlý vývoj, bohatý ekosystém pro datové zpracování |
| **Databáze** | PostgreSQL 16 + pgvector | Relační data + vektorové vyhledávání podobných zakázek |
| **Message Queue** | Redis Streams / Celery | Asynchronní zpracování emailů a dokumentů |
| **AI/LLM** | Claude API (Anthropic) | Klasifikace, extrakce, generování dokumentů |
| **OCR** | Tesseract + pdf2image | Extrakce textu z výkresů |
| **PDF generování** | WeasyPrint / ReportLab | Nabídky, průvodky, protokoly |
| **Excel** | openpyxl + pandas | Čtení/zápis Excel souborů |
| **Email** | imaplib + smtplib / aiosmtplib | IMAP/SMTP integrace |
| **Pohoda** | lxml + requests | XML API komunikace |
| **Frontend** | Next.js 14 + Tailwind | Dashboard pro správu zakázek |
| **Auth** | Keycloak / NextAuth | Přihlašování, role (obchodník, technolog, vedení) |
| **Deployment** | Docker + Docker Compose | On-premise nasazení (citlivá data) |
| **CI/CD** | GitHub Actions | Automatizované testování a nasazení |
| **Monitoring** | Sentry + Prometheus + Grafana | Logování chyb, metriky |

---

## 8. Bezpečnost a compliance

### 8.1 Požadavky

- **GDPR** — osobní údaje zákazníků, kontaktní informace
- **ISO 9001** — trasovatelnost dokumentace, verzování, audit trail
- **On-premise nasazení** — výkresy a technická dokumentace nesmí opustit firemní síť
- **Role-based access control** — obchodník, technolog, vedení, účetní
- **Šifrování** — TLS pro komunikaci, AES-256 pro úložiště dokumentů
- **Backup** — denní automatické zálohy databáze a dokumentového úložiště

### 8.2 Audit trail

Každá akce v systému bude logována: kdo, kdy, co, na jaké zakázce. Nutné pro ISO 9001 audit a interní kontrolu.

---

## 9. Fáze implementace

| Fáze | Rozsah | Trvání | Milestone |
|---|---|---|---|
| **F0: Discovery** | Analýza procesů, mapování dat, PoC | 3 týdny | Validovaný datový model |
| **F1: Core** | Datový model, Email Agent, základní UI | 6 týdnů | Automatický příjem poptávek |
| **F2: Parser** | OCR, BOM parser, výkresová analýza | 5 týdnů | Strukturovaná data ze vstupů |
| **F3: Kalkulace** | Kalkulační engine, ceníky, šablony | 5 týdnů | Automatická nabídka |
| **F4: Pohoda** | XML API integrace, sync | 4 týdny | Nabídky/faktury v Pohodě |
| **F5: Dokumenty** | Průvodky, plány, archivace | 4 týdny | Kompletní workflow |
| **F6: Polish** | UX, edge cases, load testing | 3 týdny | Production-ready |
| **CELKEM** | | **~30 týdnů** | **Full launch** |

---

## 10. Struktura AI Agentního Developerského Týmu

### 10.1 Filosofie týmu

Tým je organizován jako **product-led engineering squad** vedený zkušeným leaderem, který kombinuje hluboké technické znalosti s porozuměním strojírenskému byznysu. Každý člen týmu je AI agent se specializovanou rolí, schopný autonomní práce i spolupráce.

### 10.2 Organizační struktura

```
                    ┌──────────────────────────────┐
                    │     🎯 PRODUCT & ENGINEERING  │
                    │          LEADER               │
                    │                               │
                    │  "Kovář" — orchestrátor       │
                    │  Řídí vizi, priority, kvalitu │
                    └──────────┬───────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
  ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
  │  BACKEND      │   │  INTEGRACE    │   │  FRONTEND     │
  │  ARCHITEKT    │   │  SPECIALISTA  │   │  DEVELOPER    │
  │               │   │               │   │               │
  │  "Ocel"       │   │  "Spojka"     │   │  "Forma"      │
  └───────┬───────┘   └───────┬───────┘   └───────────────┘
          │                   │
  ┌───────▼───────┐   ┌───────▼───────┐
  │  AI/ML        │   │  QA &         │
  │  ENGINEER     │   │  DevOps       │
  │               │   │               │
  │  "Neuron"     │   │  "Kontrola"   │
  └───────────────┘   └───────────────┘
```

### 10.3 Detailní role

---

#### 🎯 PRODUCT & ENGINEERING LEADER — "Kovář"

**Profil:** Zkušený product manager / engineering leader se 10+ lety praxe ve strojírenství a IT. Rozumí výrobním procesům, normám (ISO 9001, EN 10-204), kalkulačním metodikám a zároveň ovládá moderní softwarový vývoj.

**Zodpovědnosti:**
- Definice produktové vize a roadmapy
- Prioritizace backlogu na základě business hodnoty pro Infer s.r.o.
- Technické rozhodování (architektura, trade-offs)
- Komunikace se stakeholdery (vedení Infer, technologové, obchodníci)
- Code review a kvalitativní gate
- Sprint planning a retrospektivy
- Řízení rizik a eskalace

**Klíčové kompetence:**
- Strojírenská výroba: potrubní díly, tlakové nádoby, svářečská dokumentace
- Kalkulační metodiky: materiálové normy, strojní časy, režie
- Ekonomické systémy: Pohoda, ABRA, Money S3
- Softwarová architektura: mikroservisy, event-driven, API design
- AI/LLM: prompt engineering, RAG, fine-tuning
- Projektový management: Agile/Scrum, risk management

**Rozhodovací rámec:**
1. Má to přímý dopad na výrobní efektivitu Infer?
2. Je to v souladu s ISO 9001 požadavky?
3. Je řešení udržitelné a rozšiřitelné?
4. Zvládne to Infer provozovat bez externího týmu?

---

#### ⚙️ BACKEND ARCHITEKT — "Ocel"

**Profil:** Senior Python developer se zkušenostmi s datově intenzivními aplikacemi a enterprise integracemi.

**Zodpovědnosti:**
- Návrh a implementace datového modelu (PostgreSQL)
- FastAPI backend — REST + WebSocket API
- Implementace business logiky: kalkulační engine, workflow engine
- Celery task queue pro asynchronní zpracování
- Implementace audit trail a verzování dokumentů

**Technický stack:**
- Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic
- PostgreSQL 16, Redis, Celery
- pytest, mypy, ruff

**Klíčové deliverables:**
- Datový model zakázkového systému
- Kalkulační engine s konfigurovatelnými ceníky
- Workflow state machine (poptávka → nabídka → objednávka → výroba → fakturace)
- REST API dokumentace (OpenAPI)

---

#### 🔗 INTEGRAČNÍ SPECIALISTA — "Spojka"

**Profil:** Developer specializovaný na systémové integrace, parsování dat a práci s legacy systémy.

**Zodpovědnosti:**
- Email integrace (IMAP/SMTP) — polling, parsing, odpovědi
- Pohoda XML API — kompletní obousměrná synchronizace
- Excel import/export — BOM kusovníky, ceníky, výstupní sestavy
- OCR pipeline pro PDF výkresy
- Souborový management — verzování výkresů, archivace

**Technický stack:**
- imaplib, aiosmtplib, email.parser
- lxml, pohoda-xml (custom library)
- openpyxl, pandas
- Tesseract, pdf2image, PyMuPDF
- MinIO / local filesystem

**Klíčové deliverables:**
- Email listener s AI klasifikací
- Pohoda connector (CRUD pro nabídky, objednávky, faktury, adresář)
- BOM parser (multi-formát: Excel, CSV, PDF tabulky)
- Document versioning system

---

#### 🧠 AI/ML ENGINEER — "Neuron"

**Profil:** Specialista na NLP, document understanding a LLM integrace s focus na průmyslové aplikace.

**Zodpovědnosti:**
- Fine-tuning LLM klasifikátoru na strojírenských poptávkách (typy zakázek, urgence)
- RAG systém pro vyhledávání podobných historických zakázek
- Extrakce strukturovaných dat z nestrukturovaných vstupů (emaily, výkresy)
- Prompt engineering pro generování nabídkových textů
- Vektorová databáze pro embedding zakázek a výkresů

**Technický stack:**
- Anthropic Claude API
- pgvector, sentence-transformers
- LangChain / LlamaIndex pro RAG
- Tesseract + custom post-processing
- scikit-learn pro supplementární ML modely

**Klíčové deliverables:**
- Klasifikační pipeline pro příchozí komunikaci (accuracy > 95%)
- RAG systém: "najdi podobnou zakázku" (top-5 relevance > 80%)
- Extraction pipeline: email → strukturovaná poptávka
- Generátor nabídkových textů v češtině

---

#### 🖥️ FRONTEND DEVELOPER — "Forma"

**Profil:** React/Next.js developer s citem pro UX v enterprise prostředí.

**Zodpovědnosti:**
- Dashboard pro správu zakázek (kanban board: poptávka → nabídka → výroba → fakturace)
- Detail zakázky: přehled, dokumenty, komunikace, kalkulace, Pohoda stav
- Formuláře pro manuální zadání/editaci poptávek a kalkulací
- Real-time notifikace (WebSocket)
- Mobilní responsivita pro výrobní halu

**Technický stack:**
- Next.js 14 (App Router), TypeScript
- Tailwind CSS, shadcn/ui
- React Query (TanStack)
- WebSocket pro live updates

**Klíčové deliverables:**
- Zakázkový dashboard s filtry a vyhledáváním
- Kalkulační editor s live preview nákladů
- Inbox view pro příchozí poptávky s AI návrhy
- Export a tisk sestav

---

#### ✅ QA & DevOps ENGINEER — "Kontrola"

**Profil:** DevOps inženýr s důrazem na kvalitu, bezpečnost a spolehlivost production prostředí.

**Zodpovědnosti:**
- Docker kontejnerizace celého stacku
- CI/CD pipeline (GitHub Actions)
- Infrastruktura: on-premise server setup, networking, SSL
- Monitoring: Sentry, Prometheus, Grafana dashboardy
- Automatizované testování: unit, integration, E2E
- Bezpečnost: penetrační testy, dependency audit
- Backup strategie a disaster recovery

**Technický stack:**
- Docker, Docker Compose, Nginx
- GitHub Actions, pytest, Playwright
- Sentry, Prometheus, Grafana, Loki
- Certbot (Let's Encrypt), fail2ban

**Klíčové deliverables:**
- Production-ready Docker Compose stack
- CI/CD pipeline s automatickými testy
- Monitoring dashboard
- Backup a restore procedury
- Security hardening checklist

---

## 11. Metriky úspěchu (KPIs)

| Metrika | Současný stav (odhad) | Cíl po 6 měsících |
|---|---|---|
| Čas zpracování poptávky | 2–4 hodiny | < 30 minut |
| Čas tvorby nabídky | 4–8 hodin | < 1 hodina |
| Chybovost přepisu do Pohody | ~5% | < 0.5% |
| Trasovatelnost zakázky | Částečná (email) | 100% digitální |
| Využití historických kalkulací | 0% (manuální) | > 60% automaticky |
| Čas od objednávky k výrobní průvodce | 1–2 dny | < 2 hodiny |

---

## 12. Rizika a mitigace

| Riziko | Pravděpodobnost | Dopad | Mitigace |
|---|---|---|---|
| Odpor zaměstnanců ke změně | Vysoká | Vysoký | Postupné zavádění, školení, quick wins |
| Nestandardní formáty od zákazníků | Vysoká | Střední | Fallback na manuální zpracování + iterativní zlepšování |
| Pohoda API omezení | Střední | Vysoký | Důkladné testování, fallback na XML import/export |
| Kvalita OCR na technických výkresech | Střední | Střední | Hybrid přístup: AI + manuální verifikace |
| Citlivost dat (výkresy zákazníků) | Nízká | Vysoký | On-premise, šifrování, přístupová práva |

---

## 13. Budget odhad

| Položka | Měsíční náklad | Poznámka |
|---|---|---|
| AI API (Claude) | 5 000–15 000 CZK | Dle objemu zpracovaných dokumentů |
| Server (on-premise) | 3 000 CZK (amortizace) | Dedikovaný server / NAS |
| Development tým | Dle implementace | AI agenti / externí dev tým |
| Pohoda licence (upgrade) | 0–5 000 CZK | Může vyžadovat vyšší edici pro XML API |
| Školení | Jednorázově 20 000 CZK | Workshop pro klíčové uživatele |

---

## 14. Přílohy

### A. Kontextové instrukce pro AI agenty

Každý AI agent v systému **inferbox** má přístup k tomuto PRD jako ke svému primárnímu kontextovému dokumentu. Agenti se řídí následujícími pravidly:

1. **Vždy pracuj v kontextu strojírenské výroby** — terminologie, normy, materiály
2. **Respektuj ISO 9001** — trasovatelnost, dokumentace, verzování
3. **Komunikuj česky** — emaily, nabídky, průvodky v češtině
4. **Eskaluj nejistotu** — pokud si agent není jistý klasifikací (< 80% confidence), eskaluje na člověka
5. **Loguj vše** — každá akce má audit záznam
6. **Preferuj bezpečnost** — citlivá data zůstávají on-premise

### B. Slovník pojmů

| Pojem | Význam |
|---|---|
| BOM | Bill of Materials — kusovník |
| NDT | Nedestruktivní testování |
| WPS | Welding Procedure Specification — svářečský postup |
| WPQR | Welding Procedure Qualification Record |
| DN | Diameter Nominal — jmenovitý průměr potrubí |
| PN | Pressure Nominal — jmenovitý tlak |
| DWG | AutoCAD výkresový formát |
| STEP | Standard for Exchange of Product Data (CAD formát) |
| mServer | Pohoda XML API server |

---

*Tento dokument slouží jako primární zdroj pravdy pro developerský tým projektu **inferbox**. Veškeré změny procházejí schválením Product & Engineering Leadera.*

**Připravil:** AI Product Architect  
**Pro:** Infer s.r.o. — Ing. Lukáš Benček, Ing. Martin Tůma  
**Datum:** 7. února 2026
