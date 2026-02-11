#!/usr/bin/env python3
"""
inferbox — Dynamic Codebase Analyzer
Analyzes backend + frontend and generates a JSON graph for interactive visualization.
Re-run to get fresh state from the actual codebase.
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Node:
    id: str
    label: str
    category: str
    description: str = ""
    detail: str = ""
    parent: Optional[str] = None
    file_path: str = ""
    line_count: int = 0
    function_count: int = 0
    class_count: int = 0
    endpoints: list = field(default_factory=list)
    methods: list = field(default_factory=list)


@dataclass
class Edge:
    source: str
    target: str
    label: str = ""
    edge_type: str = "dependency"  # dependency, api_call, data_flow, triggers


# ── Paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend" / "app"
FRONTEND = ROOT / "frontend" / "src"
OUTPUT = Path(__file__).resolve().parent / "graph_data.json"


# ── AST Helpers ──────────────────────────────────────────────────────────────

def count_lines(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except Exception:
        return 0


def parse_python_file(path: Path) -> Optional[ast.Module]:
    try:
        source = path.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(path))
    except Exception:
        return None


def get_docstring(node) -> str:
    """Extract docstring from AST node."""
    ds = ast.get_docstring(node)
    return ds.strip().split("\n")[0] if ds else ""


def get_functions(tree: ast.Module) -> list[dict]:
    """Extract all function/method definitions."""
    funcs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") and node.name != "__init__":
                continue
            funcs.append({
                "name": node.name,
                "doc": get_docstring(node),
                "line": node.lineno,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            })
    return funcs


def get_classes(tree: ast.Module) -> list[dict]:
    """Extract class definitions."""
    classes = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            classes.append({
                "name": node.name,
                "doc": get_docstring(node),
                "line": node.lineno,
            })
    return classes


def get_imports(tree: ast.Module) -> list[str]:
    """Extract app-internal imports."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("app."):
                imports.append(node.module)
    return list(set(imports))


# ── FastAPI Endpoint Extraction ──────────────────────────────────────────────

FASTAPI_METHODS = {"get", "post", "put", "patch", "delete"}


def extract_endpoints(tree: ast.Module) -> list[dict]:
    """Extract FastAPI router endpoints from decorators."""
    endpoints = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            call = None
            if isinstance(decorator, ast.Call):
                call = decorator
            elif isinstance(decorator, ast.Attribute):
                continue

            if call is None:
                continue

            func = call.func
            method_name = None
            if isinstance(func, ast.Attribute) and func.attr in FASTAPI_METHODS:
                method_name = func.attr.upper()
            elif isinstance(func, ast.Name) and func.id in FASTAPI_METHODS:
                method_name = func.id.upper()

            if method_name and call.args:
                path_arg = call.args[0]
                if isinstance(path_arg, ast.Constant) and isinstance(path_arg.value, str):
                    endpoints.append({
                        "method": method_name,
                        "path": path_arg.value,
                        "handler": node.name,
                        "doc": get_docstring(node),
                        "line": node.lineno,
                    })
    return endpoints


# ── Celery Task Extraction ───────────────────────────────────────────────────

def extract_celery_tasks(tree: ast.Module) -> list[dict]:
    """Extract Celery task definitions."""
    tasks = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            is_task = False
            if isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute) and func.attr == "task":
                    is_task = True
                elif isinstance(func, ast.Name) and func.id == "task":
                    is_task = True
            elif isinstance(decorator, ast.Attribute) and decorator.attr == "task":
                is_task = True
            elif isinstance(decorator, ast.Name) and decorator.id == "task":
                is_task = True

            if is_task:
                tasks.append({
                    "name": node.name,
                    "doc": get_docstring(node),
                    "line": node.lineno,
                })
    return tasks


# ── SQLAlchemy Model Extraction ──────────────────────────────────────────────

