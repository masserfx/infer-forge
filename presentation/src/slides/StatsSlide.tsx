import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const stats = [
  { value: "557", label: "Backend testu", color: "#22c55e" },
  { value: "69%", label: "Code coverage", color: "#3b82f6" },
  { value: "17", label: "Frontend routes", color: "#a855f7" },
  { value: "11", label: "Docker sluzeb", color: "#f59e0b" },
  { value: "19", label: "Alembic tabulek", color: "#ef4444" },
  { value: "16+", label: "AI features", color: "#06b6d4" },
];

export const StatsSlide: React.FC = () => {
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
        padding: 80,
      }}
    >
      <div style={{
        opacity: titleOpacity,
        fontSize: 48,
        fontWeight: 800,
        color: "#ffffff",
        marginBottom: 60,
        textAlign: "center",
      }}>
        Projekt v <span style={{ color: "#ef4444" }}>cislech</span>
      </div>

      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 40,
        justifyContent: "center",
        maxWidth: 1200,
      }}>
        {stats.map((stat, i) => {
          const delay = 15 + i * 10;
          const opacity = interpolate(frame, [delay, delay + 20], [0, 1], { extrapolateRight: "clamp" });
          const scale = interpolate(frame, [delay, delay + 20], [0.7, 1], { extrapolateRight: "clamp" });
          const countUp = interpolate(
            frame,
            [delay + 5, delay + 30],
            [0, parseInt(stat.value) || 100],
            { extrapolateRight: "clamp" }
          );

          return (
            <div key={stat.label} style={{
              opacity,
              transform: `scale(${scale})`,
              width: 320,
              padding: "40px 30px",
              borderRadius: 20,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              textAlign: "center",
              backdropFilter: "blur(10px)",
            }}>
              <div style={{
                fontSize: 64,
                fontWeight: 800,
                color: stat.color,
                lineHeight: 1,
                marginBottom: 12,
              }}>
                {stat.value.includes("%")
                  ? `${Math.round(countUp)}%`
                  : stat.value.includes("+")
                    ? `${Math.round(countUp)}+`
                    : Math.round(countUp).toString()
                }
              </div>
              <div style={{
                fontSize: 20,
                color: "#94a3b8",
                fontWeight: 500,
              }}>
                {stat.label}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
