import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const costs = [
  { label: "Materiál", value: 150000, color: "#3b82f6" },
  { label: "Práce", value: 30000, color: "#22c55e" },
  { label: "Kooperace", value: 20000, color: "#f59e0b" },
  { label: "Režie", value: 15000, color: "#a855f7" },
];

export const CalculationSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const imageOpacity = interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" });
  const imageScale = interpolate(frame, [0, 25], [1.05, 1], { extrapolateRight: "clamp" });

  const totalCost = costs.reduce((sum, c) => sum + c.value, 0);
  const margin = 0.2;
  const finalPrice = totalCost * (1 + margin);

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
            infer-forge.hradev.cz/kalkulace
          </div>
        </div>
        <Img
          src={staticFile("pages/17-kalkulace-detail.png")}
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
            Krok 3
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            <span style={{ color: "#f59e0b" }}>Kalkulace</span>
          </div>
        </div>

        {/* Cost bars */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {costs.map((cost, i) => {
            const delay = 25 + i * 12;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const barWidth = interpolate(frame, [delay + 5, delay + 25], [0, (cost.value / totalCost) * 100], { extrapolateRight: "clamp" });
            const countUp = interpolate(frame, [delay + 5, delay + 25], [0, cost.value], { extrapolateRight: "clamp" });

            return (
              <div key={cost.label} style={{ opacity }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: 16, color: "#e2e8f0", fontWeight: 500 }}>{cost.label}</span>
                  <span style={{ fontSize: 16, color: cost.color, fontWeight: 700 }}>
                    {Math.round(countUp).toLocaleString("cs-CZ")} Kč
                  </span>
                </div>
                <div style={{
                  width: "100%", height: 10, borderRadius: 5,
                  background: "rgba(255,255,255,0.06)",
                }}>
                  <div style={{
                    width: `${barWidth}%`, height: "100%", borderRadius: 5,
                    background: cost.color,
                  }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Divider */}
        <div style={{
          height: 1,
          background: "rgba(255,255,255,0.1)",
          margin: "4px 0",
        }} />

        {/* Margin */}
        <div style={{
          opacity: interpolate(frame, [85, 100], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderRadius: 10,
          background: "rgba(34,197,94,0.06)",
          border: "1px solid rgba(34,197,94,0.15)",
        }}>
          <span style={{ fontSize: 16, color: "#94a3b8" }}>Marže 20%</span>
          <span style={{ fontSize: 16, color: "#22c55e", fontWeight: 700 }}>
            {Math.round(interpolate(frame, [90, 110], [0, totalCost * margin], { extrapolateRight: "clamp" })).toLocaleString("cs-CZ")} Kč
          </span>
        </div>

        {/* Total price */}
        <div style={{
          opacity: interpolate(frame, [100, 115], [0, 1], { extrapolateRight: "clamp" }),
          transform: `scale(${interpolate(frame, [100, 115], [0.9, 1], { extrapolateRight: "clamp" })})`,
          padding: "20px 24px",
          borderRadius: 16,
          background: "rgba(239,68,68,0.08)",
          border: "2px solid rgba(239,68,68,0.25)",
          textAlign: "center",
        }}>
          <div style={{ fontSize: 14, color: "#94a3b8", marginBottom: 6 }}>Celková cena</div>
          <div style={{ fontSize: 40, fontWeight: 800, color: "#ef4444" }}>
            {Math.round(interpolate(frame, [105, 125], [0, finalPrice], { extrapolateRight: "clamp" })).toLocaleString("cs-CZ")} Kč
          </div>
        </div>

        {/* Description */}
        <div style={{
          opacity: interpolate(frame, [120, 140], [0, 1], { extrapolateRight: "clamp" }),
          fontSize: 16,
          color: "#94a3b8",
          lineHeight: 1.6,
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          Rozpočet s AI doporučením z podobných zakázek
        </div>
      </div>
    </AbsoluteFill>
  );
};
