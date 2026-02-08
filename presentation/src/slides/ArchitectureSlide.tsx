import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const layers = [
  {
    label: "Frontend",
    items: ["Next.js 16", "TypeScript strict", "Tailwind CSS 4", "shadcn/ui", "TanStack Query"],
    color: "#3b82f6",
    bg: "rgba(59,130,246,0.08)",
  },
  {
    label: "Backend API",
    items: ["FastAPI", "SQLAlchemy 2.0 async", "Pydantic v2", "JWT Auth + RBAC"],
    color: "#22c55e",
    bg: "rgba(34,197,94,0.08)",
  },
  {
    label: "AI & Integrace",
    items: ["Claude API (tool_use)", "Email Agent", "RAG pgvector", "Pohoda XML", "OCR + Excel"],
    color: "#a855f7",
    bg: "rgba(168,85,247,0.08)",
  },
  {
    label: "Infrastruktura",
    items: ["PostgreSQL 16", "Redis + Celery", "Docker Compose", "Prometheus + Grafana", "Loki"],
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.08)",
  },
];

export const ArchitectureSlide: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(160deg, #0a0a0a 0%, #111827 50%, #1e1b4b 100%)",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "60px 100px",
      }}
    >
      <div style={{
        opacity: titleOpacity,
        fontSize: 48,
        fontWeight: 800,
        color: "#ffffff",
        marginBottom: 50,
      }}>
        Architektura <span style={{ color: "#ef4444" }}>systemu</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 20, width: "100%", maxWidth: 1400 }}>
        {layers.map((layer, i) => {
          const delay = 15 + i * 12;
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
          const slideX = interpolate(frame, [delay, delay + 15], [-50, 0], { extrapolateRight: "clamp" });

          return (
            <div key={layer.label} style={{
              opacity,
              transform: `translateX(${slideX}px)`,
              display: "flex",
              alignItems: "center",
              gap: 30,
              padding: "22px 30px",
              borderRadius: 16,
              background: layer.bg,
              border: `1px solid ${layer.color}33`,
            }}>
              <div style={{
                width: 180,
                fontSize: 20,
                fontWeight: 700,
                color: layer.color,
                flexShrink: 0,
              }}>
                {layer.label}
              </div>
              <div style={{
                width: 2,
                height: 40,
                background: `${layer.color}44`,
                borderRadius: 1,
              }} />
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                {layer.items.map((item) => (
                  <div key={item} style={{
                    padding: "6px 16px",
                    borderRadius: 8,
                    background: "rgba(255,255,255,0.05)",
                    color: "#e2e8f0",
                    fontSize: 16,
                    fontWeight: 500,
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}>
                    {item}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
