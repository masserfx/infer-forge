import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const monitoringTools = [
  {
    icon: "📊",
    title: "Prometheus",
    desc: "Metrics collection",
    color: "#e74c3c",
    details: "Real-time metriky",
  },
  {
    icon: "📈",
    title: "Grafana",
    desc: "13 dashboards",
    color: "#f39c12",
    details: "Vizualizace dat",
  },
  {
    icon: "🔔",
    title: "AlertManager",
    desc: "Email alerts",
    color: "#ef4444",
    details: "Automatické notifikace",
  },
  {
    icon: "🌸",
    title: "Flower",
    desc: "Celery monitoring",
    color: "#ec4899",
    details: "Task tracking",
  },
  {
    icon: "⚡",
    title: "Circuit Breaker",
    desc: "Self-healing",
    color: "#22c55e",
    details: "Automatická recovery",
  },
  {
    icon: "🔍",
    title: "Correlation ID",
    desc: "Request tracing",
    color: "#06b6d4",
    details: "End-to-end tracking",
  },
];

export const MonitoringSlide: React.FC = () => {
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
        padding: "80px 100px",
      }}
    >
      {/* Decorative circles */}
      <div style={{
        position: "absolute", top: -100, right: -100,
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 70%)",
      }} />

      <div style={{
        position: "absolute", bottom: -150, left: -150,
        width: 500, height: 500, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(34,197,94,0.06) 0%, transparent 70%)",
      }} />

      {/* Title */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        fontSize: 48,
        fontWeight: 800,
        color: "#ffffff",
        marginBottom: 70,
        textAlign: "center",
      }}>
        Enterprise <span style={{ color: "#06b6d4" }}>monitoring</span>
      </div>

      {/* Grid of monitoring tools */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 30,
        maxWidth: 1400,
        width: "100%",
      }}>
        {monitoringTools.map((tool, i) => {
          const delay = 25 + i * 12;
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
          const scale = interpolate(frame, [delay, delay + 15], [0.85, 1], { extrapolateRight: "clamp" });
          const y = interpolate(frame, [delay, delay + 15], [20, 0], { extrapolateRight: "clamp" });

          return (
            <div key={tool.title} style={{
              opacity,
              transform: `scale(${scale}) translateY(${y}px)`,
              padding: "32px 28px",
              borderRadius: 18,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              backdropFilter: "blur(10px)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
              position: "relative",
              overflow: "hidden",
            }}>
              {/* Gradient accent on top */}
              <div style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: 4,
                background: `linear-gradient(90deg, ${tool.color} 0%, transparent 100%)`,
              }} />

              <div style={{ fontSize: 56, marginBottom: 16 }}>{tool.icon}</div>

              <div style={{
                fontSize: 22,
                fontWeight: 800,
                color: tool.color,
                marginBottom: 8,
              }}>
                {tool.title}
              </div>

              <div style={{
                fontSize: 15,
                color: "#94a3b8",
                fontWeight: 600,
                marginBottom: 12,
              }}>
                {tool.desc}
              </div>

              <div style={{
                padding: "8px 16px",
                borderRadius: 8,
                background: `${tool.color}10`,
                border: `1px solid ${tool.color}25`,
                fontSize: 13,
                color: "#e2e8f0",
                fontWeight: 500,
              }}>
                {tool.details}
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom tagline */}
      <div style={{
        opacity: interpolate(frame, [130, 150], [0, 1], { extrapolateRight: "clamp" }),
        marginTop: 50,
        padding: "20px 40px",
        borderRadius: 16,
        background: "rgba(6,182,212,0.06)",
        border: "1px solid rgba(6,182,212,0.15)",
        fontSize: 18,
        color: "#94a3b8",
        textAlign: "center",
        fontWeight: 600,
      }}>
        Proaktivní monitoring s real-time alertingem
      </div>
    </AbsoluteFill>
  );
};
