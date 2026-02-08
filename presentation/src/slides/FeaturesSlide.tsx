import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const features = [
  { icon: "📋", text: "Zakazky & Kalkulace" },
  { icon: "🏭", text: "Vyrobni operace" },
  { icon: "📊", text: "Kanban pipeline" },
  { icon: "📧", text: "AI Email klasifikace" },
  { icon: "🔍", text: "RAG podobne zakazky" },
  { icon: "📄", text: "PDF generovani" },
  { icon: "💰", text: "Cenik materialu" },
  { icon: "🤝", text: "Subdodavatele" },
  { icon: "🔔", text: "WebSocket notifikace" },
  { icon: "🏆", text: "Gamifikace" },
  { icon: "🔗", text: "Pohoda XML integrace" },
  { icon: "🔐", text: "AES-256 sifrovani" },
  { icon: "📈", text: "Prometheus metriky" },
  { icon: "📝", text: "Audit trail ISO 9001" },
  { icon: "🔒", text: "RBAC + GDPR" },
  { icon: "📦", text: "BOM export" },
];

export const FeaturesSlide: React.FC = () => {
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
        <span style={{ color: "#ef4444" }}>28+</span> implementovanych funkci
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 16,
        width: "100%",
        maxWidth: 1400,
      }}>
        {features.map((feature, i) => {
          const delay = 10 + i * 4;
          const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
          const scale = interpolate(frame, [delay, delay + 12], [0.8, 1], { extrapolateRight: "clamp" });

          return (
            <div key={feature.text} style={{
              opacity,
              transform: `scale(${scale})`,
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "14px 18px",
              borderRadius: 12,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}>
              <span style={{ fontSize: 24 }}>{feature.icon}</span>
              <span style={{ color: "#e2e8f0", fontSize: 16, fontWeight: 500 }}>
                {feature.text}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
