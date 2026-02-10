"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  RefreshCw,
  Maximize,
  Download,
  Search,
  Loader2,
  Network,
  GitBranch,
} from "lucide-react";
import type cytoscape from "cytoscape";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ── Types ────────────────────────────────────────────────────────────────────

interface GraphNode {
  id: string;
  label: string;
  category: string;
  description: string;
  detail: string;
  file_path: string;
  line_count: number;
  function_count: number;
  class_count: number;
  endpoints: string[];
  methods: string[];
}

interface GraphEdge {
  source: string;
  target: string;
  label: string;
  edge_type: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  category_labels: Record<string, string>;
  stats: {
    total_nodes: number;
    total_edges: number;
    total_lines: number;
    total_functions: number;
    total_classes: number;
    categories: Record<string, { count: number; total_lines: number; total_functions: number }>;
  };
}

interface WorkflowNode {
  id: string;
  label: string;
  description: string;
  color: string;
  icon: string;
  phase: string;
  category: string;
}

interface WorkflowEdge {
  source: string;
  target: string;
  label: string;
  edge_type: string;
}

interface WorkflowData {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  phase_labels: Record<string, string>;
  category_labels: Record<string, string>;
}

type TabId = "architecture" | "workflow";

// ── Architecture constants ───────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  api:         { bg: "#f59e0b", border: "#d97706", text: "#000" },
  service:     { bg: "#3b82f6", border: "#2563eb", text: "#fff" },
  model:       { bg: "#8b5cf6", border: "#7c3aed", text: "#fff" },
  agent:       { bg: "#ef4444", border: "#dc2626", text: "#fff" },
  integration: { bg: "#10b981", border: "#059669", text: "#fff" },
  core:        { bg: "#6b7280", border: "#4b5563", text: "#fff" },
  frontend:    { bg: "#06b6d4", border: "#0891b2", text: "#000" },
};

const CATEGORY_SHAPES: Record<string, string> = {
  api: "round-rectangle",
  service: "ellipse",
  model: "diamond",
  agent: "star",
  integration: "hexagon",
  core: "octagon",
  frontend: "round-rectangle",
};

const EDGE_COLORS: Record<string, string> = {
  dependency: "#64748b",
  api_call:   "#3b82f6",
  data_flow:  "#8b5cf6",
  triggers:   "#ef4444",
};

const LAYOUTS = [
  { id: "cose-bilkent", label: "Organické" },
  { id: "circle", label: "Kruhové" },
  { id: "concentric", label: "Soustředné" },
  { id: "breadthfirst", label: "Hierarchické" },
  { id: "grid", label: "Mřížka" },
];

// ── Workflow constants ───────────────────────────────────────────────────────

const WORKFLOW_CATEGORY_COLORS: Record<string, { bg: string; border: string }> = {
  pipeline:     { bg: "#64748b", border: "#475569" },
  order_status: { bg: "#3b82f6", border: "#2563eb" },
  support:      { bg: "#10b981", border: "#059669" },
};

