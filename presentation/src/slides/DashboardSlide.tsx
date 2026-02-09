import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const statCards = [
  { label: "Aktivní zakázky", value: 24, color: "#3b82f6", suffix: "" },
  { label: "Měsíční obrat", value: 2800, color: "#22c55e", suffix: " tis." },
  { label: "Ve výrobě", value: 8, color: "#f59e0b", suffix: "" },
  { label: "K fakturaci", value: 5, color: "#ef4444", suffix: "" },
];

export const DashboardSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const imageOpacity = interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" });
  const imageScale = interpolate(frame, [0, 25], [1.05, 1], { extrapolateRight: "clamp" });

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
            91.99.126.53:3000/dashboard
          </div>
        </div>
        <Img
          src={staticFile("pages/18-dashboard-full.png")}
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
          <div style={{ fontSize: 32, fontWeight: 700, color: "#ffffff" }}>Dashboard</div>
          <div style={{
            opacity: interpolate(frame, [20, 38], [0, 1], { extrapolateRight: "clamp" }),
            fontSize: 18, color: "#94a3b8",
          }}>
            Manažerský přehled v reálném čase
          </div>
        </div>
      </div>

      {/* Bottom stat cards */}
      <div style={{
        position: "absolute",
        bottom: 40,
        left: 80,
        right: 80,
        display: "flex",
        gap: 20,
      }}>
        {statCards.map((stat, i) => {
          const delay = 30 + i * 12;
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
          const scale = interpolate(frame, [delay, delay + 15], [0.8, 1], { extrapolateRight: "clamp" });
          const countUp = interpolate(frame, [delay + 5, delay + 25], [0, stat.value], { extrapolateRight: "clamp" });

          return (
            <div key={stat.label} style={{
              opacity,
              transform: `scale(${scale})`,
              flex: 1,
              padding: "20px 24px",
              borderRadius: 16,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              backdropFilter: "blur(10px)",
              textAlign: "center",
            }}>
              <div style={{ fontSize: 36, fontWeight: 800, color: stat.color, marginBottom: 6 }}>
                {Math.round(countUp)}{stat.suffix}
              </div>
              <div style={{ fontSize: 14, color: "#94a3b8", fontWeight: 500 }}>{stat.label}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
