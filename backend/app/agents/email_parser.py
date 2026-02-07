"""Email parsing agent for extracting structured inquiry data.

Uses Anthropic Claude API with structured tool_use output to extract
company info, contact details, and item specifications from incoming
emails in the steel fabrication domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog
from anthropic import AsyncAnthropic

logger = structlog.get_logger(__name__)

# Anthropic model used for parsing
_MODEL: str = "claude-sonnet-4-20250514"

# Maximum tokens for the parsing response
_MAX_TOKENS: int = 2048

# Timeout in seconds for the API call
_TIMEOUT_SECONDS: float = 60.0

# Tool definition for structured parsed inquiry output
_PARSE_TOOL: dict[str, object] = {
    "name": "parse_inquiry",
    "description": (
        "Extrahuj strukturovana data z emailu - informace o firme, kontaktni osobe "
        "a pozadovanych polozkach (material, rozmery, mnozstvi). "
        "Pokud nektera informace neni v emailu uvedena, vrat null."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_name": {
                "type": ["string", "null"],
                "description": "Nazev firmy zakaznika (pokud je uveden v emailu nebo podpisu).",
            },
            "contact_name": {
                "type": ["string", "null"],
                "description": ("Jmeno kontaktni osoby (odesilatel, osoba uvedena v podpisu)."),
            },
            "email": {
                "type": ["string", "null"],
                "description": "Emailova adresa kontaktni osoby (pokud je uvedena v tele).",
            },
            "phone": {
                "type": ["string", "null"],
                "description": (
                    "Telefonni cislo kontaktni osoby. Zachovej format vcetne predvolby."
                ),
            },
            "items": {
                "type": "array",
                "description": "Seznam pozadovanych polozek / vyrobku.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": (
                                "Nazev polozky (napr. koleno 90, T-kus, priruba, svarenec, "
                                "ocelova konstrukce). Pouzij cesky nazev."
                            ),
                        },
                        "material": {
                            "type": ["string", "null"],
                            "description": (
                                "Material polozky - oznaceni oceli (napr. 11 353, P235GH, "
                                "1.4301, AISI 304), norma materialu, nebo slovni popis "
                                "(nerezova ocel, uhlikova ocel)."
                            ),
                        },
                        "quantity": {
                            "type": ["number", "null"],
                            "description": "Pozadovane mnozstvi (ciselna hodnota).",
                        },
                        "unit": {
                            "type": ["string", "null"],
                            "description": (
                                "Jednotka mnozstvi (ks, m, bm, kg, t, sada, komplet). "
                                "Vychozi je 'ks'."
                            ),
                        },
                        "dimensions": {
                            "type": ["string", "null"],
                            "description": (
                                "Rozmery polozky - DN (jmenovity prumer), PN (jmenovity tlak), "
                                "prumer x tloustka stenky (napr. 219.1x6.3), delka, "
                                "rozmery profilu (napr. HEB 200), nebo odkaz na vykres. "
                                "Zachovej puvodni format vcetne jednotek."
                            ),
                        },
                    },
                    "required": ["name"],
                },
            },
            "deadline": {
                "type": ["string", "null"],
                "description": (
                    "Pozadovany termin dodani / realizace. "
                    "Zachovej puvodni formulaci (napr. 'do konce brezna', '15.4.2025', "
                    "'6-8 tydnu', 'co nejdrive')."
                ),
            },
            "note": {
                "type": ["string", "null"],
                "description": (
                    "Dalsi dulezite poznamky - pozadavky na certifikaty (EN 10204 3.1), "
                    "NDT zkousky, povrchovou upravu, baleni, dopravu, montaz, "
                    "nebo jakekoli dalsi specificke pozadavky."
                ),
            },
        },
        "required": ["company_name", "contact_name", "email", "phone", "items", "deadline", "note"],
    },
}

# System prompt for the email parsing task
_SYSTEM_PROMPT: str = """Jsi AI asistent strojirenske firmy Infer s.r.o., ktera vyrabi potrubni dily,
svarence, ocelove konstrukce a provadi prumyslove montaze.

Tvym ukolem je extrahovat strukturovana data z prichoziho emailu. Zamerujes se na:

**Kontaktni udaje:**
- Nazev firmy (hledej v podpisu, hlavicce, nebo tele emailu)
- Jmeno kontaktni osoby
- Email a telefon (z podpisu nebo tela)

**Polozky / vyrobky:**
Pro kazdou pozadovanou polozku extrahuj:
- Nazev vyrobku v cestine (koleno, T-kus, redukce, priruba, svarenec, konstrukce, potrubi...)
- Material - oznaceni oceli dle CSN (11 353, 12 022), EN (P235GH, S235JR, S355J2),
  nebo DIN/AISI (1.4301, AISI 304, AISI 316L). Rozlisuj uhlikovou a nerezovou ocel.
- Mnozstvi a jednotky
- Rozmery - DN (jmenovity prumer, napr. DN200), PN (jmenovity tlak, napr. PN16),
  prumer x tloustka (napr. 219.1x6.3 mm), delky, rozmery profilu. Zachovej puvodni zapis.

**Dalsi informace:**
- Termin dodani (zachovej puvodni formulaci)
- Poznamky: certifikaty (atesty dle EN 10204), NDT (RT, UT, MT, PT), povrchova uprava
  (zinkovani, natery, tryskani), baleni, doprava, montaz, WPS, WPQR.