const WORKFLOW_EDGE_COLORS: Record<string, string> = {
  forward:  "#3b82f6",
  back:     "#f59e0b",
  pipeline: "#64748b",
  support:  "#10b981",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function loadCytoscape() {
  const cytoscapeModule = await import("cytoscape");
  const cy = cytoscapeModule.default;
  try {
    const coseBilkent = await import("cytoscape-cose-bilkent");
    cy.use(coseBilkent.default || coseBilkent);
  } catch {
    // plugin not available
  }
  return cy;
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function DiagramPage() {
  const [activeTab, setActiveTab] = useState<TabId>("architecture");
  const [loading, setLoading] = useState(true);

  // Architecture state
  const archCyRef = useRef<HTMLDivElement>(null);
  const archCyInstanceRef = useRef<unknown>(null);
  const [archData, setArchData] = useState<GraphData | null>(null);
  const [archRefreshing, setArchRefreshing] = useState(false);
  const [activeCategories, setActiveCategories] = useState<Set<string>>(new Set());
  const [currentLayout, setCurrentLayout] = useState("cose-bilkent");
  const [archSearch, setArchSearch] = useState("");
  const [archTooltip, setArchTooltip] = useState<{ node: GraphNode; x: number; y: number } | null>(null);

  // Workflow state
  const wfCyRef = useRef<HTMLDivElement>(null);
  const wfCyInstanceRef = useRef<unknown>(null);
  const [wfData, setWfData] = useState<WorkflowData | null>(null);
  const [wfLoading, setWfLoading] = useState(false);
  const [wfTooltip, setWfTooltip] = useState<{ node: WorkflowNode; x: number; y: number } | null>(null);

  // ── Architecture data loading ──────────────────────────────────────────────

  const loadArchData = useCallback(async (refresh = false) => {
    try {
      const url = `${API_BASE}/architektura${refresh ? "?refresh=true" : ""}`;
      const resp = await fetch(url, { headers: getAuthHeaders() });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      if (json.error) throw new Error(json.error);
      setArchData(json);

      const cats = new Set<string>();
      for (const node of json.nodes) cats.add(node.category);
      setActiveCategories(cats);
      return json;
    } catch {
      return null;
    }
  }, []);

  // ── Architecture graph init ────────────────────────────────────────────────

  const initArchGraph = useCallback(async (graphData: GraphData, layout: string, categories: Set<string>) => {
    if (!archCyRef.current) return;

    const cytoscape = await loadCytoscape();

    if (archCyInstanceRef.current) {
      (archCyInstanceRef.current as { destroy: () => void }).destroy();
    }

    const elements: cytoscape.ElementDefinition[] = [];
    for (const node of graphData.nodes) {
      if (!categories.has(node.category)) continue;
      const colors = CATEGORY_COLORS[node.category] || CATEGORY_COLORS.core;
      const shape = CATEGORY_SHAPES[node.category] || "ellipse";
      const size = Math.max(25, Math.min(65, 25 + Math.sqrt(node.line_count + node.function_count * 10) * 2));

      elements.push({
        group: "nodes",
        data: {
          id: node.id,
          label: node.label.replace(/^(API|Service|Model|Agent|Integrace|Core|Stránka): ?/, ""),
          fullLabel: node.label,
          category: node.category,
          description: node.description,
          detail: node.detail,
          file_path: node.file_path,
          line_count: node.line_count,
          function_count: node.function_count,
          endpoints: node.endpoints || [],
          methods: node.methods || [],
          bgColor: colors.bg,
          borderColor: colors.border,
          shape,
          size,
        },
      });
    }

    const nodeIds = new Set(elements.filter((e) => e.group === "nodes").map((e) => e.data.id));
    for (const edge of graphData.edges) {
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) continue;
      elements.push({
        group: "edges",
        data: {
          source: edge.source,
          target: edge.target,
          label: edge.label,
          edgeType: edge.edge_type,
          lineColor: EDGE_COLORS[edge.edge_type] || "#64748b",
        },
      });
    }

    const layoutConfigs: Record<string, cytoscape.LayoutOptions & Record<string, unknown>> = {
      "cose-bilkent": {
        name: "cose-bilkent",
        animate: "end",
        animationDuration: 600,
        nodeRepulsion: 8000,
        idealEdgeLength: 120,
        edgeElasticity: 0.45,
        gravity: 0.2,
        numIter: 2500,
        tile: true,
        tilingPaddingVertical: 20,
        tilingPaddingHorizontal: 20,
      },
      circle: { name: "circle", animate: true, animationDuration: 500, padding: 50 },
      concentric: {
        name: "concentric",
        animate: true,
        animationDuration: 500,
        concentric: (node: cytoscape.NodeSingular) => {
          const p: Record<string, number> = { core: 5, model: 4, service: 3, api: 2, agent: 2, integration: 1, frontend: 0 };
          return p[node.data("category")] || 0;
        },
        levelWidth: () => 2,
        padding: 50,
      },
      breadthfirst: { name: "breadthfirst", animate: true, animationDuration: 500, directed: true, padding: 40, spacingFactor: 1.2 },
      grid: { name: "grid", animate: true, animationDuration: 500, padding: 30 },
    };

    const layoutConfig = layoutConfigs[layout] || layoutConfigs["circle"];

    const cy = cytoscape({
      container: archCyRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            width: "data(size)",
            height: "data(size)",
            "background-color": "data(bgColor)",
            "background-opacity": 0.85,
            "border-width": 2.5,
            "border-color": "data(borderColor)",
            label: "data(label)",
            "text-valign": "bottom",
            "text-halign": "center",
            "font-size": 11,
            "font-weight": "bold",
            color: "#cbd5e1",
            "text-margin-y": 8,
            "text-outline-color": "#0a0e17",
            "text-outline-width": 2,
            shape: "data(shape)",
            "text-wrap": "ellipsis",
            "text-max-width": "110px",
            opacity: 1,
            "transition-property": "opacity, width, height, border-width, border-color",
            "transition-duration": "0.25s",
          },
        },
        { selector: "node[category = 'agent']", style: { "border-width": 3, "background-opacity": 0.95 } },
        { selector: "node[category = 'integration']", style: { "border-width": 3, "border-style": "dashed" as const } },
        { selector: "node[category = 'core']", style: { "background-opacity": 0.6, "border-style": "dotted" as const } },
        {
          selector: "node.hover",
          style: {
            "border-width": 5,
            "border-color": "#60a5fa",
            "background-opacity": 1,
            "font-size": 13,
            color: "#f1f5f9",
            "z-index": 100,
          },
        },
        { selector: "node.neighbor", style: { "border-width": 3.5, "border-color": "#60a5fa", "background-opacity": 0.95 } },
        { selector: "node.faded", style: { opacity: 0.12 } },
        { selector: "node.search-match", style: { "border-width": 5, "border-color": "#22c55e", "background-opacity": 1, "z-index": 150 } },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "data(lineColor)",
            "target-arrow-color": "data(lineColor)",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.8,
            "curve-style": "bezier",
            opacity: 0.3,
          },
        },
        { selector: "edge[edgeType = 'triggers']", style: { "line-style": "dashed" as const, width: 2, opacity: 0.5 } },
        { selector: "edge.highlighted", style: { opacity: 1, width: 3.5, "z-index": 50 } },
        { selector: "edge.faded", style: { opacity: 0.03 } },
      ] as cytoscape.StylesheetStyle[],
      layout: layoutConfig,
      minZoom: 0.15,
      maxZoom: 3,
      wheelSensitivity: 0.3,
    });

    cy.on("mouseover", "node", (evt) => {
      const node = evt.target;
      const connEdges = node.connectedEdges();
      const neighbors = connEdges.connectedNodes().difference(node);
      cy.elements().addClass("faded");
      node.removeClass("faded").addClass("hover");
      neighbors.removeClass("faded").addClass("neighbor");
      connEdges.removeClass("faded").addClass("highlighted");

      const pos = node.renderedPosition();
      const nodeData = node.data() as GraphNode;
      if (archCyRef.current) {
        const rect = archCyRef.current.getBoundingClientRect();
        setArchTooltip({ node: nodeData, x: pos.x + rect.left + 20, y: pos.y + rect.top - 20 });
      }
    });

    cy.on("mouseout", "node", () => {
      cy.elements().removeClass("faded hover highlighted neighbor");
      setArchTooltip(null);
    });

    cy.on("tap", "node", (evt) => {
      cy.animate({ center: { eles: evt.target }, zoom: 1.5 }, { duration: 400 });
    });

    archCyInstanceRef.current = cy;
  }, []);

  // ── Workflow data loading ──────────────────────────────────────────────────

  const loadWorkflowData = useCallback(async () => {
    try {
      setWfLoading(true);
      const resp = await fetch(`${API_BASE}/architektura/workflow`, { headers: getAuthHeaders() });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      setWfData(json);
      return json;
    } catch {
      return null;
    } finally {
      setWfLoading(false);
    }
  }, []);

  // ── Workflow graph init ────────────────────────────────────────────────────

  const initWorkflowGraph = useCallback(async (wfGraphData: WorkflowData) => {
    if (!wfCyRef.current) return;

    const cytoscape = await loadCytoscape();

    if (wfCyInstanceRef.current) {
      (wfCyInstanceRef.current as { destroy: () => void }).destroy();
    }

    const elements: cytoscape.ElementDefinition[] = [];

    // Phase ordering for vertical position
    const phaseOrder: Record<string, number> = {
      vstup: 0,
      obchod: 1,
      "výroba": 2,
      logistika: 3,
      finance: 4,
      archiv: 5,
    };

    for (const node of wfGraphData.nodes) {
      const catColors = WORKFLOW_CATEGORY_COLORS[node.category] || WORKFLOW_CATEGORY_COLORS.order_status;
      const isOrderStatus = node.category === "order_status";
      const size = isOrderStatus ? 55 : 40;

      elements.push({
        group: "nodes",
        data: {
          id: node.id,
          label: node.label,
          description: node.description,
          category: node.category,
          phase: node.phase,
          phaseOrder: phaseOrder[node.phase] ?? 3,
          bgColor: node.color,
          borderColor: catColors.border,
          size,
        },
      });
    }

    const nodeIds = new Set(elements.filter((e) => e.group === "nodes").map((e) => e.data.id));
    for (const edge of wfGraphData.edges) {
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) continue;
      elements.push({
        group: "edges",
        data: {
          source: edge.source,
          target: edge.target,
          label: edge.label,
          edgeType: edge.edge_type,
          lineColor: WORKFLOW_EDGE_COLORS[edge.edge_type] || "#64748b",
        },
      });
    }

    const cy = cytoscape({
      container: wfCyRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            width: "data(size)",
            height: "data(size)",
            "background-color": "data(bgColor)",
            "background-opacity": 0.9,
            "border-width": 3,
            "border-color": "data(borderColor)",
            label: "data(label)",
            "text-valign": "bottom",
            "text-halign": "center",
            "font-size": 12,
            "font-weight": "bold",
            color: "#e2e8f0",
            "text-margin-y": 10,
            "text-outline-color": "#0a0e17",
            "text-outline-width": 2.5,
            shape: "round-rectangle",
            opacity: 1,
            "transition-property": "opacity, border-width, border-color",
            "transition-duration": "0.25s",
          },
        },
        {
          selector: "node[category = 'order_status']",
          style: {
            shape: "round-rectangle",
            "border-width": 3.5,
            "font-size": 13,
          },
        },
        {
          selector: "node[category = 'pipeline']",
          style: {
            shape: "ellipse",
            "background-opacity": 0.7,
            "border-style": "dashed" as const,
          },
        },
        {
          selector: "node[category = 'support']",
          style: {
            shape: "diamond",
            "background-opacity": 0.75,
            "font-size": 10,
          },
        },
        {
          selector: "node.hover",
          style: {
            "border-width": 5,
            "border-color": "#60a5fa",
            "background-opacity": 1,
            "font-size": 14,
            color: "#f8fafc",
            "z-index": 100,
          },
        },
        { selector: "node.neighbor", style: { "border-width": 4, "border-color": "#60a5fa", "background-opacity": 0.95 } },
        { selector: "node.faded", style: { opacity: 0.15 } },
        {
          selector: "edge",
          style: {
            width: 2.5,
            "line-color": "data(lineColor)",
            "target-arrow-color": "data(lineColor)",
            "target-arrow-shape": "triangle",
            "arrow-scale": 1,
            "curve-style": "bezier",
            opacity: 0.6,
            label: "data(label)",
            "font-size": 9,
            color: "#94a3b8",
            "text-rotation": "autorotate",
            "text-outline-color": "#0a0e17",
            "text-outline-width": 2,
            "text-margin-y": -10,
          },
        },
        {
          selector: "edge[edgeType = 'back']",
          style: {
            "line-style": "dashed" as const,
            width: 2,
            opacity: 0.5,
            "target-arrow-shape": "triangle-backcurve",
          },
        },
        {
          selector: "edge[edgeType = 'support']",
          style: {
            "line-style": "dotted" as const,
            width: 1.5,
            opacity: 0.4,
          },
        },
        {
          selector: "edge[edgeType = 'pipeline']",
          style: {
            width: 2,
            opacity: 0.5,
          },
        },
        { selector: "edge.highlighted", style: { opacity: 1, width: 4, "z-index": 50, "font-size": 11 } },
        { selector: "edge.faded", style: { opacity: 0.05 } },
      ] as cytoscape.StylesheetStyle[],
      layout: {
        name: "breadthfirst",
        directed: true,
        padding: 60,
        spacingFactor: 1.6,
        animate: true,
        animationDuration: 600,
        roots: "#pipe_email_in",
      } as cytoscape.LayoutOptions & Record<string, unknown>,
      minZoom: 0.15,
      maxZoom: 3,
      wheelSensitivity: 0.3,
    });

    cy.on("mouseover", "node", (evt) => {
      const node = evt.target;
      const connEdges = node.connectedEdges();
      const neighbors = connEdges.connectedNodes().difference(node);
      cy.elements().addClass("faded");
      node.removeClass("faded").addClass("hover");
      neighbors.removeClass("faded").addClass("neighbor");
      connEdges.removeClass("faded").addClass("highlighted");

      const pos = node.renderedPosition();
      const nodeData = node.data() as WorkflowNode;
      if (wfCyRef.current) {
        const rect = wfCyRef.current.getBoundingClientRect();
        setWfTooltip({ node: nodeData, x: pos.x + rect.left + 20, y: pos.y + rect.top - 20 });
      }
    });

    cy.on("mouseout", "node", () => {
      cy.elements().removeClass("faded hover highlighted neighbor");
      setWfTooltip(null);
    });

    cy.on("tap", "node", (evt) => {
      cy.animate({ center: { eles: evt.target }, zoom: 1.8 }, { duration: 400 });
    });

    wfCyInstanceRef.current = cy;
  }, []);

  // ── Effects ────────────────────────────────────────────────────────────────

  // Initial load — always refresh architecture from codebase
  useEffect(() => {
    (async () => {
      const d = await loadArchData(true);
      if (d) setLoading(false);
    })();
  }, [loadArchData]);

  // Rebuild architecture graph when data/layout/categories change
  useEffect(() => {
    if (!archData || loading || activeTab !== "architecture") return;
    initArchGraph(archData, currentLayout, activeCategories);
  }, [archData, currentLayout, activeCategories, loading, activeTab, initArchGraph]);

  // Load workflow data when switching to workflow tab
  useEffect(() => {
    if (activeTab !== "workflow") return;
    if (!wfData) {
      loadWorkflowData();
    }
  }, [activeTab, wfData, loadWorkflowData]);

  // Rebuild workflow graph when data is available
  useEffect(() => {
    if (!wfData || activeTab !== "workflow") return;
    // Slight delay to let the container render
    const t = setTimeout(() => initWorkflowGraph(wfData), 50);
    return () => clearTimeout(t);
  }, [wfData, activeTab, initWorkflowGraph]);

  // Architecture search
  useEffect(() => {
    if (activeTab !== "architecture") return;
    const cy = archCyInstanceRef.current as cytoscape.Core | null;
    if (!cy) return;

    cy.elements().removeClass("search-match faded");
    if (!archSearch.trim()) return;

    const q = archSearch.toLowerCase();
    cy.elements().addClass("faded");
    const matched = cy.nodes().filter((node: cytoscape.NodeSingular) => {
      const d = node.data();
      return (
        (d.label || "").toLowerCase().includes(q) ||
        (d.fullLabel || "").toLowerCase().includes(q) ||
        (d.description || "").toLowerCase().includes(q) ||
        (d.file_path || "").toLowerCase().includes(q)
      );
    });
    matched.removeClass("faded").addClass("search-match");
    matched.connectedEdges().removeClass("faded").connectedNodes().removeClass("faded");
  }, [archSearch, activeTab]);

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleArchRefresh = async () => {
    setArchRefreshing(true);
    await loadArchData(true);
    setArchRefreshing(false);
  };

  const handleFit = () => {
    const cy = (activeTab === "architecture" ? archCyInstanceRef.current : wfCyInstanceRef.current) as cytoscape.Core | null;
    if (cy) cy.animate({ fit: { eles: cy.elements(), padding: 50 } }, { duration: 400 });
  };

  const handleExport = () => {
    const cy = (activeTab === "architecture" ? archCyInstanceRef.current : wfCyInstanceRef.current) as cytoscape.Core | null;
    if (!cy) return;
    const png = cy.png({ scale: 2, bg: "#0a0e17", full: true });
    const link = document.createElement("a");
    link.download = activeTab === "architecture" ? "infer-forge-architecture.png" : "infer-forge-workflow.png";
    link.href = png;
    link.click();
  };

  const toggleCategory = (cat: string) => {
    setActiveCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  // ── Loading state ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[80vh]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-3 text-muted-foreground">Analyzuji architekturu...</span>
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Header */}
      <div className="flex items-center gap-4 px-4 py-2 border-b bg-background/95 backdrop-blur shrink-0">
        {/* Tabs */}
        <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5">
          <button
            onClick={() => setActiveTab("architecture")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === "architecture"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Network className="h-4 w-4" />
            Architektura
          </button>
          <button
            onClick={() => setActiveTab("workflow")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === "workflow"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <GitBranch className="h-4 w-4" />
            Proces zakázky
          </button>
        </div>

        {/* Architecture stats */}
        {activeTab === "architecture" && archData && (
          <div className="hidden md:flex items-center gap-4 text-xs text-muted-foreground">
            <span>Uzly: <span className="text-blue-500 font-semibold">{archData.stats.total_nodes}</span></span>
            <span>Hrany: <span className="text-blue-500 font-semibold">{archData.stats.total_edges}</span></span>
            <span>LOC: <span className="text-blue-500 font-semibold">{archData.stats.total_lines.toLocaleString("cs")}</span></span>
            <span>Funkce: <span className="text-blue-500 font-semibold">{archData.stats.total_functions}</span></span>
          </div>
        )}

        {/* Workflow stats */}
        {activeTab === "workflow" && wfData && (
          <div className="hidden md:flex items-center gap-4 text-xs text-muted-foreground">
            <span>Stavy: <span className="text-blue-500 font-semibold">{wfData.nodes.filter(n => n.category === "order_status").length}</span></span>
            <span>Pipeline: <span className="text-blue-500 font-semibold">{wfData.nodes.filter(n => n.category === "pipeline").length}</span></span>
            <span>Podprocesy: <span className="text-blue-500 font-semibold">{wfData.nodes.filter(n => n.category === "support").length}</span></span>
          </div>
        )}

        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleFit}>
            <Maximize className="h-4 w-4 mr-1" /> Vejít
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-1" /> PNG
          </Button>
          {activeTab === "architecture" && (
            <Button size="sm" onClick={handleArchRefresh} disabled={archRefreshing}>
              <RefreshCw className={`h-4 w-4 mr-1 ${archRefreshing ? "animate-spin" : ""}`} />
              Obnovit
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Architecture Sidebar */}
        {activeTab === "architecture" && (
          <div className="w-60 border-r p-3 overflow-y-auto shrink-0 hidden lg:block">
            <div className="relative mb-3">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Hledat uzel..."
                value={archSearch}
                onChange={e => setArchSearch(e.target.value)}
                className="pl-8 h-9 text-sm"
              />
            </div>

            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Kategorie</p>
              {archData && Object.entries(CATEGORY_COLORS).map(([cat, colors]) => {
                const count = archData.stats.categories[cat]?.count || 0;
                if (!count) return null;
                const label = archData.category_labels[cat] || cat;
                return (
                  <label key={cat} className="flex items-center gap-2 py-1 px-1 rounded hover:bg-accent/50 cursor-pointer text-sm">
                    <input
                      type="checkbox"
                      checked={activeCategories.has(cat)}
                      onChange={() => toggleCategory(cat)}
                      className="rounded"
                    />
                    <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: colors.bg }} />
                    {label}
                    <span className="ml-auto text-xs text-muted-foreground bg-muted px-1.5 rounded">{count}</span>
                  </label>
                );
              })}
            </div>

            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Rozložení</p>
              {LAYOUTS.map(l => (
                <button
                  key={l.id}
                  onClick={() => setCurrentLayout(l.id)}
                  className={`block w-full text-left text-sm px-2 py-1 rounded mb-0.5 ${currentLayout === l.id ? "bg-blue-600 text-white" : "hover:bg-accent/50 text-muted-foreground"}`}
                >
                  {l.label}
                </button>
              ))}
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Hrany</p>
              <div className="grid grid-cols-2 gap-1 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-slate-500" />závisí na</span>
                <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-blue-500" />API volání</span>
                <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-purple-500" />data flow</span>
                <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-red-500" />spouští</span>
              </div>
            </div>
          </div>
        )}

        {/* Workflow Sidebar */}
        {activeTab === "workflow" && (
          <div className="w-60 border-r p-3 overflow-y-auto shrink-0 hidden lg:block">
            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Kategorie uzlů</p>
              {wfData && Object.entries(wfData.category_labels).map(([cat, label]) => {
                const count = wfData.nodes.filter(n => n.category === cat).length;
                const catColor = WORKFLOW_CATEGORY_COLORS[cat]?.bg || "#6b7280";
                return (
                  <div key={cat} className="flex items-center gap-2 py-1.5 px-1 text-sm">
                    <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: catColor }} />
                    <span className="text-foreground">{label}</span>
                    <span className="ml-auto text-xs text-muted-foreground bg-muted px-1.5 rounded">{count}</span>
                  </div>
                );
              })}
            </div>

            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Fáze procesu</p>
              {wfData && Object.entries(wfData.phase_labels).map(([phase, label]) => {
                const count = wfData.nodes.filter(n => n.phase === phase).length;
                return (
                  <div key={phase} className="flex items-center gap-2 py-1 px-1 text-sm text-muted-foreground">
                    <span className="text-foreground">{label}</span>
                    <span className="ml-auto text-xs bg-muted px-1.5 rounded">{count}</span>
                  </div>
                );
              })}
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Hrany</p>
              <div className="space-y-1 text-xs text-muted-foreground">
                <span className="flex items-center gap-2"><span className="w-5 h-0.5 bg-blue-500 rounded" />Hlavní tok</span>
                <span className="flex items-center gap-2"><span className="w-5 h-0.5 bg-amber-500 rounded border-dashed" />Zpětný tok</span>
                <span className="flex items-center gap-2"><span className="w-5 h-0.5 bg-slate-500 rounded" />Email pipeline</span>
                <span className="flex items-center gap-2"><span className="w-5 h-0.5 bg-emerald-500 rounded" style={{ borderTop: "1px dotted" }} />Podpůrný proces</span>
              </div>
            </div>
          </div>
        )}

        {/* Architecture Graph */}
        <div
          ref={archCyRef}
          className="flex-1 bg-[#0a0e17]"
          style={{ display: activeTab === "architecture" ? "block" : "none" }}
        />

        {/* Workflow Graph */}
        <div
          ref={wfCyRef}
          className="flex-1 bg-[#0a0e17]"
          style={{ display: activeTab === "workflow" ? "block" : "none" }}
        />

        {/* Workflow loading overlay */}
        {activeTab === "workflow" && wfLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e17]/80 z-10">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            <span className="ml-3 text-muted-foreground">Načítám workflow...</span>
          </div>
        )}
      </div>

      {/* Architecture Tooltip */}
      {activeTab === "architecture" && archTooltip && (
        <div
          className="fixed z-50 bg-card border rounded-xl shadow-2xl min-w-[300px] max-w-[420px] pointer-events-none"
          style={{ left: archTooltip.x, top: archTooltip.y }}
        >
          <div className="flex items-center gap-2 px-4 py-3 border-b">
            <Badge style={{ backgroundColor: CATEGORY_COLORS[archTooltip.node.category]?.bg, color: CATEGORY_COLORS[archTooltip.node.category]?.text }}>
              {archData?.category_labels[archTooltip.node.category] || archTooltip.node.category}
            </Badge>
            <span className="font-semibold text-sm">{archTooltip.node.label}</span>
          </div>
          <div className="px-4 py-3 text-sm">
            <p className="text-muted-foreground mb-2">{archTooltip.node.description || "Bez popisu"}</p>
            {(archTooltip.node.line_count > 0 || archTooltip.node.function_count > 0) && (
              <p className="text-xs text-muted-foreground border-t pt-2">
                {archTooltip.node.line_count > 0 && <><span className="text-foreground font-medium">{archTooltip.node.line_count}</span> LOC &nbsp;|&nbsp; </>}
                {archTooltip.node.function_count > 0 && <><span className="text-foreground font-medium">{archTooltip.node.function_count}</span> funkcí</>}
              </p>
            )}
            {archTooltip.node.endpoints.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {archTooltip.node.endpoints.slice(0, 6).map((ep, i) => (
                  <span key={i} className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">{ep}</span>
                ))}
                {archTooltip.node.endpoints.length > 6 && (
                  <span className="text-xs bg-muted px-1.5 py-0.5 rounded">+{archTooltip.node.endpoints.length - 6}</span>
                )}
              </div>
            )}
          </div>
          {archTooltip.node.file_path && (
            <div className="px-4 py-2 border-t text-xs text-muted-foreground font-mono">
              {archTooltip.node.file_path}
            </div>
          )}
        </div>
      )}

      {/* Workflow Tooltip */}
      {activeTab === "workflow" && wfTooltip && (
        <div
          className="fixed z-50 bg-card border rounded-xl shadow-2xl min-w-[280px] max-w-[380px] pointer-events-none"
          style={{ left: wfTooltip.x, top: wfTooltip.y }}
        >
          <div className="flex items-center gap-2 px-4 py-3 border-b">
            <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: wfTooltip.node.color }} />
            <span className="font-semibold text-sm">{wfTooltip.node.label}</span>
            {wfData && (
              <Badge variant="outline" className="ml-auto text-xs">
                {wfData.category_labels[wfTooltip.node.category] || wfTooltip.node.category}
              </Badge>
            )}
          </div>
          <div className="px-4 py-3 text-sm">
            <p className="text-muted-foreground">{wfTooltip.node.description}</p>
            {wfTooltip.node.phase && wfData && (
              <p className="text-xs text-muted-foreground border-t pt-2 mt-2">
                Fáze: <span className="text-foreground font-medium">{wfData.phase_labels[wfTooltip.node.phase] || wfTooltip.node.phase}</span>
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
