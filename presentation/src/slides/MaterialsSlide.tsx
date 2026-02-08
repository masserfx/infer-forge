import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const materials = [
  { name: "Ocel S235JR", price: "28 500", unit: "Kc/t", trend: "+2.3%" },
  { name: "Trubka DN80", price: "1 240", unit: "Kc/m", trend: "-0.8%" },
  { name: "Priruba DN100", price: "890", unit: "Kc/ks", trend: "+1.1%" },
  { name: "Svar. drat", price: "450", unit: "Kc/kg", trend: "0.0%" },
];

const subcontractors = [
  { name: "NDT Inspekce", color: "#3b82f6" },
  { name: "Tryskani", color: "#f59e0b" },
  { name: "CNC obrabeni", color: "#a855f7" },
  { name: "Doprava", color: "#06b6d4" },
];

export const MaterialsSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        opacity: containerOpacity,
        background: "linear-gradient(160deg, #0a0a0a 0%, #111827 50%, #1e1b4b 100%)",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
        display: "flex",
        padding: "60px 80px",
        gap: 40,
      }}
    >
      {/* Left: Materials */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
        <div>
          <div style={{ fontSize: 14, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 3, marginBottom: 8 }}>
            Databaze
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            Cenik <span style={{ color: "#3b82f6" }}>materialu</span>
          </div>
        </div>

        {/* Screenshot */}
        <div style={{
          opacity: interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" }),
          borderRadius: 16,
          overflow: "hidden",
          boxShadow: "0 15px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.08)",
          height: 350,
        }}>
          <div style={{
            height: 32,
            background: "linear-gradient(180deg, #2a2a3a 0%, #1f1f2e 100%)",
            display: "flex", alignItems: "center", paddingLeft: 12, gap: 6,
          }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5f57" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#febc2e" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#28c840" }} />
          </div>
          <Img
            src={staticFile("pages/09-materialy.png")}
            style={{ width: "100%", height: "calc(100% - 32px)", objectFit: "cover", objectPosition: "top left" }}
          />
        </div>

        {/* Material prices */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {materials.map((mat, i) => {
            const delay = 30 + i * 10;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const trendColor = mat.trend.startsWith("+") ? "#22c55e" : mat.trend.startsWith("-") ? "#ef4444" : "#64748b";
            return (
              <div key={mat.name} style={{
                opacity,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 16px",
                borderRadius: 10,
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.06)",
              }}>
                <span style={{ fontSize: 15, color: "#e2e8f0", fontWeight: 500 }}>{mat.name}</span>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 15, color: "#3b82f6", fontWeight: 700 }}>{mat.price} {mat.unit}</span>
                  <span style={{ fontSize: 12, color: trendColor, fontWeight: 600 }}>{mat.trend}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right: Subcontractors */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
        <div>
          <div style={{ fontSize: 14, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 3, marginBottom: 8 }}>
            Partneri
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            <span style={{ color: "#f59e0b" }}>Subdodavatele</span>
          </div>
        </div>

        {/* Screenshot */}
        <div style={{
          opacity: interpolate(frame, [10, 25], [0, 1], { extrapolateRight: "clamp" }),
          borderRadius: 16,
          overflow: "hidden",
          boxShadow: "0 15px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.08)",
          height: 350,
        }}>
          <div style={{
            height: 32,
            background: "linear-gradient(180deg, #2a2a3a 0%, #1f1f2e 100%)",
            display: "flex", alignItems: "center", paddingLeft: 12, gap: 6,
          }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5f57" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#febc2e" }} />
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#28c840" }} />
          </div>
          <Img
            src={staticFile("pages/10-subdodavatele.png")}
            style={{ width: "100%", height: "calc(100% - 32px)", objectFit: "cover", objectPosition: "top left" }}
          />
        </div>

        {/* Subcontractor cards */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          {subcontractors.map((sub, i) => {
            const delay = 60 + i * 10;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const scale = interpolate(frame, [delay, delay + 12], [0.8, 1], { extrapolateRight: "clamp" });
            return (
              <div key={sub.name} style={{
                opacity,
                transform: `scale(${scale})`,
                padding: "12px 20px",
                borderRadius: 12,
                background: `${sub.color}08`,
                border: `1px solid ${sub.color}25`,
                fontSize: 14,
                color: sub.color,
                fontWeight: 600,
              }}>
                {sub.name}
              </div>
            );
          })}
        </div>

        {/* Description */}
        <div style={{
          opacity: interpolate(frame, [100, 120], [0, 1], { extrapolateRight: "clamp" }),
          fontSize: 16,
          color: "#94a3b8",
          lineHeight: 1.6,
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          Centralni cenik s automatickym vyberem nejlepsi ceny
        </div>
      </div>
    </AbsoluteFill>
  );
};
