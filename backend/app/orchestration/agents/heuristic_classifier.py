"""Heuristic Classifier - Czech regex-based email classification without AI.

Fast pre-classification stage using regex patterns before falling back to Claude.
Reduces API costs by handling obvious cases (objednávka, poptávka, reklamace, etc).
"""

from __future__ import annotations

import re

import structlog

from app.agents.email_classifier import ClassificationResult

logger = structlog.get_logger(__name__)

# Compiled regex patterns for Czech email classification (case-insensitive)
_OBJEDNAVKA_PATTERNS = [
    re.compile(r"objednáváme", re.IGNORECASE),
    re.compile(r"potvrzujeme\s+objedn", re.IGNORECASE),
    re.compile(r"objednávka\s+číslo", re.IGNORECASE),
    re.compile(r"objednávka\s+č\.", re.IGNORECASE),
    re.compile(r"objednací\s+list", re.IGNORECASE),
]

_POPTAVKA_PATTERNS = [
    re.compile(r"poptáváme", re.IGNORECASE),
    re.compile(r"cenovou\s+nabídku", re.IGNORECASE),
    re.compile(r"prosím\s+o\s+nabídku", re.IGNORECASE),
    re.compile(r"žádáme\s+o\s+cenovou", re.IGNORECASE),
    re.compile(r"žádost\s+o\s+nabídku", re.IGNORECASE),
    re.compile(r"poptávka\s+(č|číslo)", re.IGNORECASE),
    re.compile(r"ocenit", re.IGNORECASE),
]

_REKLAMACE_PATTERNS = [
    re.compile(r"reklamac", re.IGNORECASE),
    re.compile(r"neshod", re.IGNORECASE),
    re.compile(r"vad[ay]", re.IGNORECASE),
    re.compile(r"stížnost", re.IGNORECASE),
    re.compile(r"vrácení\s+zboží", re.IGNORECASE),
    re.compile(r"nekvalitní", re.IGNORECASE),
]

_OBCHODNI_SDELENI_PATTERNS = [
    re.compile(r"newsletter", re.IGNORECASE),
    re.compile(r"unsubscribe", re.IGNORECASE),
    re.compile(r"odhlásit\s+se", re.IGNORECASE),
    re.compile(r"zasílání\s+novinek", re.IGNORECASE),
]

_FAKTURA_PATTERNS = [
    re.compile(r"faktura\s+(č|číslo)", re.IGNORECASE),
    re.compile(r"daňový\s+doklad", re.IGNORECASE),
    re.compile(r"splatnost.*\d+.*dn", re.IGNORECASE),
]


class HeuristicClassifier:
    """Fast regex-based classifier for Czech emails.

    Returns confident classification for obvious cases,
    or None to fall back to AI-based classification.
    """

    def classify(
        self, subject: str, body: str, has_attachments: bool, body_length: int
    ) -> ClassificationResult | None:
        """Classify email using regex patterns.

        Args:
            subject: Email subject line
            body: Email body text
            has_attachments: Whether email has attachments
            body_length: Character count of body text

        Returns:
            ClassificationResult if confident match, else None
        """
        combined_text = f"{subject} {body}"

        # Check for short email with attachments → priloha
        if body_length < 100 and has_attachments:
            logger.info(
                "heuristic_classification",
                category="priloha",
                confidence=0.85,
                reason="short_body_with_attachments",
            )
            return ClassificationResult(
                category="priloha",
                confidence=0.85,
                reasoning="Krátký email s přílohami, pravděpodobně zasílání dokumentů",
                needs_escalation=False,
            )

        # Count pattern matches per category
        match_counts = {
            "objednavka": self._count_matches(_OBJEDNAVKA_PATTERNS, combined_text),
            "poptavka": self._count_matches(_POPTAVKA_PATTERNS, combined_text),
            "reklamace": self._count_matches(_REKLAMACE_PATTERNS, combined_text),
            "obchodni_sdeleni": self._count_matches(_OBCHODNI_SDELENI_PATTERNS, combined_text),
            "faktura": self._count_matches(_FAKTURA_PATTERNS, combined_text),
        }

        # Find category with most matches
        max_category = max(match_counts, key=match_counts.get)  # type: ignore
        max_count = match_counts[max_category]

        # Require at least 1 match
        if max_count == 0:
            logger.debug("heuristic_classification_no_match", text_preview=combined_text[:100])
            return None

        # Determine confidence based on match count
        if max_count >= 2:
            confidence = 0.92
            reasoning = (
                f"Silná shoda s kategorie {max_category} ({max_count} vzorů odpovídá)"
            )
        else:
            confidence = 0.85
            reasoning = f"Shoda s kategorií {max_category} (1 vzor odpovídá)"

        logger.info(
            "heuristic_classification",
            category=max_category,
            confidence=confidence,
            match_count=max_count,
        )

        return ClassificationResult(
            category=max_category,  # type: ignore  # Already validated above
            confidence=confidence,
            reasoning=reasoning,
            needs_escalation=False,
        )

    @staticmethod
    def _count_matches(patterns: list[re.Pattern], text: str) -> int:
        """Count how many patterns match the text.

        Args:
            patterns: List of compiled regex patterns
            text: Text to search

        Returns:
            Number of patterns that found at least one match
        """
        return sum(1 for pattern in patterns if pattern.search(text))
