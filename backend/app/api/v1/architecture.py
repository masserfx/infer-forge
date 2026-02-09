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
