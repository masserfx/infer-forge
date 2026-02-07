"""Pohoda XML builder for dataPack documents.

Builds XML documents for Pohoda accounting system with Windows-1250 encoding.
Supports customer (addressbook), order, and offer document types.
"""

from datetime import date, datetime
from decimal import Decimal

from lxml import etree

from app.core.config import get_settings
from app.models.customer import Customer
from app.models.offer import Offer
from app.models.order import Order

# Pohoda XML namespaces (version 2.0)
NAMESPACES = {
    "dat": "http://www.stormware.cz/schema/version_2/data.xsd",
    "adb": "http://www.stormware.cz/schema/version_2/addressbook.xsd",
    "ofr": "http://www.stormware.cz/schema/version_2/offer.xsd",
    "ord": "http://www.stormware.cz/schema/version_2/order.xsd",
    "inv": "http://www.stormware.cz/schema/version_2/invoice.xsd",
    "typ": "http://www.stormware.cz/schema/version_2/type.xsd",
    "ftr": "http://www.stormware.cz/schema/version_2/filter.xsd",
    "prn": "http://www.stormware.cz/schema/version_2/print.xsd",
    "lAdb": "http://www.stormware.cz/schema/version_2/list_addBook.xsd",
}


class PohodaXMLBuilder:
    """Builder for Pohoda XML documents with proper encoding and structure.

    All XML documents are wrapped in dataPack envelope with company IČO,
    application name, and XML version. Uses Windows-1250 encoding as required
    by Pohoda.
    """

    def __init__(self) -> None:
        """Initialize XML builder with configuration settings."""
        self.settings = get_settings()
        self.ico = self.settings.POHODA_ICO
        self.xml_version = self.settings.POHODA_XML_VERSION
        self.application = self.settings.POHODA_APPLICATION

    def _create_datapack_root(self) -> etree.Element:
        """Create root dataPack element with namespaces and attributes.

        Returns:
            etree.Element: Root dataPack element with proper namespaces.
        """
        nsmap = {k if k != "dat" else None: v for k, v in NAMESPACES.items()}
        root = etree.Element(
            f"{{{NAMESPACES['dat']}}}dataPack",
            nsmap=nsmap,
            version=self.xml_version,
            ico=self.ico,
            application=self.application,
            id="IF001",  # Unique ID for this dataPack
        )
        return root

    def _create_datapack_item(
        self,
        parent: etree.Element,
        item_id: str,
        version: str = "2.0",
    ) -> etree.Element:
        """Create dataPackItem element to wrap individual documents.

        Args:
            parent: Parent dataPack element.
            item_id: Unique ID for this item.
            version: XML schema version.

        Returns:
            etree.Element: Created dataPackItem element.
        """
        item = etree.SubElement(
            parent,
            f"{{{NAMESPACES['dat']}}}dataPackItem",
            version=version,
            id=item_id,
        )
        return item

    def _format_date(self, dt: date | datetime | None) -> str | None:
        """Format date/datetime to Pohoda format (YYYY-MM-DD).

        Args:
            dt: Date or datetime to format.

        Returns:
            str: Formatted date string or None if input is None.
        """
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.date().isoformat()
        return dt.isoformat()

    def _format_decimal(self, value: Decimal | None) -> str | None:
        """Format Decimal to string with 2 decimal places.

        Args:
            value: Decimal value to format.

        Returns:
            str: Formatted decimal string or None if input is None.
        """
        if value is None:
            return None
        return f"{value:.2f}"

    def _add_element(
        self,
        parent: etree.Element,
        tag: str,
        text: str | None = None,
        **attrs: str,
    ) -> etree.Element:
        """Add child element with optional text and attributes.

        Args:
            parent: Parent element.
            tag: Tag name (without namespace).
            text: Optional text content.
            **attrs: Optional attributes.

        Returns:
            etree.Element: Created element.
        """
        elem = etree.SubElement(parent, tag, **attrs)
        if text is not None:
            elem.text = text
        return elem

    def build_customer_xml(self, customer: Customer) -> bytes:
        """Build addressbook XML for customer synchronization.

        Creates Pohoda addressbook (adb:addressbook) document for creating
        or updating customer in Pohoda accounting system.

        Args:
            customer: Customer model instance.

        Returns:
            bytes: XML document as bytes in Windows-1250 encoding.
        """
        root = self._create_datapack_root()
        item = self._create_datapack_item(root, f"ADB{customer.ico}")

        # Create addressbook element
        adb = self._add_element(item, f"{{{NAMESPACES['adb']}}}addressbook")

        # Action header (add new or update existing)
        action = "update" if customer.pohoda_id else "add-intercompany"
        action_type = etree.SubElement(
            adb,
            f"{{{NAMESPACES['adb']}}}actionType",
        )
        self._add_element(action_type, f"{{{NAMESPACES['adb']}}}{action}")

        # Addressbook header
        header = self._add_element(adb, f"{{{NAMESPACES['adb']}}}addressbookHeader")

        # Identity section (company info)
        identity = self._add_element(header, f"{{{NAMESPACES['typ']}}}identity")

        # Address section
        address = self._add_element(identity, f"{{{NAMESPACES['typ']}}}address")
        self._add_element(address, f"{{{NAMESPACES['typ']}}}company", customer.company_name)

        # Split address into street, city, zip if possible
        if customer.address:
            # Simple split - take first line as street, rest as city/zip
            address_lines = customer.address.strip().split("\n")
            if address_lines:
                street = address_lines[0][:64]
                self._add_element(address, f"{{{NAMESPACES['typ']}}}street", street)
                if len(address_lines) > 1:
                    city = address_lines[1][:45]
                    self._add_element(address, f"{{{NAMESPACES['typ']}}}city", city)

        # IČO
        self._add_element(address, f"{{{NAMESPACES['typ']}}}ico", customer.ico)

        # DIČ (if available)
        if customer.dic:
            self._add_element(address, f"{{{NAMESPACES['typ']}}}dic", customer.dic)

        # Contact info
        if customer.phone:
            self._add_element(address, f"{{{NAMESPACES['typ']}}}mobilPhone", customer.phone[:40])

        self._add_element(address, f"{{{NAMESPACES['typ']}}}email", customer.email)

        # Contact person
        if customer.contact_name:
            self._add_element(header, f"{{{NAMESPACES['adb']}}}email", customer.email)

        # Serialize to bytes with Windows-1250 encoding
        return etree.tostring(
            root,
            xml_declaration=True,
            encoding="Windows-1250",
            pretty_print=True,
        )

    def build_order_xml(self, order: Order, customer: Customer) -> bytes:
        """Build order XML document for Pohoda.

        Creates Pohoda order (ord:order) document with all order items.

        Args:
            order: Order model instance.
            customer: Related customer model instance.

        Returns:
            bytes: XML document as bytes in Windows-1250 encoding.
        """
        root = self._create_datapack_root()
        item = self._create_datapack_item(root, f"ORD{order.number}")

        # Create order element
        order_elem = self._add_element(item, f"{{{NAMESPACES['ord']}}}order")

        # Order header
        header = self._add_element(order_elem, f"{{{NAMESPACES['ord']}}}orderHeader")

        # Order number
        number = self._add_element(header, f"{{{NAMESPACES['ord']}}}number")
        self._add_element(number, f"{{{NAMESPACES['typ']}}}numberRequested", order.number)

        # Date (created date)
        order_date = self._format_date(order.created_at)
        if order_date:
            self._add_element(header, f"{{{NAMESPACES['ord']}}}date", order_date)

        # Due date (if available)
        if order.due_date:
            due_date = self._format_date(order.due_date)
            self._add_element(header, f"{{{NAMESPACES['ord']}}}dateDelivery", due_date)

        # Partner reference (customer)
        partner = self._add_element(header, f"{{{NAMESPACES['typ']}}}partnerIdentity")
        address = self._add_element(partner, f"{{{NAMESPACES['typ']}}}address")
        self._add_element(address, f"{{{NAMESPACES['typ']}}}company", customer.company_name)
        self._add_element(address, f"{{{NAMESPACES['typ']}}}ico", customer.ico)

        # Note
        if order.note:
            self._add_element(header, f"{{{NAMESPACES['ord']}}}note", order.note[:240])

        # Order detail (items)
        detail = self._add_element(order_elem, f"{{{NAMESPACES['ord']}}}orderDetail")

        for order_item in order.items:
            item_elem = self._add_element(detail, f"{{{NAMESPACES['ord']}}}orderItem")

            # Item text (name + material + DN/PN)
            text_parts = [order_item.name]
            if order_item.material:
                text_parts.append(f"Mat: {order_item.material}")
            if order_item.dn:
                text_parts.append(f"DN{order_item.dn}")
            if order_item.pn:
                text_parts.append(f"PN{order_item.pn}")

            item_text = " | ".join(text_parts)
            self._add_element(item_elem, f"{{{NAMESPACES['ord']}}}text", item_text[:90])

            # Quantity
            quantity = self._format_decimal(order_item.quantity)
            self._add_element(item_elem, f"{{{NAMESPACES['ord']}}}quantity", quantity)

            # Unit
            self._add_element(item_elem, f"{{{NAMESPACES['ord']}}}unit", order_item.unit)

            # Note
            if order_item.note:
                self._add_element(item_elem, f"{{{NAMESPACES['ord']}}}note", order_item.note[:240])

        # Serialize to bytes with Windows-1250 encoding
        return etree.tostring(
            root,
            xml_declaration=True,
            encoding="Windows-1250",
            pretty_print=True,
        )

    def build_offer_xml(
        self,
        offer: Offer,
        order: Order,
        customer: Customer,
    ) -> bytes:
        """Build offer XML document for Pohoda.

        Creates Pohoda offer (ofr:offer) document based on order and its items.

        Args:
            offer: Offer model instance.
            order: Related order model instance.
            customer: Related customer model instance.

        Returns:
            bytes: XML document as bytes in Windows-1250 encoding.
        """
        root = self._create_datapack_root()
        item = self._create_datapack_item(root, f"OFR{offer.number}")

        # Create offer element
        ofr = self._add_element(item, f"{{{NAMESPACES['ofr']}}}offer")

        # Offer header
        header = self._add_element(ofr, f"{{{NAMESPACES['ofr']}}}offerHeader")

        # Offer number
        number = self._add_element(header, f"{{{NAMESPACES['ofr']}}}number")
        self._add_element(number, f"{{{NAMESPACES['typ']}}}numberRequested", offer.number)

        # Date (created date)
        offer_date = self._format_date(offer.created_at)
        if offer_date:
            self._add_element(header, f"{{{NAMESPACES['ofr']}}}date", offer_date)

        # Valid until date
        valid_until = self._format_date(offer.valid_until)
        self._add_element(header, f"{{{NAMESPACES['ofr']}}}dateValidTill", valid_until)

        # Partner reference (customer)
        partner = self._add_element(header, f"{{{NAMESPACES['typ']}}}partnerIdentity")
        address = self._add_element(partner, f"{{{NAMESPACES['typ']}}}address")
        self._add_element(address, f"{{{NAMESPACES['typ']}}}company", customer.company_name)
        self._add_element(address, f"{{{NAMESPACES['typ']}}}ico", customer.ico)

        # Note from order
        if order.note:
            self._add_element(header, f"{{{NAMESPACES['ofr']}}}note", order.note[:240])

        # Offer detail (items from order)
        detail = self._add_element(ofr, f"{{{NAMESPACES['ofr']}}}offerDetail")

        for order_item in order.items:
            item_elem = self._add_element(detail, f"{{{NAMESPACES['ofr']}}}offerItem")

            # Item text (name + material + DN/PN)
            text_parts = [order_item.name]
            if order_item.material:
                text_parts.append(f"Mat: {order_item.material}")
            if order_item.dn:
                text_parts.append(f"DN{order_item.dn}")
            if order_item.pn:
                text_parts.append(f"PN{order_item.pn}")

            item_text = " | ".join(text_parts)
            self._add_element(item_elem, f"{{{NAMESPACES['ofr']}}}text", item_text[:90])

            # Quantity
            quantity = self._format_decimal(order_item.quantity)
            self._add_element(item_elem, f"{{{NAMESPACES['ofr']}}}quantity", quantity)

            # Unit
            self._add_element(item_elem, f"{{{NAMESPACES['ofr']}}}unit", order_item.unit)

            # Note
            if order_item.note:
                self._add_element(item_elem, f"{{{NAMESPACES['ofr']}}}note", order_item.note[:240])

        # Offer summary (total price)
        summary = self._add_element(ofr, f"{{{NAMESPACES['ofr']}}}offerSummary")
        home_currency = self._add_element(summary, f"{{{NAMESPACES['typ']}}}homeCurrency")
        price_none = self._add_element(home_currency, f"{{{NAMESPACES['typ']}}}priceNone")
        formatted_price = self._format_decimal(offer.total_price)
        self._add_element(price_none, f"{{{NAMESPACES['typ']}}}price", formatted_price)

        # Serialize to bytes with Windows-1250 encoding
        return etree.tostring(
            root,
            xml_declaration=True,
            encoding="Windows-1250",
            pretty_print=True,
        )
