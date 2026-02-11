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
  Mail,
  Brain,
  ScanLine,
  Eye,
  UserCheck,
  FileText,
  Calculator,
  ClipboardCheck,
  Cog,
  Truck,
  Receipt,
  CheckCircle,
  Wrench,
  Handshake,
  ArrowDown,
  ArrowRight,
  ChevronRight,
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

// ── Workflow icon mapping ────────────────────────────────────────────────────

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  mail: Mail,
  brain: Brain,
  scan: ScanLine,
  eye: Eye,
  "user-check": UserCheck,
  inbox: FileText,
  "file-text": FileText,
  "clipboard-check": ClipboardCheck,
  calculator: Calculator,
  cog: Cog,
  truck: Truck,
  receipt: Receipt,
  "check-circle": CheckCircle,
  "file-output": FileText,
  "refresh-cw": RefreshCw,
  wrench: Wrench,
  handshake: Handshake,
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

// ── Workflow column definitions ──────────────────────────────────────────────

interface WfColumn {
  id: string;
  title: string;
  color: string;
  bgLight: string;
  borderColor: string;
  phases: string[];
  nodeOrder: string[];
}

const WF_COLUMNS: WfColumn[] = [
  {
    id: "prijem",
    title: "Příjem zakázky",
    color: "#64748b",
    bgLight: "rgba(100,116,139,0.08)",
    borderColor: "rgba(100,116,139,0.25)",
    phases: ["vstup"],
    nodeOrder: ["pipe_email_in", "pipe_classify", "pipe_ocr", "pipe_parse", "pipe_customer"],
  },
  {
    id: "obchod",
    title: "Obchodní proces",
    color: "#f59e0b",
    bgLight: "rgba(245,158,11,0.08)",
    borderColor: "rgba(245,158,11,0.25)",
    phases: ["obchod"],
    nodeOrder: ["status_poptavka", "sup_kalkulace", "status_nabidka", "sup_dokumenty", "status_objednavka"],
  },
  {
    id: "vyroba",
    title: "Výroba",
    color: "#ef4444",
    bgLight: "rgba(239,68,68,0.08)",
    borderColor: "rgba(239,68,68,0.25)",
    phases: ["výroba"],
    nodeOrder: ["status_vyroba", "sup_operace", "sup_kooperace"],
  },
  {
    id: "dokonceni",
    title: "Dokončení",
    color: "#10b981",
    bgLight: "rgba(16,185,129,0.08)",
    borderColor: "rgba(16,185,129,0.25)",
    phases: ["logistika", "finance", "archiv"],
    nodeOrder: ["status_expedice", "status_fakturace", "sup_pohoda", "status_dokonceno"],
  },
];

// ── Workflow step card ───────────────────────────────────────────────────────

function WfStepCard({ node, edges, isLast }: { node: WorkflowNode; edges: WorkflowEdge[]; isLast: boolean }) {
  const Icon = ICON_MAP[node.icon] || FileText;
  const isStatus = node.category === "order_status";
  const isSupport = node.category === "support";

  // Find forward edge label leading OUT of this node
  const outEdge = edges.find(e => e.source === node.id && e.edge_type === "forward");
  const transitionLabel = outEdge?.label;

  return (
    <div className="flex flex-col items-center">
      {/* Card */}
      <div
        className={`group relative w-full rounded-xl border-2 p-4 transition-all hover:scale-[1.02] hover:shadow-lg ${
          isStatus ? "bg-card" : "bg-card/60"
        } ${isSupport ? "border-dashed" : ""}`}
        style={{ borderColor: node.color + (isSupport ? "80" : "b0") }}
      >
        {/* Category badge */}
        {isSupport && (
          <span className="absolute -top-2.5 left-3 bg-background px-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Podproces
          </span>
        )}

        <div className="flex items-start gap-3">
          {/* Icon circle */}
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
            style={{ backgroundColor: node.color + "20", border: `2px solid ${node.color}` }}
          >
            <span style={{ color: node.color }}><Icon className="h-5 w-5" /></span>
          </div>

          {/* Text */}
          <div className="flex-1 min-w-0">
            <h3 className={`font-bold leading-tight ${isStatus ? "text-base" : "text-sm"}`} style={{ color: node.color }}>
              {node.label}
            </h3>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {node.description}
            </p>
          </div>
        </div>
      </div>

      {/* Arrow + transition label */}
      {!isLast && (
        <div className="flex flex-col items-center py-2">
          {transitionLabel && (
            <span className="mb-1 rounded-full bg-muted px-2.5 py-0.5 text-[11px] font-medium text-muted-foreground">
              {transitionLabel}
            </span>
          )}
          <ArrowDown className="h-5 w-5 text-muted-foreground/50" />
        </div>
      )}
    </div>
  );
}

// ── Workflow column component ────────────────────────────────────────────────

