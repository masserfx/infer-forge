# INFER FORGE Zálohovací Systém

Automatizované denní a týdenní zálohy databáze PostgreSQL a nahraných souborů.

## Přehled

- **Denní záloha:** Každý den v 2:00 (retention 7 dní)
- **Týdenní záloha:** Každou neděli ve 3:00 (retention 90 dní)
- **Zálohuje:** PostgreSQL databáze + uploads volume
- **Umístění:** `/opt/infer-forge/backups/`
- **Logy:** `/var/log/infer-forge-backup.log`

## Instalace

Na produkčním serveru (jako root):

```bash
cd /opt/infer-forge
sudo ./scripts/backup-cron.sh
```

Tento příkaz:
- Vytvoří `/opt/infer-forge/backups/` adresář
- Nastaví oprávnění pro skripty
- Nainstaluje cron jobs pro automatické zálohy

## Struktura Záloh

### Denní zálohy
```
/opt/infer-forge/backups/
├── infer-forge-backup-2026-02-08-020000.sql.gz
├── infer-forge-backup-2026-02-09-020000.sql.gz
├── uploads-2026-02-08.tar.gz
└── uploads-2026-02-09.tar.gz
```

### Týdenní zálohy
```
/opt/infer-forge/backups/
├── infer-forge-weekly-2026-02-02-030000.sql.gz
├── infer-forge-weekly-2026-02-09-030000.sql.gz
├── uploads-weekly-2026-02-02.tar.gz
└── uploads-weekly-2026-02-09.tar.gz
```

## Retention Policy

| Typ zálohy | Frekvence | Retention | Účel |
|-----------|-----------|-----------|------|
| Denní | Každý den 2:00 | 7 dní | Rychlý rollback |
| Týdenní | Neděle 3:00 | 90 dní | Dlouhodobé uchovávání |

Automatická rotace:
- **7 denních** záloh (nejnovější)
- **4 týdenní** zálohy (poslední měsíc)
- **3 měsíční** zálohy (first weekly of month, až 90 dní)

## Manuální Použití

### Denní záloha (ručně)
```bash
cd /opt/infer-forge
./scripts/backup_db.sh
```

### Týdenní záloha (ručně)
```bash
cd /opt/infer-forge
./scripts/backup_db.sh --weekly
```

### Obnovení databáze
```bash
# Pouze databáze
./scripts/restore_db.sh /opt/infer-forge/backups/infer-forge-backup-2026-02-08-020000.sql.gz

# Databáze + uploads
./scripts/restore_db.sh \
  /opt/infer-forge/backups/infer-forge-backup-2026-02-08-020000.sql.gz \
  /opt/infer-forge/backups/uploads-2026-02-08.tar.gz
```

**Restore proces:**
1. Vytvoří safety backup současné databáze
2. Potvrzení uživatelem (yes/no prompt)
3. Dropne a znovu vytvoří databázi
4. Obnoví data ze zálohy
5. Obnoví uploads (pokud zadáno)
6. Spustí Alembic migrace
7. V případě chyby obnoví safety backup

### Seznam dostupných záloh
```bash
ls -lh /opt/infer-forge/backups/*.sql.gz
```

### Sledování logů
```bash
# Live sledování
tail -f /var/log/infer-forge-backup.log

# Poslední záloha
tail -100 /var/log/infer-forge-backup.log

# Chyby
grep ERROR /var/log/infer-forge-backup.log
```

## Cron Jobs

```cron
# Denní záloha v 2:00
0 2 * * * cd /opt/infer-forge && /opt/infer-forge/scripts/backup_db.sh >> /var/log/infer-forge-backup.log 2>&1

# Týdenní záloha v neděli ve 3:00
0 3 * * 0 cd /opt/infer-forge && /opt/infer-forge/scripts/backup_db.sh --weekly >> /var/log/infer-forge-backup.log 2>&1
```

Zobrazení aktuálního crontabu:
```bash
crontab -l | grep infer-forge
```

## Skripty

