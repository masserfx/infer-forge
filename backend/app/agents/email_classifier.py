"""Email classification agent for incoming emails.

Uses Anthropic Claude API with structured tool_use output to classify
incoming emails into categories relevant for a steel fabrication company.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import structlog
from anthropic import AsyncAnthropic

logger = structlog.get_logger(__name__)

# Valid email categories for the steel fabrication domain
EmailCategory = Literal[
    "poptavka",
    "objednavka",
    "reklamace",
    "dotaz",
    "priloha",
    "informace_zakazka",
    "faktura",
    "obchodni_sdeleni",
]

_VALID_CATEGORIES: set[str] = {
    "poptavka",
    "objednavka",
    "reklamace",
    "dotaz",
    "priloha",
    "informace_zakazka",
    "faktura",
    "obchodni_sdeleni",
}

# Confidence threshold below which the result is flagged for human review
_ESCALATION_THRESHOLD: float = 0.8

# Anthropic model — centralized in Settings
from app.core.config import get_settings as _get_settings
_MODEL: str = _get_settings().ANTHROPIC_MODEL

# Maximum tokens for the classification response
_MAX_TOKENS: int = 1024

# Timeout in seconds for the API call
_TIMEOUT_SECONDS: float = 30.0

# Tool definition for structured classification output
_CLASSIFY_TOOL: dict[str, object] = {
    "name": "classify_email",
    "description": (
        "Klasifikuj email do jedne z kategorii: poptavka, objednavka, "
        "reklamace, dotaz, priloha. Vrat kategorii, miru jistoty (confidence) "
        "a zduvodneni v cestine."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": [
                    "poptavka",
                    "objednavka",
                    "reklamace",
                    "dotaz",
                    "priloha",
                    "informace_zakazka",
                    "faktura",
                    "obchodni_sdeleni",
                ],
                "description": (
                    "Kategorie emailu: poptavka (request for quote / novy projekt), "
                    "objednavka (potvrzeni objednavky / objednani materialu), "
                    "reklamace (stiznost / vada / neshoda), "
                    "dotaz (obecny dotaz / informace), "
                    "priloha (email obsahujici hlavne prilohy - vykresy, specifikace), "
                    "informace_zakazka (informace o stavu existujici zakazky), "
                    "faktura (danovy doklad / faktura / proforma), "
                    "obchodni_sdeleni (newsletter / marketing / unsubscribe)."
                ),
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": (
                    "Mira jistoty klasifikace od 0.0 (zadna jistota) " "do 1.0 (absolutni jistota)."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "Kratke zduvodneni klasifikace v cestine. "
                    "Vysvetli, proc byl email zarazen do dane kategorie."
                ),
            },
        },
        "required": ["category", "confidence", "reasoning"],
    },
}

# System prompt describing the classification task and company context
_SYSTEM_PROMPT: str = """Jsi AI asistent strojirenske firmy Infer s.r.o. Firma vyrabi:
- Potrubni dily (kolena, T-kusy, redukce, priruby) z uhlove a nerezove oceli
- Svarove konstrukce a svarence dle vykresove dokumentace
- Ocelove konstrukce (nosne, podperne, technologicke)
- Provadi montaze prumyslovych zarizeni a potrubi

Tvym ukolem je klasifikovat prichozi emaily do jedne z kategorii:

1. **poptavka** - Zakaznik se pta na cenu, termin, moznost vyroby. Obsahuje specifikace,
   mnozstvi, materialy, rozmery (DN, PN), odkaz na normy. Muze jit o novou zakazku.
2. **objednavka** - Zakaznik potvrzuje objednavku, odkazuje na nabidku ci predchozi
   komunikaci. Obsahuje objednavkove cislo, potvrzeni ceny/terminu.
3. **reklamace** - Stiznost na kvalitu, vadu, nesplneni terminu, neshodny material.
   Zminka o neshode, protokolu, vraceni zbozi.
4. **dotaz** - Obecny dotaz na stav zakazky, dodaci podminky, certifikaty, kapacity.
   Neni to poptavka ani objednavka.
5. **priloha** - Email slouzici predevsim k predani priloh (vykresy DWG/PDF, specifikace,
   atesni listy, fotografie). Telo emailu je kratke, odkazuje na prilohy.
6. **informace_zakazka** - Informace tykajici se existujici zakazky - stav vyroby,
   dodaci podminky, zmeny v objednavce, doplnujici specifikace.
