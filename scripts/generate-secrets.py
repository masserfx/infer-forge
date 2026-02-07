#!/usr/bin/env python3
"""Generátor bezpečných hesel a secret keys pro produkční prostředí.

Usage:
    python scripts/generate-secrets.py
    python scripts/generate-secrets.py --output .env.prod
"""

import argparse
import secrets
import sys
from pathlib import Path


def generate_secret_key(length: int = 64) -> str:
    """Vygeneruj SECRET_KEY pro JWT signing.

    Args:
        length: Délka klíče v bajtech (výsledek bude delší kvůli base64 encoding)

    Returns:
        Random URL-safe string
    """
    return secrets.token_urlsafe(length)


def generate_password(length: int = 32) -> str:
    """Vygeneruj silné heslo pro databázi/Redis.

    Args:
        length: Délka hesla v bajtech (výsledek bude delší)

    Returns:
        Random hexadecimal string
    """
    return secrets.token_hex(length)


def create_env_template(output_path: Path | None = None) -> str:
    """Vytvoř .env.prod soubor s vygenerovanými hesly.

    Args:
        output_path: Cesta k výstupnímu souboru (None = print do stdout)

    Returns:
        Vygenerovaný obsah
    """
    template = f"""# INFER FORGE - Produkční konfigurace
# Vygenerováno automaticky {secrets.token_hex(8)}
# NIKDY necommituj tento soubor do Git!

# ============================================
# Database (PostgreSQL 16 + pgvector)
# ============================================
POSTGRES_DB=infer_forge
POSTGRES_USER=infer
POSTGRES_PASSWORD={generate_password()}

# ============================================
# Redis (Celery broker & cache)
# ============================================
REDIS_PASSWORD={generate_password()}

# ============================================
# Application Security
# ============================================
SECRET_KEY={generate_secret_key()}

# ============================================
# CORS (Comma-separated allowed origins)
# ============================================
# DŮLEŽITÉ: Nastav na produkční domény!
CORS_ORIGINS=http://localhost:3000

# ============================================
# AI/ML (Anthropic Claude API)
# ============================================
# Získej z: https://console.anthropic.com/
ANTHROPIC_API_KEY=

# ============================================
# Email - IMAP (příjem pošty)
# ============================================
IMAP_HOST=
IMAP_PORT=993
IMAP_USER=
IMAP_PASSWORD=

# ============================================
# Email - SMTP (odesílání pošty)
# ============================================
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=

# ============================================
# Pohoda XML integrace (Stormware)
# ============================================
POHODA_MSERVER_URL=

# ============================================
# Monitoring (volitelné)
# ============================================
SENTRY_DSN=
"""

    if output_path:
        if output_path.exists():
            print(f"⚠️  Soubor {output_path} již existuje!", file=sys.stderr)
            response = input("Chceš ho přepsat? (ano/ne): ")
            if response.lower() not in ["ano", "yes", "y"]:
                print("Operace zrušena.", file=sys.stderr)
                sys.exit(1)

        output_path.write_text(template, encoding="utf-8")
        print(f"✅ Vygenerováno: {output_path}")
        print("⚠️  DŮLEŽITÉ: Uprav CORS_ORIGINS a doplň API klíče!")
    else:
        print(template)

    return template


def generate_individual_secrets() -> None:
    """Vygeneruj pouze jednotlivé secrets (pro rychlé použití)."""
    print("=== Vygenerované secrets ===\n")
    print(f"SECRET_KEY={generate_secret_key()}")
    print(f"POSTGRES_PASSWORD={generate_password()}")
    print(f"REDIS_PASSWORD={generate_password()}")
    print("\n⚠️  ULOŽIT DO .env.prod A NIKDY NECOMMITOVAT DO GIT!")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generátor bezpečných hesel pro INFER FORGE",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Výstupní soubor (např. .env.prod)",
    )
    parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Pouze vygeneruj secrets bez kompletního .env souboru",
    )

    args = parser.parse_args()

    if args.quick:
        generate_individual_secrets()
    else:
        create_env_template(args.output)


if __name__ == "__main__":
    main()
