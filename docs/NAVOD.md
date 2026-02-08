# INFER FORGE -- Uzivatelska prirucka

> Verze 1.0 | Aktualizace: unor 2026 | Platforma: INFER FORGE v1.0
> Provozovatel: Infer s.r.o. (ICO: 04856562)

---

## Obsah

- [1. Uvod](#1-uvod)
  - [1.1 Co je INFER FORGE](#11-co-je-infer-forge)
  - [1.2 Pro koho je urcen](#12-pro-koho-je-urcen)
  - [1.3 Systemove pozadavky](#13-systemove-pozadavky)
  - [1.4 Pristup do aplikace](#14-pristup-do-aplikace)
- [2. Prihlaseni a navigace](#2-prihlaseni-a-navigace)
  - [2.1 Prihlasovaci stranka](#21-prihlasovaci-stranka)
  - [2.2 Hlavni menu (sidebar)](#22-hlavni-menu-sidebar)
  - [2.3 Notifikace](#23-notifikace)
  - [2.4 Odhlaseni](#24-odhlaseni)
- [3. Dashboard](#3-dashboard)
  - [3.1 KPI karty](#31-kpi-karty)
  - [3.2 Doporucene akce (AI)](#32-doporucene-akce-ai)
  - [3.3 Pipeline graf](#33-pipeline-graf)
  - [3.4 Posledni zakazky](#34-posledni-zakazky)
- [4. Sprava zakazek](#4-sprava-zakazek)
  - [4.1 Seznam zakazek](#41-seznam-zakazek)
  - [4.2 Quick filtry a bulk akce](#42-quick-filtry-a-bulk-akce)
  - [4.3 Vytvoreni nove zakazky](#43-vytvoreni-nove-zakazky)
  - [4.4 Detail zakazky](#44-detail-zakazky)
  - [4.5 Kanban board (Pipeline)](#45-kanban-board-pipeline)
- [5. Kalkulace](#5-kalkulace)
  - [5.1 Seznam kalkulaci](#51-seznam-kalkulaci)
  - [5.2 Detail kalkulace](#52-detail-kalkulace)
  - [5.3 AI kalkulace](#53-ai-kalkulace)
  - [5.4 Schvaleni a export](#54-schvaleni-a-export)
  - [5.5 Detekce anomalii](#55-detekce-anomalii)
- [6. Dokumenty](#6-dokumenty)
  - [6.1 Sprava dokumentu](#61-sprava-dokumentu)
  - [6.2 Upload dokumentu](#62-upload-dokumentu)
  - [6.3 AI analyza vykresu](#63-ai-analyza-vykresu)
  - [6.4 Vyhledavani](#64-vyhledavani)
- [7. Email a komunikace](#7-email-a-komunikace)
  - [7.1 Inbox](#71-inbox)
  - [7.2 AI klasifikace](#72-ai-klasifikace)
  - [7.3 Automaticka orchestrace](#73-automaticka-orchestrace)
  - [7.4 Vytvoreni zakazky z emailu](#74-vytvoreni-zakazky-z-emailu)
- [8. Materialy a subdodavatele](#8-materialy-a-subdodavatele)
  - [8.1 Cenik materialu](#81-cenik-materialu)
  - [8.2 Subdodavatele](#82-subdodavatele)
- [9. Pohoda integrace](#9-pohoda-integrace)
  - [9.1 Prehled synchronizace](#91-prehled-synchronizace)
  - [9.2 Synchronizace zakazniku](#92-synchronizace-zakazniku)
  - [9.3 Synchronizace zakazek](#93-synchronizace-zakazek)
  - [9.4 Synchronizace skladu](#94-synchronizace-skladu)
  - [9.5 Reseni problemu](#95-reseni-problemu)
- [10. Reporting a analyzy](#10-reporting-a-analyzy)
  - [10.1 Dashboard statistik](#101-dashboard-statistik)
  - [10.2 Report trzeb](#102-report-trzeb)
  - [10.3 Vyrobni report](#103-vyrobni-report)
  - [10.4 Report zakazniku](#104-report-zakazniku)
  - [10.5 AI Insights](#105-ai-insights)
  - [10.6 Export a tisk](#106-export-a-tisk)
- [11. Trziste ukolu a gamifikace](#11-trziste-ukolu-a-gamifikace)
  - [11.1 Trziste ukolu](#111-trziste-ukolu)
  - [11.2 Bodovy system](#112-bodovy-system)
  - [11.3 Zebricek](#113-zebricek)
- [12. Nastaveni a automatizace](#12-nastaveni-a-automatizace)
  - [12.1 Profil uzivatele](#121-profil-uzivatele)
  - [12.2 Feature flags](#122-feature-flags)
  - [12.3 Stav integraci](#123-stav-integraci)
  - [12.4 Automatizacni pipeline](#124-automatizacni-pipeline)
  - [12.5 Dead Letter Queue](#125-dead-letter-queue)
  - [12.6 Test email pipeline](#126-test-email-pipeline)
  - [12.7 Hromadny upload EML](#127-hromadny-upload-eml)
- [13. FAQ a reseni problemu](#13-faq-a-reseni-problemu)

---

## 1. Uvod

### 1.1 Co je INFER FORGE

INFER FORGE je automatizacni platforma navrzena pro strojirenske firmy. Integruje spravu zakazek, kalkulaci, dokumentu, emailove komunikace a ucetniho systemu Pohoda do jednoho nastroje s podporou umele inteligence.

Platforma pokryva cely zivotni cyklus zakazky:

1. **Prijem poptavky** -- email nebo rucni zadani
2. **Klasifikace** -- AI automaticky rozpozna typ zpravy (poptavka, objednavka, reklamace...)
3. **Vytvoreni zakazky** -- automaticky z emailu nebo rucne
4. **Kalkulace** -- AI navrhne polozky a ceny na zaklade historickych dat
5. **Vyroba** -- sledovani pres Kanban board
6. **Fakturace** -- export do ucetniho systemu Pohoda
7. **Reporting** -- prehledy, trendy a AI doporuceni

### 1.2 Pro koho je urcen

| Role | Popis | Typicke pouziti |
|------|-------|-----------------|
| **Administrator** | Sprava systemu, uzivatelu, integraci | Nastaveni, feature flags, automatizace |
| **Obchodnik** | Komunikace se zakazniky, nabidky | Inbox, zakazky, kalkulace, Pohoda |
| **Technolog** | Vyrobni priprava, kalkulace | Zakazky, kalkulace, dokumenty, materialy |
| **Vedeni** | Strategicke rozhodovani | Dashboard, reporting, kanban |
| **Ucetni** | Fakturace, Pohoda | Pohoda, zakazky (stav fakturace) |

### 1.3 Systemove pozadavky

- **Prohlizec:** Google Chrome 100+, Mozilla Firefox 100+, Microsoft Edge 100+
- **Rozliseni:** doporuceno 1920x1080 a vyssi; responsivni layout pro tablety (1024px+)
- **Pripojeni:** stabilni internetove pripojeni (aplikace bezi on-premise)
- **JavaScript:** musi byt povoleny

### 1.4 Pristup do aplikace

Aplikace je dostupna na adrese:

```
http://91.99.126.53:3000
```

Vychozi ucet pro testovani:
- **Email:** `admin@infer.cz`
- **Heslo:** `admin123`

> **Upozorneni:** Po prvnim prihlaseni doporucujeme zmenit heslo v sekci Nastaveni.

---

## 2. Prihlaseni a navigace

### 2.1 Prihlasovaci stranka

*(viz screenshot `screenshots/pages/01-login.png`)*

1. Otevrete adresu aplikace v prohlizeci.
2. Zadejte svuj **email** do pole "E-mail".
3. Zadejte **heslo** do pole "Heslo".
4. Kliknete na tlacitko **"Prihlasit se"**.

Po uspesnem prihlaseni budete presmerovani na Dashboard.

V pripade chybneho hesla se zobrazi cervena hlaska "Nespravny email nebo heslo". Po 5 neuspesnych pokusech je ucet docasne zablokovan na 15 minut.

### 2.2 Hlavni menu (sidebar)

*(viz screenshot `screenshots/pages/02-dashboard.png`)*

Po prihlaseni se vlevo zobrazi bocni menu (sidebar) s nasledujicimi polozkami:

| Ikona | Polozka | Cesta | Popis |
|-------|---------|-------|-------|
| Dashboard | Dashboard | `/dashboard` | Hlavni prehled, KPI, doporuceni |
| Seznam | Zakazky | `/zakazky` | Sprava zakazek a objednavek |
| Kanban | Pipeline | `/kanban` | Kanban board vyrobnich fazi |
| Pohar | Trziste ukolu | `/trziste-ukolu` | Prirazovani ukolu, zebricek |
| Kalkulacka | Kalkulace | `/kalkulace` | Naceneni zakazek |
| Graf | Reporting | `/reporting` | Prehledy a analyzy |
| Schranka | Inbox | `/inbox` | Prichozi emaily |
| Dokument | Dokumenty | `/dokumenty` | Sprava souboru a vykresu |
| Balicek | Cenik materialu | `/materialy` | Databaze materialu a cen |
| Handshake | Subdodavatele | `/subdodavatele` | Evidence subdodavatelu |
| Procesor | Automatizace | `/automatizace` | Orchestracni pipeline |
| Synchronizace | Pohoda | `/pohoda` | Integrace s ucetnictvim |
| Prezentace | Prezentace | `/prezentace` | Prezentacni rezimy |
| Ozubene kolo | Nastaveni | `/nastaveni` | Konfigurace a profil |

**Sbaleni sidebaru:** Kliknutim na sipku vlevo v hlavicce sidebaru jej lze sbalit na ikonovou lisu (pouze ikony bez textu). Opetovnym kliknutim se sidebar rozbali.

**Prihlaseny uzivatel:** Ve spodni casti sidebaru se zobrazuje jmeno a email aktualniho uzivatele.

### 2.3 Notifikace

V pravem hornim rohu se nachazi ikona zvonecku s poctem neprectenych notifikaci. Notifikace informuji o:

- Nove prichozi emaily
- Zmeny stavu zakazek
- Dokonceni automatickych kalkulaci
- Chyby v orchestracnim pipeline

Kliknutim na zvonecek se rozbali panel s poslednimi notifikacemi.

### 2.4 Odhlaseni

Kliknete na tlacitko **"Odhlasit se"** ve spodni casti sidebaru. Budete presmerovani na prihlasovaci stranku.

---

## 3. Dashboard

*(viz screenshot `screenshots/pages/02-dashboard.png`, `screenshots/pages/18-dashboard-full.png`)*

Dashboard je hlavni strana po prihlaseni. Poskytuje rychly prehled stavu firmy.

### 3.1 KPI karty

V horni casti Dashboard se nachazi 4 statisticke karty:

| Karta | Popis | Zdroj dat |
|-------|-------|-----------|
| **Aktivni zakazky** | Celkovy pocet zakazek v systemu | Vsechny zakazky |
| **Ve vyrobe** | Zakazky v aktualni fazi vyroby | Zakazky se stavem "vyroba" |
| **Nove zpravy** | Neprecetene emaily v inboxu | Inbox se stavem "new" |
| **K fakturaci** | Zakazky pripravene k fakturaci | Zakazky se stavem "fakturace" |

Karty se automaticky aktualizuji pri kazdem naceteni stranky.

### 3.2 Doporucene akce (AI)

Pod KPI kartami se nachazi widget **"Doporucene akce"**, ktery na zaklade analyzy stavu systemu navrhuje az 5 nejdulezitejsich akci. Kazda akce ma barevnou indikaci zavaznosti:

| Barva | Zavaznost | Priklad |
|-------|-----------|---------|
| **Cervena** | Kriticka | Zakazky po terminu |
| **Zluta** | Varovani | Neschvalene kalkulace starsi 3 dnu |
| **Modra** | Informacni | Neprirazene zakazky |

Typy doporuceni:
- **Zakazky po terminu** -- zakazky, ktere prekrocily deadline
- **Neschvalene kalkulace** -- kalkulace cekajici na schvaleni dele nez 3 dny
- **Neprirazene zakazky** -- zakazky bez prideleneho pracovnika
- **Emaily cekajici na odpoved** -- emaily v inboxu starsi 24 hodin
- **Kalkulace bez nabidky** -- schvalene kalkulace, ke kterym nebyla odeslana nabidka

Kliknutim na doporuceni se presmerovane na prislusnou stranku (napr. na detail zakazky).

Pokud nejsou zadne urgentni akce, zobrazi se zelena hlaska **"Vse v poradku -- Zadne urgentni akce k vyrizeni"**.

Widget se automaticky aktualizuje kazdou minutu.

### 3.3 Pipeline graf

Sloupcovy graf zobrazuje rozlozeni zakazek podle stavu (poptavka, nabidka, objednavka, priprava, vyroba, kontrola, fakturace). Umoznuje rychle vizualne posoudit, kde se nachazeji bottlenecky.

### 3.4 Posledni zakazky

Tabulka poslednich 10 zakazek serazenych od nejnovejsi. Zobrazuje:
- Cislo zakazky (kliknutelne -- presmerovani na detail)
- Zakaznik
- Stav (barevny badge)
- Priorita
- Datum vytvoreni

---

## 4. Sprava zakazek

### 4.1 Seznam zakazek

*(viz screenshot `screenshots/pages/03-zakazky.png`)*

Stranka `/zakazky` zobrazuje kompletni seznam vsech zakazek s moznosti filtrovani a vyhledavani.

**Filtrovani podle stavu:** V horni casti se nachazi roletka pro filtrovani zakazek podle stavu:
- Vse
- Poptavka
- Nabidka
- Objednavka
- Priprava
- Vyroba
- Kontrola
- Fakturace
- Dokoncena
- Stornovana

**Textove vyhledavani:** Pole pro fulltextove hledani v cisle zakazky, nazvu zakaznika a kontaktni osobe.

### 4.2 Quick filtry a bulk akce

Pod vyhledavacim polem se nachazi radek s rychlymi filtry (round buttony):

| Filtr | Funkce |
|-------|--------|
| **Vse** | Zobrazit vsechny zakazky |
| **Po terminu** | Zakazky s prekrocenym deadlinem |
| **Vysoka priorita** | Zakazky s prioritou "high" nebo "urgent" |
| **Neprirazene** | Zakazky bez prideleneho pracovnika |
| **Nove poptavky** | Zakazky ve stavu "poptavka" |

**Bulk akce:** Zaznacenim vice zakazek (checkboxy) se aktivuje lista hromadnych akci:
- Zmena stavu vybranych zakazek
- Prirazeni pracovnika

### 4.3 Vytvoreni nove zakazky

1. Na strance Zakazky kliknete na tlacitko **"Nova zakazka"** (v pravem hornim rohu).
2. Otevre se dialog s formularem:
   - **Cislo zakazky** -- automaticky predvyplneno (format ZAK-XXX)
   - **Zakaznik** -- vyber z existujicich zakazniku
   - **Priorita** -- automaticky nastavena dle kategorie zakaznika
   - **Termin** -- automaticky nastaven na +14 dnu od dnesniho data
   - **Poznamka** -- volitelny popis
3. Kliknete na **"Vytvorit"**.

> **Tip:** Zakazky lze take vytvaret automaticky z prichozich emailu (viz kapitola 7.4).

### 4.4 Detail zakazky

*(viz screenshot `screenshots/pages/14-zakazka-detail-top.png`, `screenshots/pages/18-zakazka-detail-full.png`)*

Detail zakazky (`/zakazky/[id]`) obsahuje nasledujici sekce:

**Hlavicka:**
- Cislo zakazky
- Nazev zakaznika (kliknutelny odkaz)
- Stav (barevny badge s moznosti zmeny)
- Priorita (barevny badge)
- Termin dokonceni
- Badge **"Vytvoreno automaticky"** -- pokud byla zakazka vytvorena z emailu orchestracnim pipeline

**Polozky zakazky (BOM -- Bill of Materials):**

*(viz screenshot `screenshots/pages/15-zakazka-detail-items.png`)*

Tabulka materialu a komponent potrebnych pro zakazku:
- Nazev polozky
- Pocet kusu
- Jednotkova cena
- Celkova cena

Polozky lze pridavat, editovat a mazat.

**Operace (vyrobni kroky):**

*(viz screenshot `screenshots/pages/16-zakazka-operace.png`)*

Seznam vyrobnich operaci s moznosti sledovani prubchu:
- Nazev operace (napr. "Rezani", "Svarovani", "Povrchova uprava")
- Casovy odhad
- Stav dokonceni

**Dokumenty:**

*(viz screenshot `screenshots/pages/17-zakazka-dokumenty.png`)*

Prilohy prirazene k zakazce:
- Vykresy (PDF, DXF, DWG)
- Technologicke postupy
- Atestace materialu
- Upload novych dokumentu

**Podobne zakazky (AI):**

Sekce zobrazuje az 5 historicky podobnych zakazek nalezenych pomoci AI embedding vyhledavani. U kazde podobne zakazky je uvedeno:
- Cislo zakazky
- Zakaznik
- Podobnost (procenta)

Tato funkce pomaha pri naceneni -- muzete se podivat, jak byly podobne zakazky v minulosti nakalkulovany.

**Kalkulace:**

Tlacitka pro praci s kalkulacemi:
- **"Vytvorit kalkulaci"** -- rucni kalkulace
- **"AI Kalkulace"** -- automaticky navrh polozek a cen pomoci Claude API

**AI predikce terminu:**

Na zaklade historickych dat a slozitosti zakazky AI predikuje realisticky termin dokonceni. Pokud se lisi od zadaneho terminu, zobrazi se varovani.

### 4.5 Kanban board (Pipeline)

*(viz screenshot `screenshots/pages/04-kanban.png`)*

Stranka `/kanban` zobrazuje vizualni prehled zakazek v jednotlivych fazich vyroby.

**7 sloupcu:**

| Sloupec | Popis |
|---------|-------|
| Poptavka | Nove poptavky cekajici na zpracovani |
| Nabidka | Poptavky s odeslanou nabidkou |
| Objednavka | Potvrzene objednavky |
| Priprava | Vyrobni priprava (material, technologie) |
| Vyroba | Aktivni vyroba |
| Kontrola | Kontrola kvality |
| Fakturace | Dokoncene zakazky k fakturaci |

**Pouziti:**
1. **Presun karty:** Uchopte kartu zakazky a pretahnete ji do jineho sloupce. Stav zakazky se automaticky aktualizuje.
2. **WIP limit:** Kazdy sloupec ma maximalni kapacitu 8 zakazek. Pokud je sloupec plny, jeho hlavicka se podbarvi cervene.
3. **Na karte se zobrazuje:** cislo zakazky, nazev zakaznika, priorita (barevny badge), termin dokonceni.
4. **Filtr "Jen moje zakazky":** Zaskrtavaci pole v pravem hornim rohu, ktere zobrazi pouze zakazky prirazene aktualnimu uzivateli.

> **Tip:** Kanban board je idealni pro ranni standup schuzky -- rychle vizualizuje stav vsech zakazek.

---

## 5. Kalkulace

### 5.1 Seznam kalkulaci

*(viz screenshot `screenshots/pages/05-kalkulace.png`)*

Stranka `/kalkulace` zobrazuje seznam vsech kalkulaci s moznosti filtrovani podle stavu:
- Koncept (draft)
- Odeslana
- Schvalena
- Zamitnuta

### 5.2 Detail kalkulace

*(viz screenshot `screenshots/pages/17-kalkulace-detail.png`, `screenshots/07-calculation-detail.png`)*

Detail kalkulace (`/kalkulace/[id]`) obsahuje:

**Kalkulacni polozky:**
Tabulka rozdelena na kategorie:
- **Material** -- ocel, pridelany material, spojovaci material
- **Prace** -- svarovani, obrrabeni, montaz, povrchova uprava
- **Rezie** -- doprava, zkousinky (NDT), certifikace, administrativa

Kazda polozka ma:
- Nazev
- Pocet (mn.)
- Jednotka (ks, kg, hod, m)
- Jednotkova cena (Kc)
- Celkem (Kc)

**Souhrn:**
- Celkova cena materialu
- Celkova cena prace
- Rezie
- **Celkova cena** (soucet vsech polozek)
- Marze (procenta a absolutni castka)

### 5.3 AI kalkulace

Funkce **"AI Kalkulace"** vyuziva Claude API pro automaticky navrh kalkulacnich polozek:

1. V detailu zakazky kliknete na tlacitko **"AI Kalkulace"**.
2. System odesle popis zakazky, BOM a informace o podobnych historickych zakazkach do AI.
3. AI navrhne kompletni kalkulaci vcetne:
   - Odhadu materialu a mnozstvi
   - Casoveho odhadu vyrobnich operaci
   - Navrzene ceny s prizpussobenou marzi
4. Navrhnutou kalkulaci muzete upravit pred ulozenim.

> **Poznamka:** AI kalkulace je navrh -- vzdy ji zkontrolujte a prizpusobte dle aktualniho stavu trhu a specifik zakazky.

### 5.4 Schvaleni a export

**Proces schvaleni:**
1. Technolog nebo obchodnik vytvori kalkulaci (rucne nebo AI).
2. Kalkulaci zkontroluje vedouci.
3. Kliknete na **"Schvalit"** (zelene tlacitko) nebo **"Zamitnout"** (cervene tlacitko).
4. Schvalena kalkulace se pouzije pro generovani nabidky.

**Export do PDF:**
- Kliknete na tlacitko **"Export PDF"** pro stazeni kalkulace v tiskovem formatu.
- PDF obsahuje kompletni rozpis polozek, souhrn a logo firmy.

### 5.5 Detekce anomalii

System automaticky analyzuje marzi kalkulace. Pokud se marze nachazi mimo normalin rozmezi (nastavenem na zaklade historickych dat), zobrazi se varovani:

- **Prilis nizka marze** (< 10 %) -- cervene varovani
- **Neobvykle vysoka marze** (> 45 %) -- zlute varovani

Anomalie neblokuji schvaleni, slouczi pouze jako upozorneni pro kontrolu.

---

## 6. Dokumenty

### 6.1 Sprava dokumentu

*(viz screenshot `screenshots/pages/06-dokumenty.png`)*

Stranka `/dokumenty` zobrazuje vsechny dokumenty prirazene k zakazkam.

Tabulka obsahuje:
- Nazev souboru
- Typ dokumentu (vykres, atestace, technologie, fotografie...)
- Prirazena zakazka
- Datum nahrfani
- Velikost

### 6.2 Upload dokumentu

**Nahrfani noveho dokumentu:**
1. Kliknete na tlacitko **"Nahrat dokument"**.
2. Vyberte soubor z pocitace (podporovane formaty: PDF, DXF, DWG, XLSX, DOCX, JPG, PNG).
3. Vyberte zakazku, ke ktere dokument patri.
4. Vyberte typ dokumentu.
5. Kliknete na **"Nahrat"**.

**Hromadne stazeni:**
Zaznacenim vice dokumentu a kliknutim na **"Stahnout (ZIP)"** se vsechny vybrane soubory stahnou v jednom ZIP archivu.

### 6.3 AI analyza vykresu

Po nahrfani technickych vykresu (PDF, DXF) muze AI automaticky analyzovat obsah a extrahovat:
- **DN/PN** -- jmenovity prumer a tlak
- **Material** -- typ oceli (napr. P265GH, 11 523)
- **Rozmery** -- delky, prumery, tloustrky stien
- **Pocet kusu**
- **Normy** -- referencovane normy (EN, DIN, CSN)

Vysledky analyzy se zobrazi u dokumentu a jsou pouzity pro upresneni kalkulace.

### 6.4 Vyhledavani

**Semanticke vyhledavani (AI):**
Pole pro vyhledavani umoznuje hledat v obsahu dokumentu pomoci prirozeneho jazyka. Napr.:
- "priruba DN200 PN16"
- "ocel P265GH tloust'ka 10mm"
- "svavovaci postup WPS"

Vyhledavani vyuziva OCR textu z nahrangych dokumentu a AI embeddingy pro nalezeni relevantniho obsahu.

---

## 7. Email a komunikace

### 7.1 Inbox

*(viz screenshot `screenshots/pages/08-inbox.png`)*

Stranka `/inbox` zobrazuje prichozi emaily z nastaveneho IMAP uctu.

**Zaclozky (taby):**

| Tab | Popis |
|-----|-------|
| **Vse** | Vsechny zpravy |
| **Nove** | Neprecetene zpravy cekajici na zpracovani |
| **Klasifikovane** | Zpravy zpracovane AI klasifikaci |
| **Prirazene** | Zpravy prirazene k zakazkam |

Kazdy tab zobrazuje pocet zprav ve svem stavu.

**Informacni badges:**
- Zeleny badge: "X prirazeno k zakazkam"
- Modry badge: "X ceka na zpracovani"

### 7.2 AI klasifikace

Kazdy prichozi email je automaticky klasifikovan pomoci AI do jedne z kategorii:

| Kategorie | Popis | Akce |
|-----------|-------|------|
| **Poptavka** | Zakaznik se pta na cenu / moznost vyroby | Vytvorit zakazku |
| **Objednavka** | Zakaznik potvrzuje objednavku | Vytvorit zakazku |
| **Reklamace** | Zakaznik nahlasuje problem | Prioritni reseni |
| **Dotaz** | Obecny dotaz | Odpovedet |
| **Faktura** | Fakturacni zalezitost | Presmerovat na ucetni |

U kazde zpravy se zobrazuje:
- **Klasifikace** -- kategorie s barevnym badge
- **Confidence score** -- spolehlivost klasifikace (0-100 %)
  - Zelena: > 80 % (vysoka spolehlivost)
  - Zluta: 50-80 % (stredni)
  - Cervena: < 50 % (nizka -- doporucena rucni kontrola)
- **Pipeline status** -- stav zpracovani (Zpracovano / Chyba / Ceka)

### 7.3 Automaticka orchestrace

Pokud je v Nastaveni aktivovan flag `ORCHESTRATION_ENABLED`, emaily prochazi automatickym pipeline:

```
Prijem emailu --> Klasifikace (AI) --> Parsovani --> Orchestrace --> [Kalkulace] --> [Nabidka]
```

Jednotlive kroky:
1. **Prijem (Ingest)** -- email je stazen z IMAP a ulozen do databaze
2. **Klasifikace (Classify)** -- AI urceni kategorie (poptavka, objednavka...)
3. **Parsovani (Parse)** -- extrakce strukturovangch dat (firma, kontakt, polozky)
4. **Orchestrace (Orchestrate)** -- nalezeni/vytvoreni zakaznika, vytvoreni zakazky
5. **Kalkulace (Calculate)** -- AI navrh kalkulace (pokud je aktivni `AUTO_CALCULATE`)
6. **Nabidka (Offer)** -- generovani nabidky (pokud je aktivni `AUTO_OFFER`)

### 7.4 Vytvoreni zakazky z emailu

**Rucni vytvoreni:**
1. V Inboxu najdete prislusny email.
2. Kliknete na tlacitko **"Vytvorit zakazku"** (1-click orchestrace).
3. System automaticky:
   - Identifikuje nebo vytvori zakaznika
   - Vytvori zakazku s predvyplnenymi daty z emailu
   - Priradi email k zakazce

**Automaticke vytvoreni:**
Pokud je aktivni flag `AUTO_CREATE_ORDERS`, system automaticky vytvari zakazky z emailu klasifikovangch jako "poptavka" nebo "objednavka".

---

## 8. Materialy a subdodavatele

### 8.1 Cenik materialu

*(viz screenshot `screenshots/pages/09-materialy.png`)*

Stranka `/materialy` obsahuje databazi materialu a jejich cen.

**Funkce:**
- **Seznam materialu** -- tabulka s nazvy, specifikacemi a cenami
- **Vyhledavani** -- fulltextove hledani + fuzzy autocomplete (pouziva se pri tvorbe kalkulaci)
- **CRUD operace** -- pridani, editace a smazani materialu
- **Excel import** -- hromadne nacteni cen z Excel souboru

**Pridani noveho materialu:**
1. Kliknete na **"Pridat material"**.
2. Vyplnte nazev, specifikaci (napr. "P265GH, tl. 10 mm"), jednotku a cenu.
3. Kliknete na **"Ulozit"**.

**Import z Excelu:**
1. Kliknete na **"Import z Excelu"**.
2. Vyberte soubor .xlsx se sloupci: Nazev, Specifikace, Jednotka, Cena.
3. System nacte data a zobrazi nahlled.
4. Potvrdite import.

> **Tip:** Funkce **"Najit nejlepsi cenu"** automaticky vyhledava nejlevnejsi dostupny material odpovidajici specifikaci.

### 8.2 Subdodavatele

*(viz screenshot `screenshots/pages/10-subdodavatele.png`)*

Stranka `/subdodavatele` obsahuje evidenci subdodavatelu firmy.

**Udaje o subdodavateli:**
- Nazev firmy, ICO
- Kontaktni osoba, telefon, email
- Specializace (svarovani, obrrabeni, povrchove upravy, doprava...)
- Hodnoceni (hvezdicky)
- Propojeni se zakazkami

---

## 9. Pohoda integrace

*(viz screenshot `screenshots/pages/11-pohoda.png`)*

### 9.1 Prehled synchronizace

Stranka `/pohoda` zobrazuje stav synchronizace s ucetnim systemem Pohoda (Stormware).

**Log synchronizace:**
Tabulka vsech synchronizacnich operaci s informacemi:
- Typ entity (zakazka, zakaznik, faktura, nabidka)
- Smer (export do Pohody / import z Pohody)
- Stav (ceka / uspech / chyba)
- Datum a cas

**Filtr podle typu entity:**
Roletka pro filtrovani logu podle typu: Vse / Zakazka / Zakaznik / Faktura / Nabidka.

### 9.2 Synchronizace zakazniku

**Export zakaznika do Pohody:**
1. V sekci "Synchronizace zakazniku" vyberte zakaznika z roletky.
2. Kliknete na **"Sync do Pohody"** (ikona Upload).
3. System vytvori XML v kodovani Windows-1250 a odesle do Pohody.
4. Vysledek se zapise do logu.

### 9.3 Synchronizace zakazek

**Export zakazky do Pohody:**
1. V sekci "Synchronizace zakazek" vyberte zakazku z roletky.
2. Kliknete na **"Sync do Pohody"** (ikona Upload).
3. Zakazka se exportuje jako objednavka (`ord:order`) do Pohody.

### 9.4 Synchronizace skladu

**Sync skladu:**
Kliknete na tlacitko **"Sync sklad"** (ikona Sklad) pro synchronizaci skladovgch polozek s Pohodou.

### 9.5 Reseni problemu

| Problem | Reseni |
|---------|--------|
| Chyba "Connection refused" | Overtte, ze Pohoda mServer bezi a je dostupny |
| Chyba v kodovani | XML musi byt v Windows-1250, nikoli UTF-8 |
| Duplicitni zaznamy | Zkontrolujte unikatni cisla dokladu s prefixem |
| Timeout | Zvyste cas timeoutu v Nastaveni integrace |

> **Dulezite:** Vsechna XML data jsou validovana proti XSD schematu pred odeslanim. Pokud validace selze, operace se neprovede a zobrazi se chybova hlaska.

---

## 10. Reporting a analyzy

*(viz screenshot `screenshots/pages/07-reporting.png`, `screenshots/pages/19-reporting-full.png`)*

### 10.1 Dashboard statistik

Stranka `/reporting` obsahuje 4 zaclozky (taby):

**Tab "Dashboard":**
8 statistickych karet:
- Celkem zakazek
- Ve vyrobe
- Nove zpravy
- Ceka fakturaci
- Dokumenty
- Kalkulace
- Celkovy obrat
- Po terminu

Dale obsahuje graficky prehled pipeline zakazek -- horizontalni sloupce zobrazujici podil zakazek v kazdem stavu.

### 10.2 Report trzeb

**Tab "Trzby":**
- Mesicni prehled trzeb (tabulka po mesicich)
- Trendy za 12 mesicu
- Porovnani s predchozim obdobim

### 10.3 Vyrobni report

**Tab "Vyroba":**
- Pocet zakazek ve vyrobni fazi
- Prumerna doba vyroby
- Rozlozeni podle priorit
- Prehled podle stavu

### 10.4 Report zakazniku

**Tab "Zakaznici":**
- Top 10 zakazniku podle obratu
- Pocet zakazek na zakaznika
- Prumerna hodnota zakazky
- Kategorie zakazniku (A/B/C)

### 10.5 AI Insights

Tlacitko **"AI Insights"** (ikona zarovky) spusti analyzu dat pomoci Claude API. System vygeneruje 3-5 textovgch doporuceni, napr.:

- "Zakaznik XY ma o 30 % vyssi objem zakazek nez loni -- zvazrte nabidku ramcove smlouvy."
- "Prumerna doba zpracovani poptavky vzrostla na 4,2 dne -- doporucujeme kontrolu kapacit."
- "Material P265GH zdrazil o 12 % -- aktualizujte ceniky kalkulaci."

### 10.6 Export a tisk

- **Export PDF:** Kliknete na ikonu **"Stahnout PDF"** pro stazeni reportu.
- **Tisk:** Kliknete na ikonu **"Tisk"** -- report se pripravi v tiskovem formatu a zobrazi dialog tisku prohlizece.

---

## 11. Trziste ukolu a gamifikace

### 11.1 Trziste ukolu

Stranka `/trziste-ukolu` funguje jako marketplace pro prirazovani ukolu.

**Funkce:**
- Prehled dostupngch ukolu k prevzeti
- Filtrovani podle typu (kalkulace, vyroba, kontrola...)
- Filtrovani podle priority
- Prevzeti ukolu jednim kliknutim
- Zebricek uzivatelu s body

### 11.2 Bodovy system

Za splneni ukolu v systemu ziskavate body:

| Akce | Body |
|------|------|
| Zmena stavu zakazky | +5 bodu |
| Dokonceni kalkulace | +10 bodu |
| Schvaleni kalkulace | +5 bodu |
| Zpracovani emailu | +3 body |
| Odeslani nabidky | +8 bodu |
| Dokonceni zakazky | +15 bodu |

Body slouczi jako motivacni nastroj pro tym. Neovlivnuji pristupova prava ani plat.

### 11.3 Zebricek

Zebricek zobrazuje poradii uzivatelu podle ziskanch bodu s moznosti prepnuti obdobi:

| Obdobi | Popis |
|--------|-------|
| **Denne** | Body ziskane dnes |
| **Tyden** | Body za aktualni tyden |
| **Mesic** | Body za aktualni mesic |
| **Celkem** | Celkovy soucet bodu |

**Medaile:**
- 1. misto -- zlata medaile
- 2. misto -- stribrna medaile
- 3. misto -- bronzova medaile
- 4+ misto -- ciselne umisteni

U kazdeho uzivatele se zobrazuje jmeno, inicialy (avatar) a pocet bodu. Aktualni uzivatel je vizualne zvyraznen.

---

## 12. Nastaveni a automatizace

### 12.1 Profil uzivatele

*(viz screenshot `screenshots/pages/13-nastaveni.png`)*

Na strance `/nastaveni` se v levem panelu zobrazuje profil prihlaseneho uzivatele:
- Jmeno a prijmeni
- Role (Administrator, Obchodnik, Technolog, Vedeni, Ucetni)
- Email
- Telefon

### 12.2 Feature flags

V pravem panelu se nachazeji prepinace (toggle) pro rizeni automatizace:

| Flag | Popis | Vychozi |
|------|-------|---------|
| **ORCHESTRATION_ENABLED** | Zapnuti automatickeho zpracovani emailu | Vypnuto |
| **AUTO_CREATE_ORDERS** | Automaticke vytvareni zakazek z emailu | Vypnuto |
| **AUTO_CALCULATE** | Automaticka AI kalkulace u novych zakazek | Vypnuto |
| **AUTO_OFFER** | Automaticke generovani nabidek | Vypnuto |

**Zmena flagu:**
Kliknete na prepinac u prislusneho flagu. Zmena se projevi okamzite.

> **Varovani:** Doporucujeme zapnout flagy postupne a sledovat vysledky v sekci Automatizace pred zapnutim dalsich kroku pipeline.

### 12.3 Stav integraci

Panel zobrazujici stav pripojeni k externim sluzham:
- **Pohoda** -- zelena (pripojeno) / cervena (odpojeno)
- **Email (IMAP/SMTP)** -- stav pripojeni k postovnimu serveru
- **AI (Claude API)** -- stav API klice a kreditu

### 12.4 Automatizacni pipeline

Stranka `/automatizace` zobrazuje detailni prehled orchestracniho pipeline.

**Statisticke karty (5 karet):**

| Karta | Popis |
|-------|-------|
| **Celkem uloh** | Pocet vsech zpracovangch uloh |
| **Chybovost** | Procento neuspesnch zpracovani |
| **Tokeny celkem** | Celkovy pocet AI tokenu spotrebovangch pipeline |
| **Prum. cas** | Prumerny cas zpracovani jedne ulohy (ms) |
| **DLQ nevyreseno** | Pocet chyb cekajicich na rucni reseni |

**Rozlozeni podle fazi:**
Vizualni prehled poctu uloh v kazde fazi pipeline:
- Prijem, Klasifikace, Parsovani, OCR, Analyza, Orchestrace, Kalkulace, Nabidka

**Tabulka poslednich uloh:**
Tabulka 20 poslednich zpracovangch uloh s udaji:
- Faze (badge)
- Stav (success / failed / pending / running)
- Tokeny (spotrebovane AI tokeny)
- Cas zpracovani (ms)
- Pocet opakovani
- Datum vytvoreni

### 12.5 Dead Letter Queue

Sekce **"Dead Letter Queue"** (DLQ) zobrazuje ulohy, ktere opakovanre selhaly a vyzaduji rucni zasah.

U kazde polozky DLQ se zobrazuje:
- Nazev ulohy
- Faze pipeline
- Chybova hlaska
- Pocet opakovani
- Datum

**Akce pro kazdou polozku DLQ:**
- **Retry** -- pokus o opetovne zpracovani
- **Vyresit** -- oznaceni jako vyresene (napr. po rucnim zpracovani)

### 12.6 Test email pipeline

Na strance Automatizace se nachazi formular **"Test email pipeline"** pro otestovani celeho orchestracniho pipeline bez skutecneho emailu.

**Postup:**
1. Vyplnte pole:
   - **Od (email)** -- emailova adresa odesilatele (napr. `novak@firma.cz`)
   - **Predmet** -- predmet emailu (napr. "Poptavka na vyrobu prirub DN200")
   - **Text emailu** -- telo emailu
2. Kliknete na **"Odeslat test"**.
3. Sledujte vysledek pipeline:
   - Kazdy krok je zobrazen s poradovym cislem
   - Zelena fajfka = uspech, cerveny krizek = chyba
   - U klasifikace se zobrazuje kategorie, confidence a metoda
   - U orchestrace se zobrazi, zda byl vytvoren zakaznik a/nebo zakazka
   - Celkovy cas zpracovani (ms)

**Pipeline v realnem case:**
Pokud je aktivni WebSocket pripojeni, prubeh pipeline se zobrazuje live s animovanou indikaci aktualni faze.

### 12.7 Hromadny upload EML

Sekce **"Hromadny upload EML"** umoznuje nahrat vice EML souboru najednou pro hromadne zpracovani.

**Postup:**
1. Pretahnete .eml soubory do vyznacene oblasti (drag & drop) nebo kliknete na **"Vyberte soubory"**.
2. System kazdy soubor zpracuje pres kompletni pipeline.
3. Vysledek se zobrazi pod nahravaci zonou:
   - Pocet uspesne zpracovangch / celkovy pocet
   - Detail pro kazdy soubor (uspech / chyba)

---

## 13. FAQ a reseni problemu

### Prihlaseni a pristup

**Otazka: Zapomnel jsem heslo.**
> Kontaktujte administratora systemu pro reset hesla.

**Otazka: Zobrazuje se "Nespravny email nebo heslo".**
> Overtte spravnost emailu a hesla. Pozor na velka/mala pismena v hesle. Po 5 neuspesnch pokusech je ucet zablokovan na 15 minut.

**Otazka: Stranka se nenacita / bila obrazovka.**
> Vymazrte cache prohlizece (Ctrl+Shift+Delete) a obnovte stranku (Ctrl+F5). Pokud problem pretrvava, zkuste jiny prohlizec.

### Zakazky

**Otazka: Jak zrusit zakazku?**
> V detailu zakazky zmentte stav na "Stornovana". Stornovana zakazka zustane v systemu pro audit trail, ale nebude se zobrazovat v aktivnich prehledech.

**Otazka: Zakazka se nevytvari z emailu automaticky.**
> Overtte, ze v Nastaveni je aktivni flag `ORCHESTRATION_ENABLED` a `AUTO_CREATE_ORDERS`. Zkontrolujte stranku Automatizace pro pripadne chyby v DLQ.

### Kalkulace

**Otazka: AI kalkulace trva prilis dlouho.**
> AI kalkulace typicky trva 5-15 sekund. Pokud trva dele, muze byt pretizeny AI server. Zkuste to znovu pozdeji.

**Otazka: AI navrhla nerealistickou cenu.**
> AI kalkulace je navrh, ne finalni cena. Vzdy zkontrolujte a prizpusobte polozky. Cim vice historickych kalkulaci system obsahuje, tim presnejsi budou navrhy.

### Pohoda

**Otazka: Synchronizace s Pohodou selhava.**
> Overtte: (1) Pohoda mServer bezi, (2) spravna IP adresa a port v konfiguraci, (3) ucet ma prava pro API pristup. Detaily chyby najdete v logu na strance Pohoda.

**Otazka: V Pohode se zobrazi spatne znaky (krakozabry).**
> INFER FORGE generuje XML v kodovani Windows-1250, jak vyzaduje Pohoda. Pokud vidite spatne znaky, kontaktujte administratora -- muze se jednat o chybu v konfiguraci.

### Email

**Otazka: Emaily se nestahujji.**
> Overtte v Nastaveni, ze emailova integrace je ve stavu "Pripojeno" (zelena). Zkontrolujte IMAP nastaveni (server, port, SSL, prihlasovaci udaje).

**Otazka: Klasifikace emailu je spatna.**
> AI klasifikace neni 100% spolehlivva. U emailu s nizkym confidence (< 50 %) doporucujeme rucni kontrolu. Spravnou kategorii lze nastavit rucne.

### Obecne

**Otazka: Data se neaktualizuji.**
> Kliknete na tlacitko "Obnovit" (ikona sipek) na prislusne strance, nebo obnovte celou stranku (F5).

**Otazka: Jak exportovat data?**
> Kalkulace: Export PDF v detailu kalkulace. Reporting: tlacitko "Stahnout PDF" nebo "Tisk". Dokumenty: hromadne stazeni ZIP.

---

### Kontakt na podporu

V pripade technickych problemu kontaktujte:

- **Email:** podpora@infer.cz
- **Telefon:** +420 XXX XXX XXX
- **Interni ticket:** Vytvorte pozadavek v systemu (menu Nastaveni)

---

> **INFER FORGE** -- Automatizacni platforma pro strojirenstvi
> (c) 2026 Infer s.r.o. | Vsechna prava vyhrazena.
