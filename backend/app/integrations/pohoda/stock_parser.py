"""Pohoda stock (stk:stock) XML parser for inventory sync."""

import logging
from dataclasses import dataclass
from decimal import Decimal

from lxml import etree

from .exceptions import PohodaXMLError

logger = logging.getLogger(__name__)

# Namespaces for stock list responses
STOCK_NAMESPACES = {
    "rsp": "http://www.stormware.cz/schema/version_2/response.xsd",
    "lStk": "http://www.stormware.cz/schema/version_2/list_stock.xsd",
    "stk": "http://www.stormware.cz/schema/version_2/stock.xsd",
    "typ": "http://www.stormware.cz/schema/version_2/type.xsd",
}


@dataclass
class StockItem:
    """Parsed Pohoda stock card."""
    code: str
    name: str
    unit: str
    purchasing_price: Decimal
    selling_price: Decimal | None
    note: str | None
    storage: str | None
    supplier: str | None


class PohodaStockParser:
    """Parser for Pohoda stock list XML responses."""

    @staticmethod
    def parse_stock_list(xml_bytes: bytes) -> list[StockItem]:
        """Parse Pohoda stock list response XML.

        Args:
            xml_bytes: XML as bytes (Windows-1250 encoded)

        Returns:
            List of parsed stock items

        Raises:
            PohodaXMLError: If XML is invalid
        """
        try:
            root = etree.fromstring(xml_bytes)
        except etree.XMLSyntaxError as e:
            raise PohodaXMLError(f"Invalid stock XML: {e}") from e

        items: list[StockItem] = []

        # Find all stock elements: rsp:responsePack > rsp:responsePackItem > lStk:listStock > lStk:stock
        for stock_elem in root.iter(f"{{{STOCK_NAMESPACES['lStk']}}}stock"):
            header = stock_elem.find(f"{{{STOCK_NAMESPACES['stk']}}}stockHeader")
            if header is None:
                continue

            # Extract fields
            code_el = header.find(f"{{{STOCK_NAMESPACES['stk']}}}code")
            name_el = header.find(f"{{{STOCK_NAMESPACES['stk']}}}name")
            unit_el = header.find(f"{{{STOCK_NAMESPACES['stk']}}}unit")
            purch_el = header.find(f"{{{STOCK_NAMESPACES['stk']}}}purchasingPrice")
            sell_el = header.find(f"{{{STOCK_NAMESPACES['stk']}}}sellingPrice")
            note_el = header.find(f"{{{STOCK_NAMESPACES['stk']}}}note")

            # Storage: stk:storage > typ:ids
            storage_el = header.find(f"{{{STOCK_NAMESPACES['stk']}}}storage")
            storage = None
            if storage_el is not None:
                storage_ids = storage_el.find(f"{{{STOCK_NAMESPACES['typ']}}}ids")
                if storage_ids is not None:
                    storage = storage_ids.text

            # Supplier: stk:supplier > typ:ids
            supplier_el = header.find(f"{{{STOCK_NAMESPACES['stk']}}}supplier")
            supplier = None
            if supplier_el is not None:
                supplier_ids = supplier_el.find(f"{{{STOCK_NAMESPACES['typ']}}}ids")
                if supplier_ids is not None:
                    supplier = supplier_ids.text

            # Required fields
            code = code_el.text if code_el is not None else None
            name = name_el.text if name_el is not None else None
            if not code or not name:
                logger.warning("Skipping stock item with missing code or name")
                continue

            unit = (unit_el.text if unit_el is not None else None) or "ks"
            try:
                purchasing_price = Decimal(purch_el.text) if purch_el is not None and purch_el.text else Decimal("0")
            except Exception:
                purchasing_price = Decimal("0")

            selling_price = None
            if sell_el is not None and sell_el.text:
                try:
                    selling_price = Decimal(sell_el.text)
                except Exception:
                    pass

            note = note_el.text if note_el is not None else None

            items.append(StockItem(
                code=code,
                name=name,
                unit=unit,
                purchasing_price=purchasing_price,
                selling_price=selling_price,
                note=note,
                storage=storage,
                supplier=supplier,
            ))

        logger.info("Parsed %d stock items from Pohoda XML", len(items))
        return items
