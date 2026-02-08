"""Architecture graph API — returns codebase analysis as JSON for interactive visualization."""

import json
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/architektura", tags=["architektura"])

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # infer-forge/
ANALYZER = ROOT / "prezentace" / "analyze_codebase.py"
GRAPH_JSON = ROOT / "prezentace" / "graph_data.json"


@router.get("")
async def get_architecture_graph(refresh: bool = False):
    """Return architecture graph data. Use ?refresh=true to re-analyze codebase."""
    if refresh or not GRAPH_JSON.exists():
        result = subprocess.run(
            [sys.executable, str(ANALYZER)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ROOT),
        )
        if result.returncode != 0:
            return {"error": f"Analyzer failed: {result.stderr}"}

    if not GRAPH_JSON.exists():
        return {"error": "graph_data.json not found. Run analyze_codebase.py first."}

    data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    return data