DULEZITE: Pokud informace v emailu neni, vrat null. Nevymyslej si data.
Pouzij nastroj parse_inquiry pro vraceni strukturovaneho vysledku."""


@dataclass(frozen=True, slots=True)
class ParsedItem:
    """A single item extracted from an email inquiry.

    Attributes:
        name: Item name in Czech (e.g., 'koleno 90', 'T-kus', 'priruba').
        material: Material designation (e.g., 'P235GH', '1.4301', 'S355J2').
        quantity: Requested quantity as a number.
        unit: Unit of measurement (ks, m, kg, etc.).
        dimensions: Dimensions string (DN, PN, diameter x wall thickness, etc.).
    """

    name: str
    material: str | None = None
    quantity: float | None = None
    unit: str | None = None
    dimensions: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedInquiry:
    """Structured data extracted from an email inquiry.

    Attributes:
        company_name: Customer company name.
        contact_name: Contact person name.
        email: Contact email address (extracted from body/signature).
        phone: Contact phone number.
        items: List of requested items with specifications.
        deadline: Requested delivery deadline (original wording).
        note: Additional notes (certificates, NDT, surface treatment, etc.).
    """

    company_name: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    items: list[ParsedItem] = field(default_factory=list)
    deadline: str | None = None
    note: str | None = None


class EmailParser:
    """Extracts structured inquiry data from incoming emails.

    Uses Anthropic Claude API with tool_use to reliably extract company info,
    contact details, and item specifications from emails received by the
    steel fabrication company Infer s.r.o.

    Args:
        api_key: Anthropic API key for authentication.

    Example:
        >>> parser = EmailParser(api_key="sk-ant-...")
        >>> result = await parser.parse(
        ...     subject="Poptavka - kolena DN200",
        ...     body="Dobry den, firma XYZ s.r.o. poptava 50ks kolen 90 DN200 PN16...",
        ... )
        >>> result.company_name
        'XYZ s.r.o.'
        >>> result.items[0].name
        'koleno 90'
    """

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def parse(
        self,
        subject: str,
        body: str,
    ) -> ParsedInquiry:
        """Parse an incoming email and extract structured inquiry data.

        Args:
            subject: The email subject line.
            body: The plain-text email body.

        Returns:
            ParsedInquiry with extracted company, contact, and item data.
            Returns an empty ParsedInquiry on failure.
        """
        log = logger.bind(subject=subject[:100])
        log.info("email_parsing.started")

        user_message = self._build_user_message(subject, body)

        try:
            response = await self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                tools=[_PARSE_TOOL],  # type: ignore[list-item]
                tool_choice={"type": "tool", "name": "parse_inquiry"},
                messages=[{"role": "user", "content": user_message}],
                timeout=_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            log.warning("email_parsing.timeout")
            return ParsedInquiry()
        except Exception:
            log.exception("email_parsing.api_error")
            return ParsedInquiry()

        return self._parse_response(response, log)

    @staticmethod
    def _build_user_message(subject: str, body: str) -> str:
        """Build the user message from email subject and body.

        Args:
            subject: The email subject line.
            body: The plain-text email body (truncated to 6000 chars).

        Returns:
            Formatted user message string.
        """
        # Allow longer body for parsing since we need more detail than classification
        truncated_body = body[:6000]
        if len(body) > 6000:
            truncated_body += "\n\n[... text zkracen ...]"

        return (
            f"Extrahuj strukturovana data z nasledujiciho emailu:\n\n"
            f"PREDMET: {subject}\n\n"
            f"TELO EMAILU:\n{truncated_body}"
        )

    @staticmethod
    def _parse_response(
        response: object,
        log: structlog.stdlib.BoundLogger,
    ) -> ParsedInquiry:
        """Parse the Anthropic API response into a ParsedInquiry.

        Args:
            response: The raw API response from Anthropic.
            log: Bound structlog logger for contextual logging.

        Returns:
            Parsed ParsedInquiry, or empty ParsedInquiry on parse failure.
        """
        # Extract tool_use block from response content
        tool_input: dict[str, object] | None = None
        for block in response.content:  # type: ignore[attr-defined]
            if block.type == "tool_use" and block.name == "parse_inquiry":
                tool_input = block.input  # type: ignore[assignment]
                break

        if tool_input is None:
            log.error(
                "email_parsing.no_tool_use_block",
                response_content=str(response.content),  # type: ignore[attr-defined]
            )
            return ParsedInquiry()

        # Parse items list
        items: list[ParsedItem] = []
        raw_items = tool_input.get("items", [])
        if isinstance(raw_items, list):
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    continue
                name = raw_item.get("name")
                if not name or not isinstance(name, str):
                    continue

                # Parse quantity safely
                quantity: float | None = None
                raw_quantity = raw_item.get("quantity")
                if raw_quantity is not None:
                    try:
                        quantity = float(raw_quantity)  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        quantity = None

                items.append(
                    ParsedItem(
                        name=name,
                        material=_str_or_none(raw_item.get("material")),
                        quantity=quantity,
                        unit=_str_or_none(raw_item.get("unit")),
                        dimensions=_str_or_none(raw_item.get("dimensions")),
                    )
                )

        result = ParsedInquiry(
            company_name=_str_or_none(tool_input.get("company_name")),
            contact_name=_str_or_none(tool_input.get("contact_name")),
            email=_str_or_none(tool_input.get("email")),
            phone=_str_or_none(tool_input.get("phone")),
            items=items,
            deadline=_str_or_none(tool_input.get("deadline")),
            note=_str_or_none(tool_input.get("note")),
        )

        log.info(
            "email_parsing.completed",
            company_name=result.company_name,
            items_count=len(result.items),
            has_deadline=result.deadline is not None,
        )

        return result


def _str_or_none(value: object) -> str | None:
    """Convert a value to string, returning None for empty/null values.

    Args:
        value: Any value from the parsed tool output.

    Returns:
        The string representation, or None if the value is falsy.
    """
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None
