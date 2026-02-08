import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const stacks = [
  {
    category: "Backend",
    techs: [
      { name: "Python 3.12", desc: "async/await" },
      { name: "FastAPI", desc: "REST API" },
      { name: "SQLAlchemy 2.0", desc: "async ORM" },
      { name: "Celery + Redis", desc: "task queue" },
      { name: "Alembic", desc: "migrace" },
    ],
    color: "#22c55e",
  },
  {
    category: "Frontend",
    techs: [
      { name: "Next.js 16", desc: "App Router" },
      { name: "TypeScript", desc: "strict mode" },
      { name: "Tailwind CSS 4", desc: "utility-first" },
      { name: "shadcn/ui", desc: "komponenty" },
      { name: "TanStack Query", desc: "data fetching" },
    ],
    color: "#3b82f6",
  },
  {
    category: "AI & Data",
    techs: [
      { name: "Claude API", desc: "tool_use agent" },
      { name: "pgvector", desc: "embedding search" },
      { name: "sentence-transformers", desc: "multilingual" },
      { name: "Tesseract OCR", desc: "document scan" },
      { name: "WeasyPrint", desc: "PDF gen" },
    ],
    color: "#a855f7",
  },
];

export const TechStackSlide: React.FC = () => {
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
        padding: "60px 80px",
      }}
    >
      <div style={{
        opacity: titleOpacity,
        fontSize: 48,
        fontWeight: 800,
        color: "#ffffff",
        marginBottom: 50,
      }}>
        Tech <span style={{ color: "#ef4444" }}>Stack</span>
      </div>

      <div style={{ display: "flex", gap: 30, width: "100%", maxWidth: 1500 }}>
        {stacks.map((stack, si) => {
          const delay = 10 + si * 15;
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
          const slideY = interpolate(frame, [delay, delay + 15], [30, 0], { extrapolateRight: "clamp" });

          return (
            <div key={stack.category} style={{
              opacity,
              transform: `translateY(${slideY}px)`,
              flex: 1,
              borderRadius: 20,
              background: "rgba(255,255,255,0.02)",
              border: `1px solid ${stack.color}22`,
              overflow: "hidden",
            }}>
              <div style={{
                padding: "18px 24px",
                background: `${stack.color}15`,
                borderBottom: `1px solid ${stack.color}22`,
              }}>
                <div style={{
                  fontSize: 24,
                  fontWeight: 700,
                  color: stack.color,
                }}>
                  {stack.category}
                </div>
              </div>
              <div style={{ padding: "16px 24px", display: "flex", flexDirection: "column", gap: 12 }}>
                {stack.techs.map((tech, ti) => {
                  const techDelay = delay + 8 + ti * 5;
                  const techOpacity = interpolate(frame, [techDelay, techDelay + 10], [0, 1], { extrapolateRight: "clamp" });

                  return (
                    <div key={tech.name} style={{
                      opacity: techOpacity,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "8px 0",
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                    }}>
                      <span style={{ color: "#ffffff", fontSize: 18, fontWeight: 600 }}>
                        {tech.name}
                      </span>
                      <span style={{ color: "#64748b", fontSize: 14 }}>
                        {tech.desc}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