def extract_model_fields(tree: ast.Module) -> list[dict]:
    """Extract SQLAlchemy model classes with their columns."""
    models = []
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        # Check if it inherits from Base or has __tablename__
        has_tablename = False
        tablename = ""
        columns = []
        relationships = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        has_tablename = True
                        if isinstance(item.value, ast.Constant):
                            tablename = item.value.value
            if isinstance(item, ast.AnnAssign) and item.target:
                if isinstance(item.target, ast.Name):
                    col_name = item.target.id
                    if not col_name.startswith("_"):
                        # Check if it's a relationship
                        if item.annotation and isinstance(item.annotation, ast.Subscript):
                            if isinstance(item.annotation.value, ast.Name):
                                if item.annotation.value.id == "Mapped":
                                    columns.append(col_name)
                        elif item.value and isinstance(item.value, ast.Call):
                            func = item.value.func
                            if isinstance(func, ast.Name) and func.id == "relationship":
                                relationships.append(col_name)
                            else:
                                columns.append(col_name)
                        else:
                            columns.append(col_name)

        if has_tablename:
            models.append({
                "name": node.name,
                "tablename": tablename,
                "doc": get_docstring(node),
                "columns": columns[:15],  # Limit for display
                "relationships": relationships,
                "line": node.lineno,
            })
    return models


# ── Frontend Analysis ────────────────────────────────────────────────────────

