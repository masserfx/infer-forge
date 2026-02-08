"""Mock Pohoda mServer — FastAPI application simulating Pohoda XML API."""

import logging
import os
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from lxml import etree

from db import DocumentStore
from response_builder import build_error_response, build_response_pack, build_stock_list_response
from stock_data import STOCK_ITEMS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock-pohoda")

app = FastAPI(title="Mock Pohoda mServer", version="1.0.0")

db_path = os.environ.get("DB_PATH", "/data/pohoda.db")
store = DocumentStore(db_path=db_path)

templates = Jinja2Templates(directory="templates")

# Namespace URIs for parsing incoming dataPack XML
DAT_NS = "http://www.stormware.cz/schema/version_2/data.xsd"
ADB_NS = "http://www.stormware.cz/schema/version_2/addressbook.xsd"
ORD_NS = "http://www.stormware.cz/schema/version_2/order.xsd"
OFR_NS = "http://www.stormware.cz/schema/version_2/offer.xsd"
INV_NS = "http://www.stormware.cz/schema/version_2/invoice.xsd"
LSTK_NS = "http://www.stormware.cz/schema/version_2/list_stock.xsd"
TYP_NS = "http://www.stormware.cz/schema/version_2/type.xsd"

DOC_TYPE_MAP = {
    f"{{{ADB_NS}}}addressbook": "addressbook",
    f"{{{ORD_NS}}}order": "order",
    f"{{{OFR_NS}}}offer": "offer",
    f"{{{INV_NS}}}invoice": "invoice",
}

HEADER_TAG_MAP = {
    "addressbook": f"{{{ADB_NS}}}addressbookHeader",
    "order": f"{{{ORD_NS}}}orderHeader",
    "offer": f"{{{OFR_NS}}}offerHeader",
    "invoice": f"{{{INV_NS}}}invoiceHeader",
}

DOC_TYPE_LABELS = {
    "addressbook": "Adresář",
    "order": "Objednávka",
    "offer": "Nabídka",
    "invoice": "Faktura",
    "stock_request": "Sklad",
}


def _extract_text(elem: etree._Element | None, xpath: str, nsmap: dict) -> str:
    """Safely extract text from an element via XPath."""
    if elem is None:
        return ""
    found = elem.find(xpath, namespaces=nsmap)
    return (found.text or "") if found is not None else ""


def _parse_datapack(xml_bytes: bytes) -> list[dict]:
    """Parse incoming dataPack XML and extract document metadata.

    Returns list of dicts: [{doc_type, doc_number, company_name, ico, item_id}]
    """
    root = etree.fromstring(xml_bytes)
    results = []

    nsmap = {
        "dat": DAT_NS,
        "adb": ADB_NS,
        "ord": ORD_NS,
        "ofr": OFR_NS,
        "inv": INV_NS,
        "typ": TYP_NS,
        "lStk": LSTK_NS,
    }

    items = root.findall("dat:dataPackItem", namespaces=nsmap)
    if not items:
        # Fallback: try without namespace prefix
        items = root.findall(f"{{{DAT_NS}}}dataPackItem")

    for pack_item in items:
        item_id = pack_item.get("id", "unknown")

        # Detect document type from first child element
        doc_type = None
        doc_elem = None
        for child in pack_item:
            tag = child.tag
            if tag in DOC_TYPE_MAP:
                doc_type = DOC_TYPE_MAP[tag]
                doc_elem = child
                break
            # Check for stock list request
            if LSTK_NS in tag:
                doc_type = "stock_request"
                break

        if doc_type == "stock_request":
            results.append({
                "doc_type": "stock_request",
                "doc_number": "",
                "company_name": "",
                "ico": "",
                "item_id": item_id,
            })
            continue

        if not doc_type or doc_elem is None:
            logger.warning("Unknown document type in dataPackItem id=%s", item_id)
            continue

        # Extract header info
        header_tag = HEADER_TAG_MAP.get(doc_type)
        header = doc_elem.find(header_tag) if header_tag else None

        # Extract document number
        doc_number = ""
        if header is not None:
            # Try different number patterns
            for ns_prefix in ["ord", "ofr", "inv", "adb"]:
                ns_url = nsmap.get(ns_prefix, "")
                if not ns_url:
                    continue
                num_elem = header.find(f"{{{ns_url}}}number")
                if num_elem is not None:
                    requested = num_elem.find(f"{{{TYP_NS}}}numberRequested")
                    if requested is not None and requested.text:
                        doc_number = requested.text
                        break

        # Extract company info from partner identity
        company_name = ""
        ico = ""
        if header is not None:
            partner = header.find(f"{{{TYP_NS}}}partnerIdentity")
            if partner is not None:
                addr = partner.find(f"{{{TYP_NS}}}address")
                if addr is not None:
                    company_name = _extract_text(addr, f"{{{TYP_NS}}}company", nsmap)
                    ico = _extract_text(addr, f"{{{TYP_NS}}}ico", nsmap)

            # For addressbook, company is in identity/address
            if doc_type == "addressbook":
                identity = header.find(f"{{{TYP_NS}}}identity")
                if identity is not None:
                    addr = identity.find(f"{{{TYP_NS}}}address")
                    if addr is not None:
                        company_name = _extract_text(addr, f"{{{TYP_NS}}}company", nsmap)
                        ico = _extract_text(addr, f"{{{TYP_NS}}}ico", nsmap)

        results.append({
            "doc_type": doc_type,
            "doc_number": doc_number,
            "company_name": company_name,
            "ico": ico,
            "item_id": item_id,
        })

    return results


