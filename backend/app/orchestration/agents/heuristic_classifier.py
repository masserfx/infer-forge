"""Heuristic Classifier - Czech regex-based email classification without AI.

Fast pre-classification stage using regex patterns before falling back to Claude.
Reduces API costs by handling obvious cases (objednávka, poptávka, reklamace, etc).
"""

from __future__ import annotations

import re

import structlog

from app.agents.email_classifier import ClassificationResult

logger = structlog.get_logger(__name__)

# Compiled regex patterns for Czech email classification (case-insensitive).
# Each pattern includes both diacritics and ASCII variants so that emails
# written without háčky/čárky are also matched correctly.
_OBJEDNAVKA_PATTERNS = [
    re.compile(r"objedn[aá]v[aá]me", re.IGNORECASE),
    re.compile(r"potvrzujeme\s+objedn", re.IGNORECASE),
    re.compile(r"objedn[aá]vka\s+[cč][ií]slo", re.IGNORECASE),
    re.compile(r"objedn[aá]vka\s+[cč]\.", re.IGNORECASE),
    re.compile(r"objedn[aá]c[ií]\s+list", re.IGNORECASE),
]

_POPTAVKA_PATTERNS = [
    re.compile(r"popt[aá]v[aá]me", re.IGNORECASE),
    re.compile(r"popt[aá]l[ia]", re.IGNORECASE),
    re.compile(r"popt[aá]vka\b", re.IGNORECASE),
    re.compile(r"cenov[ouéý]\w*\s+nab[ií]dk", re.IGNORECASE),
    re.compile(r"pros[ií]m\s+o\s+.*nab[ií]dk", re.IGNORECASE),
    re.compile(r"zasl[aá]n[ií]\s+.*nab[ií]dk", re.IGNORECASE),
    re.compile(r"[zž][aá]d[aá]me\s+o\s+cenov", re.IGNORECASE),
    re.compile(r"[zž][aá]dost\s+o\s+nab[ií]dku", re.IGNORECASE),
    re.compile(r"ocenit", re.IGNORECASE),
    re.compile(r"nab[ií]dkov[éý]\s+[rř][ií]zen[ií]", re.IGNORECASE),
]

_REKLAMACE_PATTERNS = [
    re.compile(r"reklamac", re.IGNORECASE),
    re.compile(r"neshod", re.IGNORECASE),
    re.compile(r"vad[ay]", re.IGNORECASE),
    re.compile(r"st[ií][zž]nost", re.IGNORECASE),
    re.compile(r"vr[aá]cen[ií]\s+zbo[zž][ií]", re.IGNORECASE),
    re.compile(r"nekvalitni", re.IGNORECASE),
    re.compile(r"nekvalitní", re.IGNORECASE),
]

_OBCHODNI_SDELENI_PATTERNS = [
    re.compile(r"newsletter", re.IGNORECASE),
    re.compile(r"unsubscribe", re.IGNORECASE),
    re.compile(r"odhl[aá]sit\s+se", re.IGNORECASE),
    re.compile(r"zas[ií]l[aá]n[ií]\s+novinek", re.IGNORECASE),
]

_FAKTURA_PATTERNS = [
    re.compile(r"faktura\s+([cč]|[cč][ií]slo)", re.IGNORECASE),
    re.compile(r"da[nň]ov[yý]\s+doklad", re.IGNORECASE),
    re.compile(r"splatnost.*\d+.*dn", re.IGNORECASE),
]

_DOTAZ_PATTERNS = [
    re.compile(r"dotaz\s+(na|ohled)", re.IGNORECASE),
    re.compile(r"informac[ie]?\s+o", re.IGNORECASE),
    re.compile(r"pros[ií]m\s+o\s+informac", re.IGNORECASE),
    re.compile(r"m[uů][zž]ete\s+sd[eě]lit", re.IGNORECASE),
    re.compile(r"jak[yý]\s+je\s+stav", re.IGNORECASE),
    re.compile(r"r[aá]d[ai]?\s+bych\s+(se\s+)?zeptal", re.IGNORECASE),
    re.compile(r"pot[rř]eboval[ai]?\s+bych\s+v[eě]d[eě]t", re.IGNORECASE),
]

_INFORMACE_ZAKAZKA_PATTERNS = [
    re.compile(r"stav\s+(zak[aá]zky|objedn[aá]vky)", re.IGNORECASE),
    re.compile(r"kde\s+je\s+(zak[aá]zka|objedn[aá]vka)", re.IGNORECASE),
    re.compile(r"(jak[yý]|kdy|sd[eě]l\w*|informov\w*)\s+.*term[ií]n", re.IGNORECASE),
    re.compile(r"p[rř]edpokl[aá]dan[yý]\s+term[ií]n", re.IGNORECASE),
    re.compile(r"zak[aá]zka\s+[cč](\.|[ií]slo)", re.IGNORECASE),
    re.compile(r"jak\s+to\s+vypad[aá]\s+s", re.IGNORECASE),
    re.compile(r"postup\w*\s+(prac[ií]|v[yý]roby)", re.IGNORECASE),
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
            "dotaz": self._count_matches(_DOTAZ_PATTERNS, combined_text),
            "informace_zakazka": self._count_matches(_INFORMACE_ZAKAZKA_PATTERNS, combined_text),
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
