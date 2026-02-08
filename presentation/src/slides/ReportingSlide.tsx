import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const tabs = [
  { name: "Prehled", color: "#3b82f6", desc: "KPI metriky a souhrny" },
  { name: "Obrat", color: "#22c55e", desc: "Mesicni a rocni trzby" },
  { name: "Vyroba", color: "#f59e0b", desc: "Vytizenost a efektivita" },
  { name: "Zakaznici", color: "#a855f7", desc: "Top zakaznici, segmentace" },
];

export const ReportingSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const imageOpacity = interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" });
  const imageScale = interpolate(frame, [0, 25], [1.05, 1], { extrapolateRight: "clamp" });

  // Active tab cycles
  const activeTab = Math.floor(interpolate(frame, [40, 160], [0, 3.99], { extrapolateRight: "clamp" }));

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
        top: 60,
        left: 80,
        right: 500,
        bottom: 60,
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
            91.99.126.53:3000/reporting
          </div>
        </div>
        <Img
          src={staticFile("pages/19-reporting-full.png")}
          style={{ width: "100%", height: "calc(100% - 36px)", objectFit: "cover", objectPosition: "top left" }}
        />
      </div>

      {/* Right panel */}
      <div style={{
        position: "absolute",
        top: 60,
        right: 60,
        width: 380,
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}>
        <div>
          <div style={{ fontSize: 14, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 3, marginBottom: 8 }}>
            Analytika
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            Reporting
            <br />
            <span style={{ color: "#3b82f6" }}>a analytika</span>
          </div>
        </div>

        {/* Tab navigation */}
        <div style={{
          opacity: interpolate(frame, [20, 35], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex",
          gap: 6,
          padding: "6px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          {tabs.map((tab, i) => (
            <div key={tab.name} style={{
              flex: 1,
              padding: "8px 6px",
              borderRadius: 8,
              background: activeTab === i ? `${tab.color}15` : "transparent",
              border: activeTab === i ? `1px solid ${tab.color}30` : "1px solid transparent",
              textAlign: "center",
              fontSize: 13,
              color: activeTab === i ? tab.color : "#64748b",
              fontWeight: activeTab === i ? 700 : 500,
            }}>
              {tab.name}
            </div>
          ))}
        </div>

        {/* Active tab details */}
        {tabs.map((tab, i) => (
          <div key={tab.name} style={{
            opacity: activeTab === i ? 1 : 0,
            position: activeTab === i ? "relative" : "absolute",
            padding: "20px 24px",
            borderRadius: 16,
            background: `${tab.color}06`,
            border: `1px solid ${tab.color}20`,
          }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: tab.color, marginBottom: 8 }}>
              {tab.name}
            </div>
            <div style={{ fontSize: 15, color: "#94a3b8", lineHeight: 1.5 }}>
              {tab.desc}
            </div>
          </div>
        ))}

        {/* Mock chart bars */}
        <div style={{
          opacity: interpolate(frame, [50, 65], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex",
          alignItems: "flex-end",
          gap: 8,
          height: 120,
          padding: "20px",
          borderRadius: 16,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          {[60, 45, 80, 55, 70, 90, 65, 75, 85, 50, 95, 40].map((h, i) => {
            const barDelay = 55 + i * 3;
            const barHeight = interpolate(frame, [barDelay, barDelay + 15], [0, h], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                flex: 1,
                height: `${barHeight}%`,
                borderRadius: 4,
                background: i % 2 === 0
                  ? "rgba(59,130,246,0.4)"
                  : "rgba(34,197,94,0.4)",
              }} />
            );
          })}
        </div>

        {/* Description */}
        <div style={{
          opacity: interpolate(frame, [110, 130], [0, 1], { extrapolateRight: "clamp" }),
          fontSize: 16,
          color: "#94a3b8",
          lineHeight: 1.6,
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          Mesicni trendy, top zakaznici, vyrobni vytizeni
        </div>
      </div>
    </AbsoluteFill>
  );
};