### 1. `backup_db.sh`
Hlavní zálohovací skript.

**Funkce:**
- Záloha PostgreSQL přes `docker compose exec db pg_dump`
- Komprese gzip
- Záloha uploads volume (docker cp + tar.gz)
- Volá `backup-rotation.sh` pro čištění
- Logování do `/var/log/infer-forge-backup.log`
- Exit code kontrola + error reporting

**Použití:**
```bash
./scripts/backup_db.sh              # denní záloha
./scripts/backup_db.sh --weekly     # týdenní záloha
```

**Environment variables:**
```bash
BACKUP_DIR=/opt/infer-forge/backups     # kam ukládat zálohy
LOG_FILE=/var/log/infer-forge-backup.log # log soubor
RETENTION_DAYS=30                        # denní retention
WEEKLY_RETENTION_DAYS=90                 # týdenní retention
```

### 2. `backup-rotation.sh`
Správa retention policy.

**Pravidla:**
- Smaže denní zálohy starší 7 dní
- Smaže týdenní zálohy starší 28 dní (4 týdny)
- Smaže všechny zálohy starší 90 dní
- Loguje statistiky (počet záloh, celková velikost)

**Použití:**
```bash
./scripts/backup-rotation.sh false   # denní rotace
./scripts/backup-rotation.sh true    # týdenní rotace
```

### 3. `backup-cron.sh`
Instalační skript pro cron jobs.

**Co dělá:**
- Vytvoří `/opt/infer-forge/backups/` adresář
- Nastaví oprávnění (755 pro adresář, 644 pro log, +x pro skripty)
- Odstraní staré INFER FORGE cron entries
- Přidá nové cron entries (denní 2:00, týdenní neděle 3:00)
- Zobrazí souhrn

**Použití:**
```bash
sudo ./scripts/backup-cron.sh
```

### 4. `restore_db.sh`
Obnovení databáze ze zálohy.

**Funkce:**
- Safety backup před restore
- Potvrzení uživatelem (yes/no)
- Podporuje `.sql.gz` (gzip) i `.sql` (plain)
- Restore přes `docker compose exec db psql`
- Restore uploads volume (pokud zadáno)
- Spustí `alembic upgrade head` po restore
- Rollback na safety backup při chybě

**Použití:**
```bash
./scripts/restore_db.sh <backup.sql.gz> [uploads.tar.gz]
```

## Bezpečnost

### Oprávnění
```bash
# Backup adresář
/opt/infer-forge/backups/  (755, root:root)

# Zálohy
*.sql.gz                   (644, root:root)
*.tar.gz                   (644, root:root)

# Log
/var/log/infer-forge-backup.log  (644, root:root)

# Skripty
scripts/*.sh               (755, root:root)
```

### Citlivá data
- Zálohy obsahují citlivá data (zákaznická data, IČO, ceny)
- **NIKDY** nenahrávat na cloud/GitHub
- Uchovávat pouze on-premise
- Šifrování disku doporučeno (LUKS/dm-crypt)

### Off-site zálohy (doporučení)
Pro disaster recovery doporučujeme:
1. Týdenní kopie na externí disk (rsync)
2. Měsíční kopie na odděleném serveru (rsync přes SSH)
3. Šifrování AES-256 (GPG) před přenosem

```bash
# Příklad: šifrovaná off-site záloha
gpg --symmetric --cipher-algo AES256 infer-forge-weekly-*.sql.gz
rsync -avz --progress infer-forge-weekly-*.sql.gz.gpg offsite-server:/backups/
```

## Monitoring

### Kontrola poslední zálohy
```bash
# Kdy byla poslední úspěšná záloha?
grep "Backup completed successfully" /var/log/infer-forge-backup.log | tail -1

# Velikost poslední zálohy
ls -lh /opt/infer-forge/backups/*.sql.gz | tail -1
```

### Alerting (doporučení)
Nastavte monitoring pro:
- [ ] Záloha se nepodařila (exit code != 0)
- [ ] Žádná záloha za posledních 25 hodin
- [ ] Velikost zálohy < 10% obvyklé velikosti (data loss?)
- [ ] Backup adresář > 90% plný

