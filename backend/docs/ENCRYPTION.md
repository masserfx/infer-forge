# Šifrování dokumentů at rest

## Přehled

inferbox implementuje AES-256-GCM šifrování pro všechny dokumenty uložené na filesystému. Šifrování je transparentní - aplikace automaticky šifruje při ukládání a dešifruje při čtení.

## Konfigurace

### Generování šifrovacího klíče

```bash
cd backend
uv run python -c "from app.core.encryption import generate_encryption_key; print(generate_encryption_key())"
```

Výstup:
```
lawaimOUmUd/kYN4Db8CurwUD6xIIEr45SsxysBpjtA=
```

### Nastavení v .env

```env
DOCUMENT_ENCRYPTION_KEY=lawaimOUmUd/kYN4Db8CurwUD6xIIEr45SsxysBpjtA=
```

**DŮLEŽITÉ:**
- Klíč musí být base64-encoded 32-byte (256-bit) AES klíč
- Klíč uchovávejte bezpečně - pokud ho ztratíte, zašifrované dokumenty se stanou nečitelnými
- V produkci použijte silný náhodný klíč (vygenerovaný pomocí `generate_encryption_key()`)
- Nepublikujte klíč do Git repozitáře
- Pravidelně zálohujte klíč (ideálně v key vault nebo HSM)

## Chování

### Když je klíč nastaven

1. **Upload dokumentu**: Dokument se zašifruje AES-256-GCM před zápisem na disk
2. **Download dokumentu**: Dokument se dešifruje při čtení z disku
3. **Formát souboru**: `ENC1` prefix (4 bytes) + nonce (12 bytes) + ciphertext + auth tag (16 bytes)

### Když klíč není nastaven

- Dokumenty se ukládají **nešifrované** (plaintext)
- Aplikace funguje normálně, pouze bez šifrování
- Vhodné pro dev/test prostředí

### Migrace existujících dokumentů

Pokud přidáte `DOCUMENT_ENCRYPTION_KEY` do běžícího systému s existujícími dokumenty:

- **Staré dokumenty** (nešifrované): budou čteny jako plaintext (zpětná kompatibilita)
- **Nové dokumenty**: budou automaticky šifrovány
- Pro full encryption existujících dat spusťte migrační skript:

```bash
uv run python scripts/encrypt_existing_documents.py
```

## Technické detaily

### Algoritmus

- **Cipher**: AES-256-GCM (Galois/Counter Mode)
- **Key size**: 256 bits (32 bytes)
- **Nonce size**: 96 bits (12 bytes) - generován náhodně pro každý soubor
- **Tag size**: 128 bits (16 bytes) - authentication tag
- **AAD**: None (additional authenticated data není použito)

### Výhody AES-GCM

- **Confidentiality**: Šifrování dat
- **Integrity**: Detekce změn/poškození dat
- **Authenticity**: Ověření, že data nebyla podvržena
- **Performance**: Hardware akcelerace na moderních CPU (AES-NI)

### Soubory

- **Modul**: `backend/app/core/encryption.py`
- **Integrace**: `backend/app/services/document.py`
- **Testy**: `backend/tests/unit/test_encryption.py`
- **Config**: `backend/app/core/config.py`

## Bezpečnostní doporučení

1. **Key rotation**: Pravidelně rotujte šifrovací klíč (každých 12-24 měsíců)
2. **Backup**: Zálohujte klíč na oddělené bezpečné místo (offline)
3. **Access control**: Omezit přístup k .env souboru na minimální počet osob
4. **Monitoring**: Logujte selhání dešifrování (možný útok nebo poškozená data)
5. **Compliance**: Šifrování splňuje požadavky ISO 9001:2016 na ochranu citlivých dat zákazníků

## Testování

```bash
# Jednotkové testy encryption modulu
uv run pytest tests/unit/test_encryption.py -v

# Integrace s document service
uv run pytest tests/unit/test_documents.py -v

# Všechny testy
uv run pytest tests/unit/ -v
```

## Troubleshooting

### "Cannot decrypt: DOCUMENT_ENCRYPTION_KEY not configured"

Soubor je zašifrovaný, ale klíč není nastaven. Nastavte `DOCUMENT_ENCRYPTION_KEY` v .env.

### "Decryption failed"

- **Špatný klíč**: Používáte jiný klíč než při šifrování
- **Poškozená data**: Soubor byl poškozen nebo změněn
- **Útok**: Pokus o podvržení dat (GCM tag validation failed)

### "DOCUMENT_ENCRYPTION_KEY must be 32 bytes"

Klíč není správná délka. Použijte `generate_encryption_key()` pro generování validního klíče.

## Reference

- **Cryptography library**: https://cryptography.io/en/latest/hazmat/primitives/aead.html
- **AES-GCM spec**: NIST SP 800-38D
- **ISO 9001:2016**: Požadavky na bezpečnost a ochranu dat
