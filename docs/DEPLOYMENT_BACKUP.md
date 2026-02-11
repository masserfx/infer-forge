# Nasazení Zálohovacího Systému na Produkční Server

Kroky pro instalaci automatických záloh na produkčním serveru inferbox.

## Prerekvizity

- Produkční server: `91.99.126.53`
- SSH přístup s root oprávněními
- Docker Compose běžící (inferbox deployed)
- `.env.prod` soubor nakonfigurovaný

## Instalace na Produkčním Serveru

### 1. Připojení na Server

```bash
# Z lokálního vývojového prostředí
ssh hetzner-leos   # nebo: ssh leos@91.99.126.53
```

### 2. Ověření Projektu

```bash
cd /opt/inferbox

# Zkontrolovat, že Docker Compose běží
docker compose -f docker-compose.prod.yml ps

# Měli byste vidět běžící služby: db, redis, backend, frontend, etc.
```

### 3. Ověření Zálohovacích Skriptů

```bash
cd /opt/inferbox

# Zkontrolovat, že skripty existují
ls -l scripts/backup*.sh scripts/restore_db.sh

# Zkontrolovat oprávnění (měly by být executable)
./scripts/test-backup-system.sh
```

Pokud test selže na oprávněních:

```bash
chmod +x scripts/backup_db.sh
chmod +x scripts/backup-rotation.sh
chmod +x scripts/backup-cron.sh
chmod +x scripts/restore_db.sh
chmod +x scripts/test-backup-system.sh
```

### 4. Instalace Cron Jobs

```bash
sudo ./scripts/backup-cron.sh
```

Výstup by měl být:

```
Setting up inferbox backup cron jobs...
Cron jobs installed successfully!

Backup schedule:
  - Daily backup:  Every day at 2:00 AM (retention: 7 days)
  - Weekly backup: Every Sunday at 3:00 AM (retention: 90 days)

Backup location: /opt/inferbox/backups
Log file: /var/log/inferbox-backup.log
```

### 5. Ověření Cron Jobs

```bash
# Zobrazit nainstalované cron joby
sudo crontab -l | grep inferbox
```

Měli byste vidět:

```cron
0 2 * * * cd /opt/inferbox && /opt/inferbox/scripts/backup_db.sh >> /var/log/inferbox-backup.log 2>&1
0 3 * * 0 cd /opt/inferbox && /opt/inferbox/scripts/backup_db.sh --weekly >> /var/log/inferbox-backup.log 2>&1
```

### 6. Test Manuální Zálohy

```bash
# Vytvořit první zálohu ručně (nemusíte čekat do 2:00)
cd /opt/inferbox
./scripts/backup_db.sh
```

Výstup by měl být:

```
[2026-02-08 14:30:00] =========================================
[2026-02-08 14:30:00] Starting DAILY backup
[2026-02-08 14:30:00] =========================================
[2026-02-08 14:30:02] Backing up PostgreSQL database to: /opt/inferbox/backups/inferbox-backup-2026-02-08-143000.sql.gz
[2026-02-08 14:30:05] Database backup complete: 15M
[2026-02-08 14:30:05] Backing up uploads volume to: /opt/inferbox/backups/uploads-2026-02-08
[2026-02-08 14:30:07] Uploads backup complete: 2.3M
[2026-02-08 14:30:07] Running backup rotation...
[2026-02-08 14:30:07] =========================================
[2026-02-08 14:30:07] Backup completed successfully!
[2026-02-08 14:30:07] Database: /opt/inferbox/backups/inferbox-backup-2026-02-08-143000.sql.gz
[2026-02-08 14:30:07] Uploads: /opt/inferbox/backups/uploads-2026-02-08.tar.gz
[2026-02-08 14:30:07] =========================================
```

### 7. Ověření Záloh

```bash
# Zkontrolovat vytvořené zálohy
ls -lh /opt/inferbox/backups/

# Měli byste vidět:
# -rw-r--r-- 1 root root 15M Feb  8 14:30 inferbox-backup-2026-02-08-143000.sql.gz
# -rw-r--r-- 1 root root 2.3M Feb  8 14:30 uploads-2026-02-08.tar.gz

# Zkontrolovat log
tail -50 /var/log/inferbox-backup.log
```

