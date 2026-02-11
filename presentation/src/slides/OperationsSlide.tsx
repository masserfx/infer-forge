import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const operations = [
  { name: "Řezání", icon: "✂", color: "#3b82f6", duration: "2h" },
  { name: "Svařování", icon: "⚡", color: "#f59e0b", duration: "4h" },
  { name: "NDT", icon: "🔍", color: "#a855f7", duration: "1h" },
  { name: "Povrch", icon: "🎨", color: "#06b6d4", duration: "2h" },
  { name: "Montáž", icon: "🔧", color: "#22c55e", duration: "3h" },
];

export const OperationsSlide: React.FC = () => {
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
            inferbox.hradev.cz/zakazky
          </div>
        </div>
        <Img
          src={staticFile("pages/16-zakazka-operace.png")}
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
            Krok 7
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            Výrobní
            <br />
            <span style={{ color: "#f59e0b" }}>operace</span>
          </div>
        </div>

        {/* Operations timeline */}
        <div style={{ display: "flex", flexDirection: "column", gap: 0, position: "relative" }}>
          {/* Vertical line */}
          <div style={{
            position: "absolute",
            left: 20,
            top: 20,
            bottom: 20,
            width: 2,
            background: "rgba(255,255,255,0.08)",
          }} />

          {operations.map((op, i) => {
            const delay = 25 + i * 18;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const checkDelay = delay + 15;
            const checkOpacity = interpolate(frame, [checkDelay, checkDelay + 10], [0, 1], { extrapolateRight: "clamp" });
            const checkScale = interpolate(frame, [checkDelay, checkDelay + 10], [0.5, 1], { extrapolateRight: "clamp" });
            const lineProgress = interpolate(frame, [delay, checkDelay], [0, 1], { extrapolateRight: "clamp" });

            return (
              <div key={op.name} style={{
                opacity,
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "14px 0",
              }}>
                {/* Timeline dot / check */}
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: "50%",
                  background: checkOpacity > 0.5
                    ? `${op.color}30`
                    : "rgba(255,255,255,0.06)",
                  border: `2px solid ${checkOpacity > 0.5 ? op.color : "rgba(255,255,255,0.12)"}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 18,
                  zIndex: 1,
                  flexShrink: 0,
                }}>
                  {checkOpacity > 0.5 ? (
                    <span style={{
                      opacity: checkOpacity,
                      transform: `scale(${checkScale})`,
                      color: op.color,
                      fontWeight: 700,
                    }}>
                      ✓
                    </span>
                  ) : (
                    <span>{op.icon}</span>
                  )}
                </div>

                {/* Operation info */}
                <div style={{
                  flex: 1,
                  padding: "10px 16px",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.03)",
                  border: `1px solid ${checkOpacity > 0.5 ? `${op.color}30` : "rgba(255,255,255,0.06)"}`,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}>
                  <span style={{ fontSize: 17, color: "#e2e8f0", fontWeight: 600 }}>{op.name}</span>
                  <span style={{ fontSize: 14, color: op.color, fontWeight: 600 }}>{op.duration}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Description */}
        <div style={{
          opacity: interpolate(frame, [130, 150], [0, 1], { extrapolateRight: "clamp" }),
          fontSize: 16,
          color: "#94a3b8",
          lineHeight: 1.6,
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          Plánování a sledování výrobních kroků
        </div>
      </div>
    </AbsoluteFill>
  );
};