Integrace s Prometheus/Grafana:
```bash
# Exportovat metriky (example)
echo "infer_forge_backup_success{type=\"daily\"} 1" > /var/lib/node_exporter/textfile_collector/backup.prom
echo "infer_forge_backup_size_bytes{type=\"daily\"} $(stat -c%s /opt/infer-forge/backups/latest.sql.gz)" >> /var/lib/node_exporter/textfile_collector/backup.prom
```

## Testování

### Test zálohy (dry run)
```bash
# Vytvořit testovací zálohu
BACKUP_DIR=/tmp/test-backup ./scripts/backup_db.sh

# Zkontrolovat obsah
ls -lh /tmp/test-backup/
```

### Test restore
```bash
# 1. Vytvořit zálohu
./scripts/backup_db.sh

# 2. Změnit nějaká data v DB (testovací změna)

# 3. Obnovit ze zálohy
./scripts/restore_db.sh /opt/infer-forge/backups/infer-forge-backup-*.sql.gz

# 4. Ověřit, že data jsou obnovená
```

### Disaster Recovery Test (quarterly doporučeno)
1. Zastavit INFER FORGE
2. Smazat databázi + volumes
3. Obnovit z týdenní zálohy
4. Ověřit funkčnost (přihlášení, vytvoření zakázky, export do Pohody)
5. Dokumentovat čas obnovy (RTO - Recovery Time Objective)

## Řešení Problémů

### Záloha selže: "Database container is not running"
```bash
# Zkontrolovat Docker Compose
cd /opt/infer-forge
docker compose -f docker-compose.prod.yml ps

# Nastartovat DB
docker compose -f docker-compose.prod.yml up -d db
```

### Záloha selže: "Permission denied"
```bash
# Nastavit oprávnění
sudo mkdir -p /opt/infer-forge/backups
sudo chmod 755 /opt/infer-forge/backups
sudo touch /var/log/infer-forge-backup.log
sudo chmod 644 /var/log/infer-forge-backup.log
```

### Restore selže: "relation already exists"
```bash
# Databáze má staré schéma, nejprve dropnout
docker compose -f docker-compose.prod.yml exec db dropdb -U infer infer_forge
docker compose -f docker-compose.prod.yml exec db createdb -U infer infer_forge

# Pak restore
./scripts/restore_db.sh <backup.sql.gz>
```

### Disk plný
```bash
# Zkontrolovat velikost backupů
du -sh /opt/infer-forge/backups

# Ručně smazat staré zálohy
./scripts/backup-rotation.sh

# Nebo manuálně
find /opt/infer-forge/backups -name "*.sql.gz" -mtime +30 -delete
```

### Cron job neběží
```bash
# Zkontrolovat crontab
crontab -l | grep infer-forge

# Zkontrolovat, jestli cron daemon běží
systemctl status cron     # nebo crond na CentOS/RHEL

# Zkontrolovat cron logy
grep CRON /var/log/syslog | grep infer-forge
```

## ISO 9001 Compliance

Pro splnění ISO 9001:2016 požadavků na uchovávání záznamů:

- [x] Verzování všech záloh (timestamp v názvu souboru)
- [x] Trasovatelnost (logy s časovými razítky)
- [x] Retention policy (7/4/3 denní/týdenní/měsíční)
- [x] Dokumentace postupů (tento dokument)
- [x] Testovací restore (doporučeno quarterly)
- [ ] Off-site zálohy (doporučeno pro DR)
- [ ] Šifrování (doporučeno pro citlivá data)

## Kontakt

V případě problémů s backup systémem:
- **Administrátor:** Leoš Hradek
- **Dokumentace:** `/opt/infer-forge/docs/BACKUP_SYSTEM.md`
- **Logy:** `/var/log/infer-forge-backup.log`
- **Skripty:** `/opt/infer-forge/scripts/backup*.sh`, `restore_db.sh`
