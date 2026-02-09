import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const columns = [
  { name: "Poptávka", color: "#64748b", count: 2 },
  { name: "Nabídka", color: "#3b82f6", count: 3 },
  { name: "Objednávka", color: "#8b5cf6", count: 2 },
  { name: "Výroba", color: "#f59e0b", count: 4 },
  { name: "Expedice", color: "#06b6d4", count: 1 },
  { name: "Fakturace", color: "#22c55e", count: 2 },
  { name: "Dokončeno", color: "#10b981", count: 5 },
];

export const KanbanSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const imageOpacity = interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" });
  const imageScale = interpolate(frame, [0, 25], [1.05, 1], { extrapolateRight: "clamp" });

  // Card moving animation
  const cardActiveCol = interpolate(frame, [40, 180], [0, 6], { extrapolateRight: "clamp" });
  const cardX = interpolate(frame, [40, 180], [0, 100], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        opacity: containerOpacity,
        background: "linear-gradient(160deg, #0a0a0a 0%, #111827 50%, #1e1b4b 100%)",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      }}
    >
      {/* Screenshot */}
      <div style={{
        position: "absolute",
        top: 80,
        left: 80,
        right: 80,
        bottom: 200,
        opacity: imageOpacity,
        transform: `scale(${imageScale})`,
        borderRadius: 16,
        overflow: "hidden",
        boxShadow: "0 25px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.08)",
      }}>
        <div style={{
          height: 36,
          background: "linear-gradient(180deg, #2a2a3a 0%, #1f1f2e 100%)",
          display: "flex", alignItems: "center", paddingLeft: 16, gap: 8,
          borderBottom: "1px solid rgba(255,255,255,0.05)",
        }}>
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#ff5f57" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#febc2e" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#28c840" }} />
          <div style={{
            marginLeft: 20, padding: "4px 60px", borderRadius: 6,
            background: "rgba(255,255,255,0.06)", color: "#64748b", fontSize: 12,
          }}>
            91.99.126.53:3000/kanban
          </div>
        </div>
        <Img
          src={staticFile("pages/04-kanban.png")}
          style={{ width: "100%", height: "calc(100% - 36px)", objectFit: "cover", objectPosition: "top left" }}
        />
      </div>

      {/* Title overlay */}
      <div style={{
        position: "absolute",
        top: 20,
        left: 80,
        display: "flex",
        alignItems: "center",
        gap: 16,
      }}>
        <div style={{
          width: interpolate(frame, [15, 40], [0, 4], { extrapolateRight: "clamp" }),
          height: 50, background: "#ef4444", borderRadius: 2,
        }} />
        <div>
          <div style={{ fontSize: 32, fontWeight: 700, color: "#ffffff" }}>Kanban Pipeline</div>
          <div style={{
            opacity: interpolate(frame, [20, 38], [0, 1], { extrapolateRight: "clamp" }),
            fontSize: 18, color: "#94a3b8",
          }}>
            Přehled celé výroby na jednom místě
          </div>
        </div>
      </div>

      {/* Bottom pipeline animation */}
      <div style={{
        position: "absolute",
        bottom: 40,
        left: 80,
        right: 80,
        display: "flex",
        gap: 8,
        alignItems: "center",
      }}>
        {columns.map((col, i) => {
          const delay = 30 + i * 8;
          const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
          const isActive = Math.floor(cardActiveCol) === i;
          const highlight = isActive ? 1 : 0;

          return (
            <div key={col.name} style={{ display: "flex", alignItems: "center", flex: 1 }}>
              <div style={{
                opacity,
                flex: 1,
                padding: "12px 10px",
                borderRadius: 10,
                background: isActive
                  ? `${col.color}20`
                  : "rgba(255,255,255,0.03)",
                border: `1px solid ${isActive ? `${col.color}50` : "rgba(255,255,255,0.06)"}`,
                textAlign: "center",
                transition: "all 0.3s",
                transform: isActive ? "scale(1.05)" : "scale(1)",
              }}>
                <div style={{ fontSize: 13, color: col.color, fontWeight: 700, marginBottom: 4 }}>
                  {col.name}
                </div>
                <div style={{ fontSize: 20, color: "#e2e8f0", fontWeight: 800 }}>
                  {col.count}
                </div>
              </div>
              {i < columns.length - 1 && (
                <div style={{
                  opacity: interpolate(frame, [delay + 5, delay + 15], [0, 1], { extrapolateRight: "clamp" }),
                  color: "#64748b",
                  fontSize: 16,
                  margin: "0 2px",
                }}>
                  →
                </div>
              )}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