### 8. Test Týdenní Zálohy

```bash
# Vytvořit týdenní zálohu ručně
./scripts/backup_db.sh --weekly

# Ověřit
ls -lh /opt/inferbox/backups/inferbox-weekly-*.sql.gz
```

## Monitoring

### Sledování Logů (Live)

```bash
# Real-time sledování záloh
tail -f /var/log/inferbox-backup.log
```

### Kontrola Poslední Zálohy

```bash
# Kdy byla poslední úspěšná záloha?
grep "Backup completed successfully" /var/log/inferbox-backup.log | tail -1

# Velikost poslední zálohy
ls -lht /opt/inferbox/backups/*.sql.gz | head -1
```

### Kontrola Chyb

```bash
# Hledat chyby v logu
grep ERROR /var/log/inferbox-backup.log

# Pokud jsou chyby, zkontrolovat detaily
tail -100 /var/log/inferbox-backup.log
```

## Test Restore (Důležité!)

**VAROVÁNÍ:** Toto provedete na testovacím prostředí, NE na produkci!

```bash
# 1. Vytvořit zálohu
./scripts/backup_db.sh

# 2. Najít nejnovější zálohu
LATEST_BACKUP=$(ls -t /opt/inferbox/backups/inferbox-backup-*.sql.gz | head -1)
echo "Latest backup: $LATEST_BACKUP"

# 3. Restore (vytvoří safety backup před restore)
./scripts/restore_db.sh "$LATEST_BACKUP"

# Budete dotázáni na potvrzení:
# Type 'yes' to continue: yes

# Výstup:
# [2026-02-08 14:35:00] RESTORE: Creating safety backup: /opt/inferbox/backups/safety-backup-2026-02-08-143500.sql.gz
# [2026-02-08 14:35:02] RESTORE: Safety backup complete: 15M
# [2026-02-08 14:35:02] RESTORE: Dropping database 'infer_forge'...
# [2026-02-08 14:35:03] RESTORE: Creating database 'infer_forge'...
# [2026-02-08 14:35:04] RESTORE: Restoring from backup...
# [2026-02-08 14:35:10] RESTORE: Database restore complete
# [2026-02-08 14:35:10] RESTORE: Running Alembic migrations...
# [2026-02-08 14:35:12] RESTORE: Migrations complete
# [2026-02-08 14:35:12] RESTORE: Restore completed successfully!
```

## Troubleshooting

### Problém: "Database container is not running"

```bash
# Zkontrolovat Docker Compose
docker compose -f docker-compose.prod.yml ps

# Nastartovat služby
docker compose -f docker-compose.prod.yml up -d
```

### Problém: "Permission denied" při vytváření zálohy

```bash
# Vytvořit backup adresář s správnými oprávněními
sudo mkdir -p /opt/inferbox/backups
sudo chmod 755 /opt/inferbox/backups

# Vytvořit log soubor
sudo touch /var/log/inferbox-backup.log
sudo chmod 644 /var/log/inferbox-backup.log
```

### Problém: Cron job neběží

```bash
# Zkontrolovat cron daemon
systemctl status cron    # nebo: systemctl status crond

# Pokud není zapnutý
sudo systemctl start cron
sudo systemctl enable cron

# Zkontrolovat cron logy
sudo grep CRON /var/log/syslog | grep inferbox
```

### Problém: Zálohy zabírají moc místa

```bash
# Zkontrolovat velikost backupů
du -sh /opt/inferbox/backups

# Ručně spustit rotaci
./scripts/backup-rotation.sh

# Případně snížit retention (ve skriptu backup_db.sh)
# RETENTION_DAYS=30 → změnit na nižší číslo
```

## Bezpečnostní Doporučení

### 1. Nastavit Off-site Zálohy (Disaster Recovery)

```bash
# Příklad: týdenní rsync na vzdálený server
# Přidat do crontabu:
0 4 * * 0 rsync -avz --progress /opt/inferbox/backups/inferbox-weekly-*.sql.gz.gpg offsite-server:/backups/
```