7. **faktura** - Danovy doklad, faktura, proforma faktura, dobropis. Obsahuje castku,
   datum splatnosti, cislo faktury, ICO/DIC.
8. **obchodni_sdeleni** - Newsletter, marketingovy email, automaticke notifikace,
   emaily s moznosti odhlaseni (unsubscribe). Neni to objednavka ani poptavka.

Pouzij nastroj classify_email pro vraceni strukturovaneho vysledku. Bud precizni
v confidence - pokud si nejsi jisty, nastav nizsi hodnotu."""


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Result of email classification.

    Attributes:
        category: The classified category, or None if classification failed.
        confidence: Confidence score between 0.0 and 1.0.
        reasoning: Human-readable reasoning for the classification.
        needs_escalation: True if confidence is below the escalation threshold
            or if classification failed.
    """

    category: EmailCategory | None
    confidence: float
    reasoning: str
    needs_escalation: bool = field(default=False)
    tokens_used: int = field(default=0)

    def __post_init__(self) -> None:
        """Validate invariants after initialization."""
        if self.confidence < 0.0 or self.confidence > 1.0:
            object.__setattr__(
                self,
                "confidence",
                max(0.0, min(1.0, self.confidence)),
            )


class EmailClassifier:
    """Classifies incoming emails using Anthropic Claude API.

    Uses structured tool_use output to produce reliable, typed classification
    results for emails received by the steel fabrication company Infer s.r.o.

    Args:
        api_key: Anthropic API key for authentication.

    Example:
        >>> classifier = EmailClassifier(api_key="sk-ant-...")
        >>> result = await classifier.classify(
        ...     subject="Poptavka - kolena DN200 PN16",
        ...     body="Dobry den, prosim o cenovou nabidku na 50ks kolen...",
        ... )
        >>> result.category
        'poptavka'
    """

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def classify(
        self,
        subject: str,
        body: str,
    ) -> ClassificationResult:
        """Classify an incoming email into a predefined category.

        Args:
            subject: The email subject line.
            body: The plain-text email body.

        Returns:
            ClassificationResult with category, confidence, reasoning,
            and escalation flag.
        """
        log = logger.bind(subject=subject[:100])
        log.info("email_classification.started")

        # Circuit breaker check
        from app.core.circuit_breaker import anthropic_breaker

        if not anthropic_breaker.can_execute():
            log.warning("email_classification.circuit_open")
            fallback = self._keyword_fallback(subject, body)
            if fallback is not None:
                log.info("email_classification.keyword_fallback", category=fallback)
                return ClassificationResult(
                    category=fallback,
                    confidence=0.3,
                    reasoning="Klasifikace pomoci klicovych slov (API nedostupne).",
                    needs_escalation=True,
                )
            return ClassificationResult(
                category=None,
                confidence=0.0,
                reasoning="Klasifikace odlozena: Anthropic API je docasne nedostupne.",
                needs_escalation=True,
            )

        # Rate limiter check
        from app.core.rate_limiter import RateLimitExceeded, get_rate_limiter

        try:
            get_rate_limiter().acquire(estimated_tokens=_MAX_TOKENS)
        except RateLimitExceeded as exc:
            log.warning("email_classification.rate_limited", reason=str(exc))
            return ClassificationResult(
                category=None,
                confidence=0.0,
                reasoning="Klasifikace odlozena: dosazeny limit API volani.",
                needs_escalation=True,
            )

        user_message = self._build_user_message(subject, body)

        tokens_used = 0
        try:
            response = await self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                tools=[_CLASSIFY_TOOL],  # type: ignore[list-item]
                tool_choice={"type": "tool", "name": "classify_email"},
                messages=[{"role": "user", "content": user_message}],
                timeout=_TIMEOUT_SECONDS,
            )
            anthropic_breaker.record_success()
            # Record actual token usage
            usage = getattr(response, "usage", None)
            if usage:
                tokens_used = (getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0))
                get_rate_limiter().record_usage(tokens_used)
                log.info("email_classification.token_usage", input=getattr(usage, "input_tokens", 0), output=getattr(usage, "output_tokens", 0))
        except TimeoutError:
            anthropic_breaker.record_failure()
            log.warning("email_classification.timeout")
            return ClassificationResult(
                category=None,
                confidence=0.0,
                reasoning="Klasifikace selhala: vyprseni casoveho limitu API volani.",
                needs_escalation=True,
            )
        except Exception:
            anthropic_breaker.record_failure()
            log.exception("email_classification.api_error")
            return ClassificationResult(
                category=None,
                confidence=0.0,
                reasoning="Klasifikace selhala: neocekavana chyba pri volani API.",
                needs_escalation=True,
            )
        finally:
            get_rate_limiter().release()

        result = self._parse_response(response, log)
        return ClassificationResult(
            category=result.category,
            confidence=result.confidence,
            reasoning=result.reasoning,
            needs_escalation=result.needs_escalation,
            tokens_used=tokens_used,
        )

    @staticmethod
    def _keyword_fallback(subject: str, body: str) -> EmailCategory | None:
        """Simple keyword-based fallback classification when API is unavailable."""
        text = (subject + " " + body).lower()
        keywords: list[tuple[EmailCategory, list[str]]] = [
            ("reklamace", ["reklamace", "reklamaci", "vada", "neshoda", "stiznost"]),
            ("objednavka", ["objednavka", "objednavame", "objednavku", "potvrzujeme objednavku"]),
            ("poptavka", ["poptavka", "poptavame", "cenova nabidka", "cenovou nabidku", "prosim o nabidku"]),
            ("faktura", ["faktura", "proforma", "dobropis", "danovy doklad"]),
            ("priloha", ["v priloze", "priloha", "prilohy", "vykres"]),
            ("obchodni_sdeleni", ["newsletter", "unsubscribe", "odhlasit"]),
        ]
        for category, kws in keywords:
            for kw in kws:
                if kw in text:
                    return category
        return None

    @staticmethod
    def _build_user_message(subject: str, body: str) -> str:
        """Build the user message from email subject and body.

        Args:
            subject: The email subject line.
            body: The plain-text email body (truncated to 4000 chars).

        Returns:
            Formatted user message string.
        """
        # Truncate very long bodies to stay within token limits
        truncated_body = body[:4000]
        if len(body) > 4000:
            truncated_body += "\n\n[... text zkracen ...]"

        # XML tags delimit user content to prevent prompt injection
        return (
            "Klasifikuj nasledujici email:\n\n"
            f"<email_subject>{subject}</email_subject>\n\n"
            f"<email_body>\n{truncated_body}\n</email_body>"
        )

    @staticmethod
    def _parse_response(
        response: object,
        log: structlog.stdlib.BoundLogger,
    ) -> ClassificationResult:
        """Parse the Anthropic API response into a ClassificationResult.

        Args:
            response: The raw API response from Anthropic.
            log: Bound structlog logger for contextual logging.

        Returns:
            Parsed ClassificationResult.
        """
        # Extract tool_use block from response content
        tool_input: dict[str, object] | None = None
        for block in response.content:  # type: ignore[attr-defined]
            if block.type == "tool_use" and block.name == "classify_email":
                tool_input = block.input  # type: ignore[assignment]
                break

        if tool_input is None:
            log.error(
                "email_classification.no_tool_use_block",
                response_content=str(response.content),  # type: ignore[attr-defined]
            )
            return ClassificationResult(
                category=None,
                confidence=0.0,
                reasoning="Klasifikace selhala: API nevratilo ocekavany tool_use blok.",
                needs_escalation=True,
            )

        category_raw = str(tool_input.get("category", ""))
        confidence_raw = tool_input.get("confidence", 0.0)
        reasoning_raw = str(tool_input.get("reasoning", ""))

        # Validate category
        category: EmailCategory | None = None
        if category_raw in _VALID_CATEGORIES:
            category = category_raw  # type: ignore[assignment]
        else:
            log.warning(
                "email_classification.invalid_category",
                category=category_raw,
            )

        # Validate confidence
        try:
            confidence = float(confidence_raw)  # type: ignore[arg-type]
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.0

        # Determine escalation need
        needs_escalation = confidence < _ESCALATION_THRESHOLD or category is None
        if needs_escalation:
            log.info(
                "email_classification.needs_escalation",
                category=category,
                confidence=confidence,
            )

        result = ClassificationResult(
            category=category,
            confidence=confidence,
            reasoning=reasoning_raw,
            needs_escalation=needs_escalation,
        )

        log.info(
            "email_classification.completed",
            category=result.category,
            confidence=result.confidence,
            needs_escalation=result.needs_escalation,
        )

        return result