@app.post("/xml")
async def receive_xml(request: Request) -> Response:
    """Receive Pohoda XML dataPack, parse, store, and return responsePack."""
    body = await request.body()

    if not body:
        error_xml = build_error_response("empty", "Prázdný požadavek")
        return Response(
            content=error_xml,
            media_type="application/xml; charset=Windows-1250",
        )

    # Decode from Windows-1250
    try:
        xml_string = body.decode("windows-1250")
    except UnicodeDecodeError:
        xml_string = body.decode("utf-8", errors="replace")

    try:
        documents = _parse_datapack(body)
    except etree.XMLSyntaxError as e:
        logger.error("XML parse error: %s", str(e))
        error_xml = build_error_response("parse-error", f"Chyba XML syntaxe: {str(e)[:100]}")
        return Response(
            content=error_xml,
            media_type="application/xml; charset=Windows-1250",
        )

    if not documents:
        error_xml = build_error_response("empty-pack", "Prázdný dataPack — žádné položky")
        return Response(
            content=error_xml,
            media_type="application/xml; charset=Windows-1250",
        )

    # Handle stock list request
    for doc in documents:
        if doc["doc_type"] == "stock_request":
            logger.info("Stock list request received")
            response_xml = build_stock_list_response(STOCK_ITEMS)
            return Response(
                content=response_xml,
                media_type="application/xml; charset=Windows-1250",
            )

    # Process each document
    # For simplicity, respond to the first document (dataPack usually contains one)
    doc = documents[0]
    pohoda_id = store.get_next_pohoda_id()

    note_map = {
        "addressbook": "Záznam v adresáři uložen",
        "order": "Objednávka přijata uložena",
        "offer": "Nabídka uložena",
        "invoice": "Faktura vystavena",
    }
    note = note_map.get(doc["doc_type"], "Záznam uložen")

    response_xml = build_response_pack(
        item_id=doc["item_id"],
        pohoda_id=pohoda_id,
        state="ok",
        note=note,
    )

    store.save_document(
        doc_type=doc["doc_type"],
        doc_number=doc["doc_number"],
        company_name=doc["company_name"],
        ico=doc["ico"],
        xml_request=xml_string,
        xml_response=response_xml.decode("windows-1250", errors="replace"),
        pohoda_id=pohoda_id,
    )

    logger.info(
        "Document stored: type=%s number=%s pohoda_id=%d company=%s",
        doc["doc_type"],
        doc["doc_number"],
        pohoda_id,
        doc["company_name"],
    )

    return Response(
        content=response_xml,
        media_type="application/xml; charset=Windows-1250",
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """HTML dashboard showing received documents."""
    docs = store.get_all_documents(limit=100)
    stats = store.get_stats()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "documents": docs,
            "stats": stats,
            "type_labels": DOC_TYPE_LABELS,
            "now": datetime.now().strftime("%d.%m.%Y %H:%M"),
        },
    )


@app.get("/xml/docs/{doc_id}", response_class=HTMLResponse)
async def document_detail(request: Request, doc_id: int) -> HTMLResponse:
    """Show XML detail of a stored document."""
    doc = store.get_document(doc_id)
    if not doc:
        return HTMLResponse(content="<h1>Doklad nenalezen</h1>", status_code=404)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "documents": [doc],
            "stats": store.get_stats(),
            "type_labels": DOC_TYPE_LABELS,
            "now": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "detail": doc,
        },
    )


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    stats = store.get_stats()
    return {
        "status": "healthy",
        "service": "mock-pohoda-mserver",
        "documents_count": stats["total"],
        "timestamp": datetime.now().isoformat(),
    }
