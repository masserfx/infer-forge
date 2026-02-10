"""Architecture graph API — returns codebase analysis as JSON for interactive visualization."""

import json
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/architektura", tags=["architektura"])

# Resolve paths — works both locally (infer-forge/) and in Docker (/prezentace mount)
_LOCAL_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LOCAL_PREZENTACE = _LOCAL_ROOT / "prezentace"
_DOCKER_PREZENTACE = Path("/prezentace")

PREZENTACE = _LOCAL_PREZENTACE if _LOCAL_PREZENTACE.exists() else _DOCKER_PREZENTACE
ANALYZER = PREZENTACE / "analyze_codebase.py"
GRAPH_JSON = PREZENTACE / "graph_data.json"


@router.get("")
async def get_architecture_graph(refresh: bool = False):
    """Return architecture graph data. Use ?refresh=true to re-analyze codebase."""
    if refresh or not GRAPH_JSON.exists():
        if ANALYZER.exists():
            cwd = str(_LOCAL_ROOT) if _LOCAL_PREZENTACE.exists() else "/app"
            result = subprocess.run(
                [sys.executable, str(ANALYZER)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
            )
            if result.returncode != 0:
                # If refresh failed but cached JSON exists, return cached
                if GRAPH_JSON.exists():
                    data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
                    data["_warning"] = f"Refresh failed, serving cached: {result.stderr[:200]}"
                    return data
                return {"error": f"Analyzer failed: {result.stderr}"}

    if not GRAPH_JSON.exists():
        return {"error": "graph_data.json not found. Run analyze_codebase.py first."}

    data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    return data


@router.get("/workflow")
async def get_order_workflow():
    """Return order lifecycle workflow graph generated from actual codebase definitions."""
    from app.models.order import OrderStatus
    from app.services.order import OrderService

    # Read status transitions from actual code
    transitions = OrderService.STATUS_TRANSITIONS

    # Status metadata — Czech labels, colors, descriptions
    status_meta: dict[str, dict] = {
        OrderStatus.POPTAVKA: {
            "label": "Poptávka",
            "description": "Příchozí poptávka od zákazníka (email, telefon, osobně)",
            "color": "#f59e0b",
            "icon": "inbox",
            "phase": "obchod",
        },
        OrderStatus.NABIDKA: {
            "label": "Nabídka",
            "description": "Zpracovaná cenová nabídka s kalkulací nákladů",
            "color": "#8b5cf6",
            "icon": "file-text",
            "phase": "obchod",
        },
        OrderStatus.OBJEDNAVKA: {
            "label": "Objednávka",
            "description": "Potvrzená objednávka zákazníkem, závazná",
            "color": "#3b82f6",
            "icon": "clipboard-check",
            "phase": "obchod",
        },
        OrderStatus.VYROBA: {
            "label": "Výroba",
            "description": "Zakázka v produkci — řezání, svařování, montáž, NDT",
            "color": "#ef4444",
            "icon": "cog",
            "phase": "výroba",
        },
        OrderStatus.EXPEDICE: {
            "label": "Expedice",
            "description": "Hotový výrobek připraven k odeslání / převzetí",
            "color": "#10b981",
            "icon": "truck",
            "phase": "logistika",
        },
        OrderStatus.FAKTURACE: {
            "label": "Fakturace",
            "description": "Vystavení faktury, synchronizace s Pohoda",
            "color": "#06b6d4",
            "icon": "receipt",
            "phase": "finance",
        },
        OrderStatus.DOKONCENO: {
            "label": "Dokončeno",
            "description": "Zakázka uzavřena, platba přijata, archivováno",
            "color": "#22c55e",
            "icon": "check-circle",
            "phase": "archiv",
        },
    }

    # Build nodes from OrderStatus enum
    order_nodes = []
    for status in OrderStatus:
        meta = status_meta.get(status, {})
        order_nodes.append({
            "id": f"status_{status.value}",
            "label": meta.get("label", status.value),
            "description": meta.get("description", ""),
            "color": meta.get("color", "#6b7280"),
            "icon": meta.get("icon", "circle"),
            "phase": meta.get("phase", ""),
            "category": "order_status",
        })

    # Build edges from actual STATUS_TRANSITIONS
    order_edges = []
    transition_labels = {
        (OrderStatus.POPTAVKA, OrderStatus.NABIDKA): "Vytvoření nabídky",
        (OrderStatus.POPTAVKA, OrderStatus.OBJEDNAVKA): "Přímá objednávka",
        (OrderStatus.NABIDKA, OrderStatus.OBJEDNAVKA): "Zákazník přijal",
        (OrderStatus.NABIDKA, OrderStatus.POPTAVKA): "Vráceno k úpravě",
        (OrderStatus.OBJEDNAVKA, OrderStatus.VYROBA): "Zahájení výroby",
        (OrderStatus.VYROBA, OrderStatus.EXPEDICE): "Výroba dokončena",
        (OrderStatus.EXPEDICE, OrderStatus.FAKTURACE): "Odesláno / převzato",
        (OrderStatus.FAKTURACE, OrderStatus.DOKONCENO): "Platba přijata",
    }

    for from_status, to_statuses in transitions.items():
        for to_status in to_statuses:
            edge_label = transition_labels.get(
                (from_status, to_status),
                f"{from_status.value} → {to_status.value}",
            )
            is_back = (
                list(OrderStatus).index(to_status)
                < list(OrderStatus).index(from_status)
            )
            order_edges.append({
                "source": f"status_{from_status.value}",
                "target": f"status_{to_status.value}",
                "label": edge_label,
                "edge_type": "back" if is_back else "forward",
            })

    # Email ingestion pipeline nodes
    pipeline_nodes = [
        {
            "id": "pipe_email_in",
            "label": "Příchozí email",
            "description": "IMAP polling — nový email v schránce",
            "color": "#64748b",
            "icon": "mail",
            "phase": "vstup",
            "category": "pipeline",
        },
        {
            "id": "pipe_classify",
            "label": "Klasifikace",
            "description": "AI agent — poptávka / reklamace / info / spam",
            "color": "#ef4444",
            "icon": "brain",
            "phase": "vstup",
            "category": "pipeline",
        },
        {
            "id": "pipe_parse",
            "label": "Extrakce dat",
            "description": "AI parser — zákazník, materiál, množství, termín",
            "color": "#ef4444",
            "icon": "scan",
            "phase": "vstup",
            "category": "pipeline",
        },
        {
            "id": "pipe_ocr",
            "label": "OCR příloh",
            "description": "Tesseract — výkresy, certifikáty, objednávky",
            "color": "#10b981",
            "icon": "eye",
            "phase": "vstup",
            "category": "pipeline",
        },
        {
            "id": "pipe_customer",
            "label": "Identifikace zákazníka",
            "description": "Matching s databází zákazníků nebo založení nového",
            "color": "#8b5cf6",
            "icon": "user-check",
            "phase": "vstup",
            "category": "pipeline",
        },
    ]

    # Pipeline edges
    pipeline_edges = [
        {"source": "pipe_email_in", "target": "pipe_classify", "label": "Nový email", "edge_type": "pipeline"},
        {"source": "pipe_classify", "target": "pipe_parse", "label": "Poptávka", "edge_type": "pipeline"},
        {"source": "pipe_email_in", "target": "pipe_ocr", "label": "Přílohy", "edge_type": "pipeline"},
        {"source": "pipe_parse", "target": "pipe_customer", "label": "Data extrahována", "edge_type": "pipeline"},
        {"source": "pipe_customer", "target": "status_poptavka", "label": "Zakázka vytvořena", "edge_type": "pipeline"},
    ]

    # Supporting process nodes
    support_nodes = [
        {
            "id": "sup_kalkulace",
            "label": "Kalkulace",
            "description": "Výpočet nákladů — materiál, práce, kooperace, marže",
            "color": "#f59e0b",
            "icon": "calculator",
            "phase": "obchod",
            "category": "support",
        },
        {
            "id": "sup_dokumenty",
            "label": "Generování PDF",
            "description": "Nabídka, průvodka, dodací list z šablon",
            "color": "#3b82f6",
            "icon": "file-output",
            "phase": "obchod",
            "category": "support",
        },
        {
            "id": "sup_pohoda",
            "label": "Pohoda sync",
            "description": "Export faktury do Pohoda (XML Windows-1250)",
            "color": "#06b6d4",
            "icon": "refresh-cw",
            "phase": "finance",
            "category": "support",
        },
        {
            "id": "sup_operace",
            "label": "Výrobní operace",
            "description": "Řezání, svařování, NDT, povrchová úprava, montáž",
            "color": "#ef4444",
            "icon": "wrench",
            "phase": "výroba",
            "category": "support",
        },
        {
            "id": "sup_kooperace",
            "label": "Kooperace",
            "description": "Subdodávky — žárové zinkování, tryskání, obrábění",
            "color": "#10b981",
            "icon": "handshake",
            "phase": "výroba",
            "category": "support",
        },
    ]

    # Supporting edges
    support_edges = [
        {"source": "status_poptavka", "target": "sup_kalkulace", "label": "Ocenění", "edge_type": "support"},
        {"source": "sup_kalkulace", "target": "status_nabidka", "label": "Nabídka hotova", "edge_type": "support"},
        {"source": "status_nabidka", "target": "sup_dokumenty", "label": "PDF nabídka", "edge_type": "support"},
        {"source": "status_vyroba", "target": "sup_operace", "label": "Výrobní plán", "edge_type": "support"},
        {"source": "status_vyroba", "target": "sup_kooperace", "label": "Subdodávka", "edge_type": "support"},
        {"source": "sup_operace", "target": "status_expedice", "label": "Vše dokončeno", "edge_type": "support"},
        {"source": "status_fakturace", "target": "sup_pohoda", "label": "Export XML", "edge_type": "support"},
    ]

    # Combine all
    all_nodes = pipeline_nodes + order_nodes + support_nodes
    all_edges = pipeline_edges + order_edges + support_edges

    # Phase labels for grouping
    phase_labels = {
        "vstup": "Příjem zakázky",
        "obchod": "Obchodní proces",
        "výroba": "Výroba",
        "logistika": "Logistika",
        "finance": "Finance",
        "archiv": "Archiv",
    }

    category_labels = {
        "pipeline": "Email pipeline",
        "order_status": "Stav zakázky",
        "support": "Podpůrné procesy",
    }

    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "phase_labels": phase_labels,
        "category_labels": category_labels,
    }