function WfColumnView({ column, nodes, edges }: { column: WfColumn; nodes: WorkflowNode[]; edges: WorkflowEdge[] }) {
  // Order nodes by predefined order
  const orderedNodes = column.nodeOrder
    .map(id => nodes.find(n => n.id === id))
    .filter((n): n is WorkflowNode => n != null);

  return (
    <div
      className="flex flex-col rounded-2xl border"
      style={{ backgroundColor: column.bgLight, borderColor: column.borderColor }}
    >
      {/* Column header */}
      <div
        className="flex items-center gap-2 rounded-t-2xl px-5 py-3"
        style={{ backgroundColor: column.color + "18", borderBottom: `2px solid ${column.borderColor}` }}
      >
        <div className="h-3 w-3 rounded-full" style={{ backgroundColor: column.color }} />
        <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: column.color }}>
          {column.title}
        </h2>
        <span className="ml-auto rounded-full bg-background/80 px-2 py-0.5 text-xs font-medium text-muted-foreground">
          {orderedNodes.length}
        </span>
      </div>

      {/* Steps */}
      <div className="flex flex-col gap-0 p-4">
        {orderedNodes.map((node, i) => (
          <WfStepCard
            key={node.id}
            node={node}
            edges={edges}
            isLast={i === orderedNodes.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

// ── Column transition arrow ──────────────────────────────────────────────────

function ColumnArrow({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 px-1 self-center">
      <ChevronRight className="h-6 w-6 text-muted-foreground/40" />
      <span className="text-[10px] font-medium text-muted-foreground/60 [writing-mode:vertical-lr] rotate-180">
        {label}
      </span>
      <ArrowRight className="h-5 w-5 text-muted-foreground/40" />
    </div>
  );
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
  const [wfData, setWfData] = useState<WorkflowData | null>(null);
  const [wfLoading, setWfLoading] = useState(false);

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
    const cy = archCyInstanceRef.current as cytoscape.Core | null;
    if (cy) cy.animate({ fit: { eles: cy.elements(), padding: 50 } }, { duration: 400 });
  };

  const handleExport = () => {
    const cy = archCyInstanceRef.current as cytoscape.Core | null;
    if (!cy) return;
    const png = cy.png({ scale: 2, bg: "#0a0e17", full: true });
    const link = document.createElement("a");
    link.download = "inferbox-architecture.png";
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

        {/* Workflow description */}
        {activeTab === "workflow" && (
          <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
            Životní cyklus zakázky od e-mailu po fakturaci
          </div>
        )}

        <div className="ml-auto flex items-center gap-2">
          {activeTab === "architecture" && (
            <>
              <Button variant="outline" size="sm" onClick={handleFit}>
                <Maximize className="h-4 w-4 mr-1" /> Vejít
              </Button>
              <Button variant="outline" size="sm" onClick={handleExport}>
                <Download className="h-4 w-4 mr-1" /> PNG
              </Button>
              <Button size="sm" onClick={handleArchRefresh} disabled={archRefreshing}>
                <RefreshCw className={`h-4 w-4 mr-1 ${archRefreshing ? "animate-spin" : ""}`} />
                Obnovit
              </Button>
            </>
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

        {/* Architecture Graph */}
        <div
          ref={archCyRef}
          className="flex-1 bg-[#0a0e17]"
          style={{ display: activeTab === "architecture" ? "block" : "none" }}
        />

        {/* Workflow Swimlane Diagram */}
        {activeTab === "workflow" && (
          <div className="flex-1 overflow-auto bg-background p-6">
            {wfLoading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                <span className="ml-3 text-muted-foreground">Načítám workflow...</span>
              </div>
            ) : wfData ? (
              <div className="mx-auto max-w-7xl">
                {/* Title */}
                <div className="mb-8 text-center">
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-emerald-500 bg-clip-text text-transparent">
                    Proces zakázky — INFERBOX
                  </h1>
                  <p className="mt-2 text-sm text-muted-foreground max-w-2xl mx-auto">
                    Kompletní životní cyklus zakázky od příjmu poptávkového e-mailu přes kalkulaci, výrobu
                    a expedici až po fakturaci v systému Pohoda. Generováno z aktuálního kódu aplikace.
                  </p>
                </div>

                {/* Legend */}
                <div className="mb-6 flex flex-wrap items-center justify-center gap-6 text-xs text-muted-foreground">
                  <span className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full border-2 border-slate-500 bg-slate-500/20 text-[8px]">S</span>
                    Stav zakázky
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full border-2 border-dashed border-emerald-500 bg-emerald-500/20 text-[8px]">P</span>
                    Podproces
                  </span>
                  <span className="flex items-center gap-2">
                    <ArrowDown className="h-4 w-4" /> Hlavní tok
                  </span>
                  <span className="flex items-center gap-2">
                    <ArrowRight className="h-4 w-4" /> Přechod do další fáze
                  </span>
                </div>

                {/* Columns grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] gap-4 xl:gap-0 items-start">
                  {WF_COLUMNS.map((col, colIdx) => (
                    <div key={col.id} className="contents">
                      <WfColumnView
                        column={col}
                        nodes={wfData.nodes}
                        edges={wfData.edges}
                      />
                      {colIdx < WF_COLUMNS.length - 1 && (
                        <div className="hidden xl:flex">
                          <ColumnArrow
                            label={
                              colIdx === 0 ? "Zakázka vytvořena" :
                              colIdx === 1 ? "Zahájení výroby" :
                              "Výroba dokončena"
                            }
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Footer info */}
                <div className="mt-8 rounded-xl border bg-muted/30 p-5">
                  <h3 className="text-sm font-semibold mb-3">Stavový automat zakázky</h3>
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    {wfData.nodes
                      .filter(n => n.category === "order_status")
                      .map((n, i, arr) => (
                        <span key={n.id} className="flex items-center gap-2">
                          <span
                            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold text-white"
                            style={{ backgroundColor: n.color }}
                          >
                            {n.label}
                          </span>
                          {i < arr.length - 1 && (
                            <ArrowRight className="h-4 w-4 text-muted-foreground" />
                          )}
                        </span>
                      ))
                    }
                  </div>
                  <p className="mt-3 text-xs text-muted-foreground">
                    Přechody mezi stavy jsou validovány stavovým automatem v <code className="bg-muted rounded px-1">OrderService.STATUS_TRANSITIONS</code>.
                    Každá změna stavu je zaznamenána v audit trail a přiděluje gamifikační body.
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                Nepodařilo se načíst workflow data.
              </div>
            )}
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
    </div>
  );
}
