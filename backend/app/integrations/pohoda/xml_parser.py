"""XML response parser for Pohoda mServer responses.

This module provides parsing functionality for XML responses received from
Pohoda mServer. It extracts response items (success/error states) and provides
structured data for further processing.
"""

import logging
from dataclasses import dataclass

from lxml import etree

from .exceptions import PohodaXMLError

logger = logging.getLogger(__name__)

# Pohoda XML namespaces for response documents
RSP_NAMESPACES = {
    "rsp": "http://www.stormware.cz/schema/version_2/response.xsd",
}


@dataclass
class PohodaResponseItem:
    """Single response item from Pohoda.

    Each item represents result of one operation (e.g. one invoice created,
    one address updated). Pohoda can return multiple items in single response.

    Attributes:
        id: Pohoda internal record ID (empty string if operation failed)
        state: Operation state - "ok" for success, "error" for failure
        note: Human-readable response message (Czech text from Pohoda)
    """

    id: str
    state: str
    note: str

    @property
    def is_success(self) -> bool:
        """Check if this item represents successful operation.

        Returns:
            True if state is "ok", False otherwise
        """
        return self.state.lower() == "ok"


@dataclass
class PohodaResponse:
    """Parsed Pohoda mServer response.

    Contains all response items and overall success status.
    Preserves raw XML for debugging and audit trail.

    Attributes:
        pack_id: Response pack ID from mServer
        success: True if all items succeeded, False if any failed
        items: List of individual response items
        raw_xml: Original XML response as string (for audit/debugging)
    """

    pack_id: str
    success: bool
    items: list[PohodaResponseItem]
    raw_xml: str


class PohodaXMLParser:
    """Parser for Pohoda XML responses.

    Handles parsing of XML documents received from Pohoda mServer.
    Supports Windows-1250 encoding and extracts structured data
    from response elements.

    Example:
        parser = PohodaXMLParser()
        response = parser.parse_response(xml_bytes)
        if response.success:
            print(f"Created records: {[item.id for item in response.items]}")
    """

    @staticmethod
    def parse_response(xml_bytes: bytes) -> PohodaResponse:
        """Parse mServer response XML.

        The response from Pohoda looks like:
        <?xml version="1.0" encoding="Windows-1250"?>
        <rsp:responsePack version="2.0" ...>
          <rsp:responsePackItem version="2.0" id="...">
            <rsp:state>ok</rsp:state>
            <rsp:note>...</rsp:note>
            <rsp:id>12345</rsp:id>
          </rsp:responsePackItem>
          ...
        </rsp:responsePack>

        Args:
            xml_bytes: XML response as bytes (typically Windows-1250 encoded)

        Returns:
            Parsed PohodaResponse with all items

        Raises:
            PohodaXMLError: If XML cannot be parsed or has invalid structure
        """
        try:
            # Decode from Windows-1250 if bytes
            if isinstance(xml_bytes, bytes):
                try:
                    xml_string = xml_bytes.decode("windows-1250")
                except UnicodeDecodeError:
                    # Fallback to UTF-8 (some test scenarios)
                    logger.warning("Failed to decode as Windows-1250, trying UTF-8")
                    xml_string = xml_bytes.decode("utf-8")
            else:
                xml_string = xml_bytes

            # Parse XML
            try:
                root = etree.fromstring(xml_bytes)
            except etree.XMLSyntaxError as e:
                raise PohodaXMLError(f"Invalid XML syntax: {str(e)}") from e

            # Extract pack ID from root element
            pack_id = root.get("id", "")

            # Find all responsePackItem elements
            items_elements = root.findall(
                "rsp:responsePackItem",
                namespaces=RSP_NAMESPACES,
            )

            if not items_elements:
                logger.warning("No responsePackItem elements found in response")

            # Parse each response item
            items: list[PohodaResponseItem] = []
            for item_elem in items_elements:
                state_elem = item_elem.find("rsp:state", namespaces=RSP_NAMESPACES)
                note_elem = item_elem.find("rsp:note", namespaces=RSP_NAMESPACES)
                id_elem = item_elem.find("rsp:id", namespaces=RSP_NAMESPACES)

                # Extract text values, handle None (missing) and "" (empty) elements
                state = (state_elem.text if state_elem is not None else None) or "error"
                note = (note_elem.text if note_elem is not None else None) or ""
                item_id = (id_elem.text if id_elem is not None else None) or ""

                items.append(
                    PohodaResponseItem(
                        id=item_id,
                        state=state,
                        note=note,
                    )
                )

            # Overall success = all items are successful
            success = all(item.is_success for item in items) if items else False

            logger.info(
                "Parsed Pohoda response: pack_id=%s, items=%d, success=%s",
                pack_id,
                len(items),
                success,
            )

            return PohodaResponse(
                pack_id=pack_id,
                success=success,
                items=items,
                raw_xml=xml_string,
            )

        except PohodaXMLError:
            raise
        except Exception as e:
            logger.exception("Unexpected error parsing Pohoda XML response")
            raise PohodaXMLError(
                f"Failed to parse Pohoda response: {type(e).__name__}: {str(e)}"
            ) from e
