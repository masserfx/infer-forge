import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const emailTypes = [
  { type: "Poptavka", color: "#3b82f6", pct: 40 },
  { type: "Objednavka", color: "#22c55e", pct: 25 },
  { type: "Reklamace", color: "#ef4444", pct: 10 },
  { type: "Dotaz", color: "#f59e0b", pct: 15 },
  { type: "Faktura", color: "#a855f7", pct: 10 },
];

const flowSteps = [
  { label: "Email", color: "#64748b" },
  { label: "Claude API", color: "#a855f7" },
  { label: "Klasifikace", color: "#3b82f6" },
  { label: "Prirazeni", color: "#22c55e" },
];

export const AiAgentSlide: React.FC = () => {
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
            91.99.126.53:3000/inbox
          </div>
        </div>
        <Img
          src={staticFile("pages/08-inbox.png")}
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
            AI Engine
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            AI Email
            <br />
            <span style={{ color: "#a855f7" }}>Agent</span>
          </div>
        </div>

        {/* Flowchart */}
        <div style={{
          opacity: interpolate(frame, [20, 35], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "12px 16px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          {flowSteps.map((step, i) => {
            const delay = 25 + i * 10;
            const opacity = interpolate(frame, [delay, delay + 8], [0, 1], { extrapolateRight: "clamp" });
            return (
              <div key={step.label} style={{ display: "flex", alignItems: "center", opacity }}>
                <div style={{
                  padding: "6px 10px",
                  borderRadius: 8,
                  background: `${step.color}15`,
                  border: `1px solid ${step.color}30`,
                  fontSize: 12,
                  color: step.color,
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                }}>
                  {step.label}
                </div>
                {i < flowSteps.length - 1 && (
                  <span style={{ color: "#64748b", margin: "0 4px", fontSize: 12 }}>→</span>
                )}
              </div>
            );
          })}
        </div>

        {/* Email types with confidence bars */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{
            opacity: interpolate(frame, [50, 60], [0, 1], { extrapolateRight: "clamp" }),
            fontSize: 14, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 2,
          }}>
            Typy zprav
          </div>
          {emailTypes.map((et, i) => {
            const delay = 55 + i * 10;
            const opacity = interpolate(frame, [delay, delay + 10], [0, 1], { extrapolateRight: "clamp" });
            const barWidth = interpolate(frame, [delay + 5, delay + 20], [0, et.pct], { extrapolateRight: "clamp" });

            return (
              <div key={et.type} style={{ opacity }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 14, color: "#e2e8f0", fontWeight: 500 }}>{et.type}</span>
                  <span style={{ fontSize: 14, color: et.color, fontWeight: 700 }}>{Math.round(barWidth)}%</span>
                </div>
                <div style={{ width: "100%", height: 6, borderRadius: 3, background: "rgba(255,255,255,0.06)" }}>
                  <div style={{
                    width: `${barWidth}%`, height: "100%", borderRadius: 3,
                    background: et.color,
                  }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Confidence display */}
        <div style={{
          opacity: interpolate(frame, [120, 140], [0, 1], { extrapolateRight: "clamp" }),
          padding: "14px 20px",
          borderRadius: 12,
          background: "rgba(168,85,247,0.06)",
          border: "1px solid rgba(168,85,247,0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}>
          <span style={{ fontSize: 14, color: "#94a3b8" }}>Prumerna presnost</span>
          <span style={{ fontSize: 28, fontWeight: 800, color: "#22c55e" }}>94%</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
