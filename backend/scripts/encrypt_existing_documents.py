#!/usr/bin/env python
"""Migrate existing unencrypted documents to encrypted format.

This script scans all documents in the database and encrypts any that are
currently stored as plaintext. Documents already encrypted are skipped.

Usage:
    uv run python scripts/encrypt_existing_documents.py [--dry-run]

Options:
    --dry-run    Show what would be encrypted without making changes
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.encryption import encrypt_data, get_encryption_key, is_encrypted
from app.models import Document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def migrate_documents(dry_run: bool = False) -> None:
    """Encrypt all unencrypted documents.

    Args:
        dry_run: If True, only report what would be encrypted without making changes
    """
    # Check if encryption key is configured
    key = get_encryption_key()
    if key is None:
        logger.error("DOCUMENT_ENCRYPTION_KEY not configured. Set it in .env file.")
        sys.exit(1)

    logger.info("Encryption key loaded successfully")

    # Get all documents from database
    async for session in get_async_session():
        session: AsyncSession
        result = await session.execute(select(Document))
        documents = result.scalars().all()

        total = len(documents)
        encrypted = 0
        already_encrypted = 0
        missing_files = 0
        errors = 0

        logger.info("Found %d documents in database", total)

        for doc in documents:
            file_path = Path(doc.file_path)

            # Check if file exists
            if not file_path.exists():
                logger.warning("File missing: %s (document_id=%s)", doc.file_path, doc.id)
                missing_files += 1
                continue

            # Read file
            try:
                file_content = file_path.read_bytes()
            except Exception as e:
                logger.error("Failed to read %s: %s", doc.file_path, e)
                errors += 1
                continue

            # Check if already encrypted
            if is_encrypted(file_content):
                logger.debug("Already encrypted: %s", doc.file_name)
                already_encrypted += 1
                continue

            # Encrypt
            logger.info("Encrypting: %s (document_id=%s, size=%d bytes)",
                       doc.file_name, doc.id, len(file_content))

            if not dry_run:
                try:
                    encrypted_content = encrypt_data(file_content)
                    file_path.write_bytes(encrypted_content)
                    logger.info("✓ Encrypted: %s", doc.file_name)
                    encrypted += 1
                except Exception as e:
                    logger.error("Failed to encrypt %s: %s", doc.file_path, e)
                    errors += 1
            else:
                logger.info("[DRY RUN] Would encrypt: %s", doc.file_name)
                encrypted += 1

        # Summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        logger.info("Total documents:      %d", total)
        logger.info("Already encrypted:    %d", already_encrypted)
        logger.info("Newly encrypted:      %d", encrypted)
        logger.info("Missing files:        %d", missing_files)
        logger.info("Errors:               %d", errors)
        logger.info("=" * 60)

        if dry_run:
            logger.info("")
            logger.info("DRY RUN MODE - No files were modified")
            logger.info("Run without --dry-run to apply changes")
        elif encrypted > 0:
            logger.info("")
            logger.info("✓ Migration completed successfully")
        elif already_encrypted == total:
            logger.info("")
            logger.info("✓ All documents already encrypted")

        if errors > 0:
            logger.warning("")
            logger.warning("⚠ %d errors occurred during migration", errors)
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Encrypt existing unencrypted documents"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be encrypted without making changes",
    )
    args = parser.parse_args()

    logger.info("Starting document encryption migration")
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be modified")
    logger.info("")

    asyncio.run(migrate_documents(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
