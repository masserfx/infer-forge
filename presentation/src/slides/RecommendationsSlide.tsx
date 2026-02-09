import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const recommendations = [
  { icon: "🔴", text: "Zakázka ZAK-2025-042 po termínu", severity: "critical", color: "#ef4444" },
  { icon: "🟡", text: "3 kalkulace čekají na schválení", severity: "warning", color: "#f59e0b" },
  { icon: "🔵", text: "Nabídka připravena k odeslání", severity: "info", color: "#3b82f6" },
  { icon: "🟡", text: "5 emailů bez odpovědi > 24h", severity: "warning", color: "#f59e0b" },
];

export const RecommendationsSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const titleOpacity = interpolate(frame, [5, 25], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [5, 25], [30, 0], { extrapolateRight: "clamp" });
  const imageOpacity = interpolate(frame, [10, 30], [0, 1], { extrapolateRight: "clamp" });
  const imageScale = interpolate(frame, [10, 35], [1.05, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        opacity: containerOpacity,
        background: "linear-gradient(160deg, #0a0a0a 0%, #111827 50%, #1e1b4b 100%)",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      }}
    >
      {/* Decorative circles */}
      <div style={{
        position: "absolute", bottom: -100, left: -100,
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(59,130,246,0.06) 0%, transparent 70%)",
      }} />

      {/* Title */}
      <div style={{
        position: "absolute",
        top: 60,
        left: 80,
        right: 80,
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
      }}>
        <div style={{ fontSize: 48, fontWeight: 800, color: "#ffffff" }}>
          AI doporučení v <span style={{ color: "#3b82f6" }}>reálném čase</span>
        </div>
        <div style={{
          opacity: interpolate(frame, [15, 35], [0, 1], { extrapolateRight: "clamp" }),
          fontSize: 20,
          color: "#94a3b8",
          marginTop: 12,
        }}>
          Chytré priority na základě dat
        </div>
      </div>

      <div style={{ display: "flex", gap: 40, padding: "200px 80px 80px 80px" }}>
        {/* Left: Recommendation cards */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
          {recommendations.map((rec, i) => {
            const delay = 40 + i * 15;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const x = interpolate(frame, [delay, delay + 12], [-40, 0], { extrapolateRight: "clamp" });

            return (
              <div key={i} style={{
                opacity,
                transform: `translateX(${x}px)`,
                padding: "20px 24px",
                borderRadius: 14,
                background: `${rec.color}08`,
                border: `2px solid ${rec.color}30`,
                display: "flex",
                alignItems: "center",
                gap: 16,
              }}>
                <span style={{ fontSize: 32 }}>{rec.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{
                    fontSize: 16,
                    color: "#e2e8f0",
                    fontWeight: 600,
                  }}>
                    {rec.text}
                  </div>
                  <div style={{
                    fontSize: 13,
                    color: "#94a3b8",
                    marginTop: 4,
                  }}>
                    {rec.severity === "critical" && "Vysoká priorita"}
                    {rec.severity === "warning" && "Vyžaduje akci"}
                    {rec.severity === "info" && "Tip"}
                  </div>
                </div>
                <div style={{
                  padding: "6px 14px",
                  borderRadius: 8,
                  background: rec.color,
                  fontSize: 13,
                  fontWeight: 700,
                  color: "#ffffff",
                }}>
                  Detail
                </div>
              </div>
            );
          })}

          {/* Time savings stat */}
          <div style={{
            opacity: interpolate(frame, [110, 130], [0, 1], { extrapolateRight: "clamp" }),
            marginTop: 20,
            padding: "24px 28px",
            borderRadius: 16,
            background: "rgba(34,197,94,0.08)",
            border: "1px solid rgba(34,197,94,0.2)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}>
            <div>
              <div style={{ fontSize: 14, color: "#94a3b8", marginBottom: 6 }}>
                Průměrná úspora
              </div>
              <div style={{ fontSize: 36, fontWeight: 800, color: "#22c55e" }}>
                45 min/den
              </div>
            </div>
            <div style={{ fontSize: 48 }}>⚡</div>
          </div>
        </div>

        {/* Right: Dashboard screenshot */}
        <div style={{ flex: 1 }}>
          <div style={{
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
                91.99.126.53:3000/dashboard
              </div>
            </div>
            <Img
              src={staticFile("pages/02-dashboard.png")}
              style={{ width: "100%", height: 600, objectFit: "cover", objectPosition: "top left" }}
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
