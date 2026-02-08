"""Tests for Pohoda stock (inventory) sync."""

from decimal import Decimal

import pytest

from app.integrations.pohoda.stock_parser import PohodaStockParser, StockItem

VALID_STOCK_XML = b"""<?xml version="1.0" encoding="Windows-1250"?>
<rsp:responsePack version="2.0"
  xmlns:rsp="http://www.stormware.cz/schema/version_2/response.xsd"
  xmlns:lStk="http://www.stormware.cz/schema/version_2/list_stock.xsd"
  xmlns:stk="http://www.stormware.cz/schema/version_2/stock.xsd"
  xmlns:typ="http://www.stormware.cz/schema/version_2/type.xsd"
  id="stk001">
  <rsp:responsePackItem version="2.0">
    <lStk:listStock version="2.0">
      <lStk:stock version="2.0">
        <stk:stockHeader>
          <stk:stockType>card</stk:stockType>
          <stk:code>MAT001</stk:code>
          <stk:name>Ocel S235JR plech 10mm</stk:name>
          <stk:unit>kg</stk:unit>
          <stk:purchasingPrice>28.50</stk:purchasingPrice>
          <stk:sellingPrice>42.00</stk:sellingPrice>
          <stk:note>EN 10025-2</stk:note>
          <stk:storage><typ:ids>Sklad 1</typ:ids></stk:storage>
          <stk:supplier><typ:ids>Ferona</typ:ids></stk:supplier>
        </stk:stockHeader>
      </lStk:stock>
      <lStk:stock version="2.0">
        <stk:stockHeader>
          <stk:code>MAT002</stk:code>
          <stk:name>Trubka P265GH DN100</stk:name>
          <stk:unit>m</stk:unit>
          <stk:purchasingPrice>850.00</stk:purchasingPrice>
        </stk:stockHeader>
      </lStk:stock>
    </lStk:listStock>
  </rsp:responsePackItem>
</rsp:responsePack>"""

EMPTY_STOCK_XML = b"""<?xml version="1.0" encoding="Windows-1250"?>
<rsp:responsePack version="2.0"
  xmlns:rsp="http://www.stormware.cz/schema/version_2/response.xsd"
  xmlns:lStk="http://www.stormware.cz/schema/version_2/list_stock.xsd"
  id="stk002">
  <rsp:responsePackItem version="2.0">
    <lStk:listStock version="2.0" />
  </rsp:responsePackItem>
</rsp:responsePack>"""


class TestPohodaStockParser:
    def test_parse_stock_list_valid_xml(self):
        parser = PohodaStockParser()
        items = parser.parse_stock_list(VALID_STOCK_XML)
        assert len(items) == 2
        assert items[0].code == "MAT001"
        assert items[0].name == "Ocel S235JR plech 10mm"
        assert items[0].unit == "kg"
        assert items[0].purchasing_price == Decimal("28.50")
        assert items[0].selling_price == Decimal("42.00")
        assert items[0].note == "EN 10025-2"
        assert items[0].storage == "Sklad 1"
        assert items[0].supplier == "Ferona"

    def test_parse_stock_list_empty(self):
        parser = PohodaStockParser()
        items = parser.parse_stock_list(EMPTY_STOCK_XML)
        assert len(items) == 0

    def test_parse_stock_list_invalid_xml(self):
        from app.integrations.pohoda.exceptions import PohodaXMLError
        parser = PohodaStockParser()
        with pytest.raises(PohodaXMLError):
            parser.parse_stock_list(b"<invalid>xml")

    def test_parse_stock_item_fields(self):
        parser = PohodaStockParser()
        items = parser.parse_stock_list(VALID_STOCK_XML)
        item2 = items[1]
        assert item2.code == "MAT002"
        assert item2.name == "Trubka P265GH DN100"
        assert item2.unit == "m"
        assert item2.purchasing_price == Decimal("850.00")
        assert item2.selling_price is None
        assert item2.supplier is None
        assert item2.storage is None

    def test_parse_stock_item_missing_name_skipped(self):
        xml = b"""<?xml version="1.0" encoding="Windows-1250"?>
        <rsp:responsePack version="2.0"
          xmlns:rsp="http://www.stormware.cz/schema/version_2/response.xsd"
          xmlns:lStk="http://www.stormware.cz/schema/version_2/list_stock.xsd"
          xmlns:stk="http://www.stormware.cz/schema/version_2/stock.xsd">
          <rsp:responsePackItem version="2.0">
            <lStk:listStock version="2.0">
              <lStk:stock version="2.0">
                <stk:stockHeader>
                  <stk:code>MAT999</stk:code>
                </stk:stockHeader>
              </lStk:stock>
            </lStk:listStock>
          </rsp:responsePackItem>
        </rsp:responsePack>"""
        parser = PohodaStockParser()
        items = parser.parse_stock_list(xml)
        assert len(items) == 0

    def test_build_stock_list_request(self):
        from app.integrations.pohoda.xml_builder import PohodaXMLBuilder
        builder = PohodaXMLBuilder()
        xml_bytes = builder.build_stock_list_request()
        assert b"listStockRequest" in xml_bytes
        assert b"Windows-1250" in xml_bytes

    def test_stock_item_dataclass(self):
        item = StockItem(
            code="T1", name="Test", unit="kg",
            purchasing_price=Decimal("10.00"),
            selling_price=None, note=None,
            storage=None, supplier=None,
        )
        assert item.code == "T1"
        assert item.purchasing_price == Decimal("10.00")

    def test_parse_stock_default_unit(self):
        xml = b"""<?xml version="1.0" encoding="Windows-1250"?>
        <rsp:responsePack version="2.0"
          xmlns:rsp="http://www.stormware.cz/schema/version_2/response.xsd"
          xmlns:lStk="http://www.stormware.cz/schema/version_2/list_stock.xsd"
          xmlns:stk="http://www.stormware.cz/schema/version_2/stock.xsd">
          <rsp:responsePackItem version="2.0">
            <lStk:listStock version="2.0">
              <lStk:stock version="2.0">
                <stk:stockHeader>
                  <stk:code>X1</stk:code>
                  <stk:name>No Unit Item</stk:name>
                  <stk:purchasingPrice>5.00</stk:purchasingPrice>
                </stk:stockHeader>
              </lStk:stock>
            </lStk:listStock>
          </rsp:responsePackItem>
        </rsp:responsePack>"""
        parser = PohodaStockParser()
        items = parser.parse_stock_list(xml)
        assert len(items) == 1
        assert items[0].unit == "ks"