### 2. Šifrování Záloh (Pro Off-site)

```bash
# Instalovat GPG
sudo apt-get install gnupg

# Šifrovat zálohu před přenosem
gpg --symmetric --cipher-algo AES256 /opt/inferbox/backups/inferbox-weekly-*.sql.gz

# Výsledek: inferbox-weekly-*.sql.gz.gpg (šifrovaný)
```

### 3. Nastavit Email Alerting

Pro produkční monitoring je doporučeno:

```bash
# Instalovat mailutils
sudo apt-get install mailutils

# Upravit backup_db.sh - přidat na konec:
if [ $? -eq 0 ]; then
    echo "Backup completed successfully" | mail -s "inferbox Backup OK" admin@infer.cz
else
    echo "Backup FAILED! Check logs at /var/log/inferbox-backup.log" | mail -s "inferbox Backup FAILED" admin@infer.cz
fi
```

### 4. Monitoring s Prometheus/Grafana

inferbox už má Prometheus + Grafana. Můžete přidat metriky pro backup monitoring:

```bash
# Vytvořit node_exporter textfile collector
sudo mkdir -p /var/lib/node_exporter/textfile_collector

# V backup_db.sh přidat export metrik (na konec):
cat > /var/lib/node_exporter/textfile_collector/infer_forge_backup.prom <<EOF
# HELP infer_forge_backup_success Last backup success (1=success, 0=failed)
# TYPE infer_forge_backup_success gauge
infer_forge_backup_success{type="daily"} 1

# HELP infer_forge_backup_timestamp_seconds Last backup timestamp
# TYPE infer_forge_backup_timestamp_seconds gauge
infer_forge_backup_timestamp_seconds{type="daily"} $(date +%s)

# HELP infer_forge_backup_size_bytes Last backup size in bytes
# TYPE infer_forge_backup_size_bytes gauge
infer_forge_backup_size_bytes{type="daily"} $(stat -c%s "$DB_BACKUP_FILE")
EOF
```

## Quarterly Disaster Recovery Test

**Každé 3 měsíce doporučujeme otestovat úplné obnovení:**

1. Na testovacím serveru (NE produkce!):

```bash
# Zastavit všechny služby
docker compose -f docker-compose.prod.yml down -v

# Smazat volumes
docker volume rm infer-forge_pgdata infer-forge_uploads

# Nastartovat DB
docker compose -f docker-compose.prod.yml up -d db

# Obnovit z týdenní zálohy
./scripts/restore_db.sh /opt/inferbox/backups/inferbox-weekly-LATEST.sql.gz

# Nastartovat všechny služby
docker compose -f docker-compose.prod.yml up -d

# Ověřit funkčnost
# - Přihlásit se do frontendu
# - Vytvořit testovací zakázku
# - Export do Pohody
# - Zkontrolovat logy
```

2. Dokumentovat výsledky:
   - ✅ RTO (Recovery Time Objective): Jak dlouho trvalo obnovení?
   - ✅ RPO (Recovery Point Objective): Kolik dat jsme ztratili?
   - ✅ Funkčnost: Vše funguje správně?

3. Uložit test report do `/opt/inferbox/docs/dr_test_YYYY-MM-DD.md`

## Checklist po Instalaci

- [ ] Cron jobs nainstalované (`crontab -l | grep inferbox`)
- [ ] První denní záloha vytvořená (`ls /opt/inferbox/backups/`)
- [ ] První týdenní záloha vytvořená
- [ ] Test restore úspěšný
- [ ] Log monitoring nastaven (`tail -f /var/log/inferbox-backup.log`)
- [ ] Email alerting nakonfigurován (optional)
- [ ] Off-site backup nastaven (recommended)
- [ ] Disaster Recovery test naplánován (quarterly)
- [ ] Dokumentace předána týmu

## Kontakt

V případě problémů:
- **Dokumentace:** `/opt/inferbox/docs/BACKUP_SYSTEM.md`
- **Logy:** `/var/log/inferbox-backup.log`
- **Support:** Leoš Hradek
