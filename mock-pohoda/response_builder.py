"""Generator for Pohoda responsePack XML responses."""

from lxml import etree

RSP_NS = "http://www.stormware.cz/schema/version_2/response.xsd"
NSMAP = {"rsp": RSP_NS}


def build_response_pack(
    item_id: str,
    pohoda_id: int,
    state: str = "ok",
    note: str = "Záznam uložen",
    pack_id: str = "mock-001",
) -> bytes:
    """Build responsePack XML matching Pohoda mServer format.

    Args:
        item_id: ID of the dataPackItem being responded to.
        pohoda_id: Auto-generated Pohoda internal record ID.
        state: Response state ("ok" or "error").
        note: Human-readable response note (Czech).
        pack_id: Response pack identifier.

    Returns:
        XML bytes encoded in Windows-1250.
    """
    root = etree.Element(
        f"{{{RSP_NS}}}responsePack",
        nsmap=NSMAP,
        version="2.0",
        id=pack_id,
    )

    item = etree.SubElement(
        root,
        f"{{{RSP_NS}}}responsePackItem",
        version="2.0",
        id=item_id,
    )

    state_elem = etree.SubElement(item, f"{{{RSP_NS}}}state")
    state_elem.text = state

    id_elem = etree.SubElement(item, f"{{{RSP_NS}}}id")
    id_elem.text = str(pohoda_id)

    note_elem = etree.SubElement(item, f"{{{RSP_NS}}}note")
    note_elem.text = note

    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="Windows-1250",
        pretty_print=True,
    )


def build_error_response(
    item_id: str,
    error_message: str,
    pack_id: str = "mock-err",
) -> bytes:
    """Build error responsePack XML."""
    return build_response_pack(
        item_id=item_id,
        pohoda_id=0,
        state="error",
        note=error_message,
        pack_id=pack_id,
    )


def build_stock_list_response(stock_items: list[dict]) -> bytes:
    """Build stock list response XML matching Pohoda listStock format.

    Args:
        stock_items: List of stock item dicts with keys:
            code, name, unit, purchasing_price, selling_price, quantity, supplier, note

    Returns:
        XML bytes encoded in Windows-1250.
    """
    RSP_NS_URL = RSP_NS
    LST_NS = "http://www.stormware.cz/schema/version_2/list_stock.xsd"
    STK_NS = "http://www.stormware.cz/schema/version_2/stock.xsd"
    TYP_NS = "http://www.stormware.cz/schema/version_2/type.xsd"

    nsmap = {
        "rsp": RSP_NS_URL,
        "lStk": LST_NS,
        "stk": STK_NS,
        "typ": TYP_NS,
    }

    root = etree.Element(
        f"{{{RSP_NS_URL}}}responsePack",
        nsmap=nsmap,
        version="2.0",
        id="mock-stock",
    )

    item = etree.SubElement(
        root,
        f"{{{RSP_NS_URL}}}responsePackItem",
        version="2.0",
        id="stk001",
    )

    list_stock = etree.SubElement(
        item,
        f"{{{LST_NS}}}listStock",
        version="2.0",
    )

    for stock in stock_items:
        stock_elem = etree.SubElement(list_stock, f"{{{LST_NS}}}stock", version="2.0")
        header = etree.SubElement(stock_elem, f"{{{STK_NS}}}stockHeader")

        code_elem = etree.SubElement(header, f"{{{STK_NS}}}code")
        code_elem.text = stock["code"]

        name_elem = etree.SubElement(header, f"{{{STK_NS}}}name")
        name_elem.text = stock["name"]

        unit_elem = etree.SubElement(header, f"{{{STK_NS}}}unit")
        unit_elem.text = stock["unit"]

        # Purchasing price
        purchase = etree.SubElement(header, f"{{{STK_NS}}}purchasingPrice")
        purchase.text = f"{stock['purchasing_price']:.2f}"

        # Selling price
        selling = etree.SubElement(header, f"{{{STK_NS}}}sellingPrice")
        selling.text = f"{stock['selling_price']:.2f}"

        # Quantity in stock
        count = etree.SubElement(header, f"{{{STK_NS}}}count")
        count.text = f"{stock.get('quantity', 0):.2f}"

        # Note
        if stock.get("note"):
            note_elem = etree.SubElement(header, f"{{{STK_NS}}}note")
            note_elem.text = stock["note"]

        # Supplier
        if stock.get("supplier"):
            supplier_elem = etree.SubElement(header, f"{{{STK_NS}}}supplier")
            company = etree.SubElement(supplier_elem, f"{{{TYP_NS}}}company")
            company.text = stock["supplier"]

    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="Windows-1250",
        pretty_print=True,
    )