def analyze_tsx_file(path: Path) -> dict:
    """Analyze a TypeScript/TSX file for components and API calls."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return {}

    # Extract component name
    component_match = re.search(r"(?:export\s+default\s+function|function)\s+(\w+)", content)
    component_name = component_match.group(1) if component_match else path.stem

    # Extract API calls
    api_calls = re.findall(r"api\.(get|post|put|patch|delete)\s*[<(]\s*['\"]([^'\"]+)['\"]", content)
    fetch_calls = re.findall(r"fetch\s*\(\s*[`'\"]([^`'\"]+)[`'\"]", content)

    # Extract imports from components
    component_imports = re.findall(r"from\s+['\"]@/components/([^'\"]+)['\"]", content)

    # Extract useQuery/useMutation hooks
    queries = re.findall(r"useQuery\s*[<(].*?queryKey:\s*\[([^\]]+)\]", content, re.DOTALL)

    # Page title or heading
    title_match = re.search(r"<h[12][^>]*>([^<]+)</h[12]>", content)
    title = title_match.group(1) if title_match else ""

    return {
        "component": component_name,
        "api_calls": [{"method": m.upper(), "path": p} for m, p in api_calls],
        "fetch_calls": fetch_calls,
        "component_imports": component_imports,
        "queries": queries,
        "title": title,
        "lines": len(content.splitlines()),
    }


def find_frontend_routes(frontend_dir: Path) -> list[dict]:
    """Find all Next.js routes."""
    routes = []
    app_dir = frontend_dir / "app"
    if not app_dir.exists():
        return routes

    for page_file in app_dir.rglob("page.tsx"):
        rel = page_file.relative_to(app_dir)
        parts = list(rel.parts[:-1])  # Remove page.tsx
        # Convert (dashboard) group to empty
        route_parts = []
        for p in parts:
            if p.startswith("(") and p.endswith(")"):
                continue
            route_parts.append(p)
        route = "/" + "/".join(route_parts) if route_parts else "/"

        analysis = analyze_tsx_file(page_file)
        routes.append({
            "route": route,
            "file": str(page_file.relative_to(ROOT)),
            **analysis,
        })
    return routes


# ── Main Analysis ────────────────────────────────────────────────────────────

# Czech descriptions for categories and modules
CATEGORY_DESCRIPTIONS = {
    "api": "REST API endpointy",
    "service": "Business logika a služby",
    "model": "Databázové modely (SQLAlchemy)",
    "agent": "AI agenti (Anthropic Claude)",
    "integration": "Externí integrace",
    "core": "Jádro aplikace",
    "frontend": "Frontendové stránky (Next.js)",
    "celery": "Asynchronní úlohy (Celery)",
    "orchestration": "Orchestrace dokumentů",
}

MODULE_DESCRIPTIONS = {
    # API
    "auth": "Autentizace — přihlášení, JWT tokeny, správa uživatelů, změna hesla",
    "customers": "Správa zákazníků — CRUD operace, kategorie, slevy",
    "orders": "Správa zakázek — vytvoření, stavy, workflow, konverze z nabídky",
    "calculations": "Kalkulace zakázek — náklady, materiál, práce, marže",
    "documents": "Dokumenty — nahrávání, generování PDF, verzování",
    "inbox": "E-mailová schránka — příjem, klasifikace, přiřazení k zakázkám",
    "pohoda": "Pohoda XML sync — export/import zákazníků, objednávek, faktur",
    "reporting": "Reporting — statistiky, grafy, trendy, export",
    "gamification": "Gamifikace — body za aktivitu, žebříček, odznaky",
    "similar_orders": "Podobné zakázky — vyhledávání pomocí RAG embeddings",
    "document_generator": "Generátor dokumentů — PDF nabídky, průvodky (Jinja2 + WeasyPrint)",
    "notifications": "Notifikace — WebSocket real-time, zvonečkové upozornění",
    "orchestration": "Orchestrace — automatický pipeline zpracování e-mailů a dokumentů",
    "materials": "Materiálová databáze — ceny, dodavatelé, Excel import",
    "ai_dashboard": "AI Dashboard — využití tokenů, statistiky agentů",
    "ai_usage": "AI využití — statistiky tokenů, náklady, history dotazů",
    "automation": "Automatizace — orchestrační pipeline, feature flags, konfigurace",
    "task_marketplace": "Tržiště úkolů — nabídky zakázek, claim/release, gamifikace bodů",
    "knowledge_base": "Znalostní báze — články, FAQ, postupy, full-text vyhledávání",
    "proactive_ai": "Proaktivní AI — doporučení, anomálie, automatické akce",
    "monitoring": "Monitoring — metriky systému, AI agentů, performance",
    # Services
    "customer_service": "Správa zákaznických dat, kategorizace A/B/C, slevy",
    "order_service": "Workflow zakázek, stavový automat, audit trail",
    "calculation_service": "Výpočet kalkulací, BOM, marže, schvalování",
    "document_service": "Ukládání a verzování dokumentů",
    "inbox_service": "Zpracování příchozích e-mailů, auto-přiřazení",
    "pohoda_service": "Synchronizace s účetním systémem Pohoda",
    "reporting_service": "Agregace dat pro reporty a dashboardy",
    "gamification_service": "Výpočet bodů, žebříček, herní mechaniky",
    # Agents
    "email_classifier": "Klasifikace e-mailů do kategorií (poptávka, reklamace, info...)",
    "email_parser": "Extrakce strukturovaných dat z e-mailů pomocí AI",
    "calculation_agent": "AI kalkulace zakázek — analýza materiálu, práce, ceny",
    "heuristic_classifier": "Rychlá klasifikace e-mailů bez AI (regex + pravidla)",
    "document_type_detector": "Detekce typu dokumentu (výkres, certifikát, objednávka...)",
    "attachment_processor": "Zpracování příloh e-mailů (OCR, parsování)",
    "order_orchestrator": "Orchestrace vytvoření zakázky z poptávkového e-mailu",
    "offer_generator": "Automatické generování nabídek z kalkulací",
    # Integrations
    "pohoda_xml": "Pohoda XML API — Windows-1250, dataPack, XSD validace",
    "email_tasks": "IMAP polling, SMTP auto-reply, Celery úlohy",
    "ocr_processor": "OCR zpracování dokumentů (Tesseract)",
    "excel_parser": "Import dat z Excelu (openpyxl)",
    "excel_exporter": "Export dat do Excelu",
    # Core
    "config": "Konfigurace aplikace (Pydantic Settings, env proměnné)",
    "database": "Databázové připojení (async SQLAlchemy, PostgreSQL)",
    "security": "Autentizace a autorizace (JWT, bcrypt, RBAC)",
    "celery_app": "Celery konfigurace (Redis broker, 4 fronty)",
    "health": "Healthcheck endpointy (/health, /ready)",
    "metrics": "Prometheus metriky (požadavky, latence, DB pool)",
    "logging_config": "Strukturované logování",
    # Frontend pages
    "/dashboard": "Hlavní přehled — statistiky zakázek, grafy, rychlé akce",
    "/zakazky": "Seznam zakázek — filtrování, řazení, hromadné operace",
    "/zakazky/[id]": "Detail zakázky — workflow, dokumenty, kalkulace, historie",
    "/kalkulace": "Seznam kalkulací — přehled nákladů, stavy schválení",
    "/kalkulace/[id]": "Detail kalkulace — položky BOM, náklady, marže",
    "/dokumenty": "Správa dokumentů — nahrávání, vyhledávání, generování PDF",
    "/reporting": "Reporty a analýzy — grafy trendů, exporty",
    "/inbox": "E-mailová schránka — příchozí zprávy, klasifikace, odpovědi",
    "/pohoda": "Pohoda synchronizace — stav sync, manuální akce",
    "/nastaveni": "Nastavení aplikace — uživatel, systém, integrace",
    "/kanban": "Kanban board — drag & drop správa zakázek ve sloupcích",
    "/zebricek": "Žebříček — gamifikace, body, odznaky, periody",
    "/automatizace": "Automatizace — orchestrační pipeline, DLQ, statistiky",
    "/podobne-zakazky": "Podobné zakázky — RAG vyhledávání pomocí embeddings",
    "/generator-dokumentu": "Generátor PDF — nabídky, průvodky z šablon",
    "/ai-dashboard": "AI Dashboard — statistiky využití AI agentů a tokenů",
    "/knowledge-base": "Znalostní báze — dokumentace, postupy, FAQ",
    "/task-marketplace": "Tržiště úkolů — přebírání zakázek, gamifikace",
}


def analyze_backend(nodes: list[Node], edges: list[Edge]):
    """Analyze entire backend."""
    if not BACKEND.exists():
        return

    # ── API Endpoints ──
    api_dir = BACKEND / "api" / "v1"
    if api_dir.exists():
        for py_file in sorted(api_dir.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            tree = parse_python_file(py_file)
            if not tree:
                continue

            module_name = py_file.stem
            node_id = f"api_{module_name}"
            endpoints = extract_endpoints(tree)
            funcs = get_functions(tree)
            imports = get_imports(tree)
            desc = MODULE_DESCRIPTIONS.get(module_name, get_docstring(tree))

            node = Node(
                id=node_id,
                label=f"API: {module_name}",
                category="api",
                description=desc,
                detail=f"Endpointy: {len(endpoints)}, Funkce: {len(funcs)}",
                file_path=str(py_file.relative_to(ROOT)),
                line_count=count_lines(py_file),
                function_count=len(funcs),
                endpoints=[f"{e['method']} {e['path']}" for e in endpoints],
                methods=[f.get("name", "") for f in funcs],
            )
            nodes.append(node)

            # Edges from API to services
            for imp in imports:
                if "services" in imp:
                    svc_name = imp.split(".")[-1]
                    edges.append(Edge(
                        source=node_id,
                        target=f"svc_{svc_name}",
                        label="volá",
                        edge_type="dependency",
                    ))
                elif "models" in imp:
                    model_name = imp.split(".")[-1]
                    edges.append(Edge(
                        source=node_id,
                        target=f"model_{model_name}",
                        label="používá",
                        edge_type="data_flow",
                    ))

    # ── Services ──
    svc_dir = BACKEND / "services"
    if svc_dir.exists():
        for py_file in sorted(svc_dir.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            tree = parse_python_file(py_file)
            if not tree:
                continue

            module_name = py_file.stem
            node_id = f"svc_{module_name}"
            funcs = get_functions(tree)
            classes = get_classes(tree)
            imports = get_imports(tree)
            desc_key = f"{module_name}_service" if not module_name.endswith("_service") else module_name
            desc = MODULE_DESCRIPTIONS.get(desc_key, MODULE_DESCRIPTIONS.get(module_name, get_docstring(tree)))

            node = Node(
                id=node_id,
                label=f"Service: {module_name}",
                category="service",
                description=desc,
                detail=f"Třídy: {len(classes)}, Metody: {len(funcs)}",
                file_path=str(py_file.relative_to(ROOT)),
                line_count=count_lines(py_file),
                function_count=len(funcs),
                class_count=len(classes),
                methods=[f.get("name", "") for f in funcs[:20]],
            )
            nodes.append(node)

            for imp in imports:
                if "models" in imp:
                    model_name = imp.split(".")[-1]
                    edges.append(Edge(
                        source=node_id,
                        target=f"model_{model_name}",
                        label="čte/zapisuje",
                        edge_type="data_flow",
                    ))
                elif "integrations" in imp:
                    int_name = imp.replace("app.integrations.", "").split(".")[0]
                    edges.append(Edge(
                        source=node_id,
                        target=f"int_{int_name}",
                        label="volá",
                        edge_type="dependency",
                    ))

    # ── Models ──
    model_dir = BACKEND / "models"
    if model_dir.exists():
        for py_file in sorted(model_dir.glob("*.py")):
            if py_file.name in ("__init__.py", "base.py"):
                continue
            tree = parse_python_file(py_file)
            if not tree:
                continue

            module_name = py_file.stem
            node_id = f"model_{module_name}"
            models = extract_model_fields(tree)
            desc = MODULE_DESCRIPTIONS.get(module_name, get_docstring(tree))

            model_details = []
            for m in models:
                cols = ", ".join(m["columns"][:8])
                rels = ", ".join(m["relationships"][:5])
                detail_parts = [f"tabulka: {m['tablename']}"]
                if cols:
                    detail_parts.append(f"sloupce: {cols}")
                if rels:
                    detail_parts.append(f"relace: {rels}")
                model_details.append(f"{m['name']} ({'; '.join(detail_parts)})")

            node = Node(
                id=node_id,
                label=f"Model: {module_name}",
                category="model",
                description=desc or f"Databázový model {module_name}",
                detail=f"Modely: {', '.join(m['name'] for m in models)}" if models else "",
                file_path=str(py_file.relative_to(ROOT)),
                line_count=count_lines(py_file),
                class_count=len(models),
                methods=[d for d in model_details],
            )
            nodes.append(node)

            # Model relationships via imports
            imports = get_imports(tree)
            for imp in imports:
                if "models" in imp:
                    related = imp.split(".")[-1]
                    if related != module_name and related != "base":
                        edges.append(Edge(
                            source=node_id,
                            target=f"model_{related}",
                            label="FK/relace",
                            edge_type="data_flow",
                        ))

    # ── Agents ──
    agent_dir = BACKEND / "agents"
    if agent_dir.exists():
        for py_file in sorted(agent_dir.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            tree = parse_python_file(py_file)
            if not tree:
                continue

            module_name = py_file.stem
            node_id = f"agent_{module_name}"
            funcs = get_functions(tree)
            classes = get_classes(tree)
            celery_tasks = extract_celery_tasks(tree)
            imports = get_imports(tree)
            desc = MODULE_DESCRIPTIONS.get(module_name, get_docstring(tree))

            node = Node(
                id=node_id,
                label=f"Agent: {module_name}",
                category="agent",
                description=desc,
                detail=f"Třídy: {len(classes)}, Funkce: {len(funcs)}, Celery tasks: {len(celery_tasks)}",
                file_path=str(py_file.relative_to(ROOT)),
                line_count=count_lines(py_file),
                function_count=len(funcs),
                class_count=len(classes),
                methods=[f.get("name", "") for f in funcs[:15]],
            )
            nodes.append(node)

            for imp in imports:
                if "services" in imp:
                    svc_name = imp.split(".")[-1]
                    edges.append(Edge(
                        source=node_id,
                        target=f"svc_{svc_name}",
                        label="volá",
                        edge_type="dependency",
                    ))
                elif "models" in imp:
                    model_name = imp.split(".")[-1]
                    edges.append(Edge(
                        source=node_id,
                        target=f"model_{model_name}",
                        label="čte/zapisuje",
                        edge_type="data_flow",
                    ))

    # ── Integrations ──
    int_dir = BACKEND / "integrations"
    if int_dir.exists():
        for sub_dir in sorted(int_dir.iterdir()):
            if not sub_dir.is_dir() or sub_dir.name == "__pycache__":
                continue

            int_name = sub_dir.name
            node_id = f"int_{int_name}"
            total_lines = 0
            total_funcs = 0
            total_classes = 0
            all_methods = []
            all_tasks = []

            for py_file in sorted(sub_dir.glob("*.py")):
                if py_file.name == "__init__.py":
                    continue
                tree = parse_python_file(py_file)
                if not tree:
                    continue
                total_lines += count_lines(py_file)
                funcs = get_functions(tree)
                total_funcs += len(funcs)
                total_classes += len(get_classes(tree))
                all_methods.extend(f.get("name", "") for f in funcs)
                all_tasks.extend(extract_celery_tasks(tree))

            desc_keys = [
                f"{int_name}_xml",
                f"{int_name}_tasks",
                f"{int_name}_processor",
                f"{int_name}_parser",
                int_name,
            ]
            desc = ""
            for dk in desc_keys:
                if dk in MODULE_DESCRIPTIONS:
                    desc = MODULE_DESCRIPTIONS[dk]
                    break
            if not desc:
                desc = f"Integrace: {int_name}"

            node = Node(
                id=node_id,
                label=f"Integrace: {int_name}",
                category="integration",
                description=desc,
                detail=f"Soubory: {len(list(sub_dir.glob('*.py')))}, Funkce: {total_funcs}, Celery tasks: {len(all_tasks)}",
                file_path=str(sub_dir.relative_to(ROOT)),
                line_count=total_lines,
                function_count=total_funcs,
                class_count=total_classes,
                methods=all_methods[:20],
            )
            nodes.append(node)

    # ── Core ──
    core_dir = BACKEND / "core"
    if core_dir.exists():
        for py_file in sorted(core_dir.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            tree = parse_python_file(py_file)
            if not tree:
                continue

            module_name = py_file.stem
            node_id = f"core_{module_name}"
            funcs = get_functions(tree)
            classes = get_classes(tree)
            desc = MODULE_DESCRIPTIONS.get(module_name, MODULE_DESCRIPTIONS.get(f"logging_config" if module_name == "logging" else module_name, get_docstring(tree)))

            node = Node(
                id=node_id,
                label=f"Core: {module_name}",
                category="core",
                description=desc or f"Core modul: {module_name}",
                detail=f"Třídy: {len(classes)}, Funkce: {len(funcs)}",
                file_path=str(py_file.relative_to(ROOT)),
                line_count=count_lines(py_file),
                function_count=len(funcs),
                class_count=len(classes),
                methods=[f.get("name", "") for f in funcs[:10]],
            )
            nodes.append(node)

    # ── Orchestration (special agents) ──
    orch_dir = BACKEND / "agents"
    orchestration_agents = [
        "email_ingestion", "heuristic_classifier", "document_type_detector",
        "attachment_processor", "order_orchestrator", "offer_generator",
    ]
    existing_agent_ids = {n.id for n in nodes if n.category == "agent"}

    # Add orchestration pipeline edges
    pipeline_order = [
        ("agent_email_ingestion", "agent_heuristic_classifier", "klasifikuje"),
        ("agent_heuristic_classifier", "agent_document_type_detector", "routuje"),
        ("agent_document_type_detector", "agent_attachment_processor", "zpracuje přílohy"),
        ("agent_attachment_processor", "agent_order_orchestrator", "vytvoří zakázku"),
        ("agent_order_orchestrator", "agent_calculation_agent", "spočítá kalkulaci"),
        ("agent_calculation_agent", "agent_offer_generator", "vygeneruje nabídku"),
    ]
    for src, tgt, label in pipeline_order:
        if src.replace("agent_", "") in [n.id.replace("agent_", "") for n in nodes if n.category == "agent"]:
            edges.append(Edge(source=src, target=tgt, label=label, edge_type="triggers"))


def analyze_frontend(nodes: list[Node], edges: list[Edge]):
    """Analyze frontend routes and components."""
    if not FRONTEND.exists():
        return

    routes = find_frontend_routes(FRONTEND)
    for route_info in routes:
        route = route_info["route"]
        node_id = f"page_{route.replace('/', '_').replace('[', '').replace(']', '').strip('_') or 'home'}"
        desc = MODULE_DESCRIPTIONS.get(route, route_info.get("title", ""))

        node = Node(
            id=node_id,
            label=f"Stránka: {route}",
            category="frontend",
            description=desc,
            detail=f"Komponenta: {route_info.get('component', '')}, Řádky: {route_info.get('lines', 0)}",
            file_path=route_info.get("file", ""),
            line_count=route_info.get("lines", 0),
            methods=[f"{c['method']} {c['path']}" for c in route_info.get("api_calls", [])],
        )
        nodes.append(node)

        # Connect pages to their API endpoints (explicit API calls)
        for api_call in route_info.get("api_calls", []):
            path = api_call["path"]
            for existing_node in nodes:
                if existing_node.category == "api":
                    for ep in existing_node.endpoints:
                        if path in ep:
                            edges.append(Edge(
                                source=node_id,
                                target=existing_node.id,
                                label=api_call["method"],
                                edge_type="api_call",
                            ))
                            break

        # Connect pages to API by route name heuristic
        route_to_api = {
            "/zakazky": "api_orders",
            "/zakazky/[id]": "api_orders",
            "/kalkulace": "api_calculations",
            "/kalkulace/[id]": "api_calculations",
            "/dokumenty": "api_documents",
            "/reporting": "api_reporting",
            "/inbox": "api_inbox",
            "/pohoda": "api_pohoda",
            "/kanban": "api_orders",
            "/zebricek": "api_gamification",
            "/automatizace": "api_orchestration",
            "/dashboard": "api_reporting",
            "/ai-dashboard": "api_ai_usage",
            "/task-marketplace": "api_task_marketplace",
            "/knowledge-base": "api_knowledge_base",
        }
        api_target = route_to_api.get(route)
        if api_target:
            # Check if node exists
            if any(n.id == api_target for n in nodes):
                edges.append(Edge(
                    source=node_id,
                    target=api_target,
                    label="fetch",
                    edge_type="api_call",
                ))


def add_summary_stats(data: dict, nodes: list[Node]):
    """Add summary statistics to the output."""
    categories = {}
    for node in nodes:
        cat = node.category
        if cat not in categories:
            categories[cat] = {"count": 0, "total_lines": 0, "total_functions": 0}
        categories[cat]["count"] += 1
        categories[cat]["total_lines"] += node.line_count
        categories[cat]["total_functions"] += node.function_count

    data["stats"] = {
        "total_nodes": len(nodes),
        "total_edges": len(data["edges"]),
        "categories": categories,
        "total_lines": sum(n.line_count for n in nodes),
        "total_functions": sum(n.function_count for n in nodes),
        "total_classes": sum(n.class_count for n in nodes),
    }


def main():
    nodes: list[Node] = []
    edges: list[Edge] = []

    print("Analyzing backend...")
    analyze_backend(nodes, edges)

    print("Analyzing frontend...")
    analyze_frontend(nodes, edges)

    # Deduplicate edges
    seen_edges = set()
    unique_edges = []
    for e in edges:
        key = (e.source, e.target, e.edge_type)
        # Only add edge if both nodes exist
        node_ids = {n.id for n in nodes}
        if key not in seen_edges and e.source in node_ids and e.target in node_ids:
            seen_edges.add(key)
            unique_edges.append(e)

    data = {
        "nodes": [asdict(n) for n in nodes],
        "edges": [asdict(e) for e in unique_edges],
        "category_labels": {
            "api": "REST API",
            "service": "Služby",
            "model": "Modely",
            "agent": "AI Agenti",
            "integration": "Integrace",
            "core": "Jádro",
            "frontend": "Frontend",
            "celery": "Celery Tasks",
            "orchestration": "Orchestrace",
        },
        "category_descriptions": CATEGORY_DESCRIPTIONS,
    }
    add_summary_stats(data, nodes)

    OUTPUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {OUTPUT} with {len(nodes)} nodes and {len(unique_edges)} edges")
    print(f"Stats: {data['stats']}")


if __name__ == "__main__":
    main()
