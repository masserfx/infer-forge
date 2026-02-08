import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const stats = [
  { value: 635, label: "Backend testu", color: "#22c55e", suffix: "" },
  { value: 67, label: "Code coverage", color: "#3b82f6", suffix: "%" },
  { value: 23, label: "Frontend stranek", color: "#a855f7", suffix: "" },
  { value: 12, label: "Docker sluzeb", color: "#f59e0b", suffix: "" },
  { value: 23, label: "DB tabulek", color: "#ef4444", suffix: "" },
  { value: 10, label: "AI agentu", color: "#06b6d4", suffix: "" },
  { value: 4, label: "Celery workers", color: "#ec4899", suffix: "" },
  { value: 1, label: "WebSocket real-time", color: "#14b8a6", suffix: "" },
];

export const StatsSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 20], [30, 0], { extrapolateRight: "clamp" });

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
      {/* Decorative circles */}
      <div style={{
        position: "absolute", top: -100, left: -100,
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(34,197,94,0.06) 0%, transparent 70%)",
      }} />

      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
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
        gap: 30,
        justifyContent: "center",
        maxWidth: 1300,
      }}>
        {stats.map((stat, i) => {
          const delay = 15 + i * 8;
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
          const scale = interpolate(frame, [delay, delay + 15], [0.7, 1], { extrapolateRight: "clamp" });
          const countUp = interpolate(
            frame,
            [delay + 5, delay + 30],
            [0, stat.value],
            { extrapolateRight: "clamp" }
          );

          return (
            <div key={stat.label} style={{
              opacity,
              transform: `scale(${scale})`,
              width: 280,
              padding: "32px 24px",
              borderRadius: 20,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              textAlign: "center",
              backdropFilter: "blur(10px)",
            }}>
              <div style={{
                fontSize: 56,
                fontWeight: 800,
                color: stat.color,
                lineHeight: 1,
                marginBottom: 10,
              }}>
                {Math.round(countUp)}{stat.suffix}
              </div>
              <div style={{
                fontSize: 18,
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
