import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const pipelineStages = [
  { label: "Email Ingestion", color: "#64748b", isAI: false },
  { label: "Classification", color: "#a855f7", isAI: true },
  { label: "Routing", color: "#3b82f6", isAI: false },
  { label: "Attachment Processing", color: "#22c55e", isAI: false },
  { label: "Drawing Analysis", color: "#a855f7", isAI: true },
  { label: "Order Creation", color: "#f59e0b", isAI: false },
  { label: "AI Calculation", color: "#a855f7", isAI: true },
  { label: "Offer Generation", color: "#22c55e", isAI: false },
];

const bottomStats = [
  { value: "8", label: "fazi", color: "#3b82f6" },
  { value: "6", label: "AI agentu", color: "#a855f7" },
  { value: "0", label: "manualnich kroku", color: "#22c55e" },
];

export const AutomationSlide: React.FC = () => {
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
        position: "absolute", top: -150, right: -150,
        width: 500, height: 500, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(168,85,247,0.08) 0%, transparent 70%)",
      }} />

      {/* Title */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        fontSize: 48,
        fontWeight: 800,
        color: "#ffffff",
        marginBottom: 80,
        textAlign: "center",
      }}>
        Plne <span style={{ color: "#a855f7" }}>automatizovany</span> pipeline
      </div>

      {/* Pipeline flow - 2 rows of 4 */}
      <div style={{
        display: "flex",
        flexDirection: "column",
        gap: 40,
        marginBottom: 60,
      }}>
        {/* First row */}
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {pipelineStages.slice(0, 4).map((stage, i) => {
            const delay = 25 + i * 15;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const scale = interpolate(frame, [delay, delay + 12], [0.8, 1], { extrapolateRight: "clamp" });
            const arrowOpacity = interpolate(frame, [delay + 8, delay + 15], [0, 1], { extrapolateRight: "clamp" });

            return (
              <div key={stage.label} style={{ display: "flex", alignItems: "center" }}>
                <div style={{
                  opacity,
                  transform: `scale(${scale})`,
                  padding: "20px 28px",
                  borderRadius: 16,
                  background: stage.isAI
                    ? "rgba(168,85,247,0.08)"
                    : "rgba(255,255,255,0.03)",
                  border: stage.isAI
                    ? "2px solid rgba(168,85,247,0.3)"
                    : "1px solid rgba(255,255,255,0.08)",
                  minWidth: 200,
                  textAlign: "center",
                  position: "relative",
                }}>
                  {stage.isAI && (
                    <div style={{
                      position: "absolute",
                      top: -12,
                      right: -12,
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      background: "linear-gradient(135deg, #a855f7 0%, #ec4899 100%)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 16,
                      fontWeight: 800,
                      color: "#ffffff",
                      border: "2px solid #0a0a0a",
                    }}>
                      AI
                    </div>
                  )}
                  <div style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: stage.color,
                    marginBottom: 6,
                  }}>
                    {i + 1}.
                  </div>
                  <div style={{
                    fontSize: 15,
                    color: "#e2e8f0",
                    fontWeight: 600,
                  }}>
                    {stage.label}
                  </div>
                </div>
                {i < 3 && (
                  <div style={{
                    opacity: arrowOpacity,
                    fontSize: 24,
                    color: "#64748b",
                    margin: "0 8px",
                  }}>
                    →
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Arrow down between rows */}
        <div style={{
          opacity: interpolate(frame, [85, 95], [0, 1], { extrapolateRight: "clamp" }),
          alignSelf: "flex-end",
          fontSize: 24,
          color: "#64748b",
          marginRight: 110,
        }}>
          ↓
        </div>

        {/* Second row (reversed) */}
        <div style={{ display: "flex", alignItems: "center", gap: 20, flexDirection: "row-reverse" }}>
          {pipelineStages.slice(4, 8).map((stage, i) => {
            const actualIndex = 7 - i; // Reverse order for display
            const delay = 100 + i * 15;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const scale = interpolate(frame, [delay, delay + 12], [0.8, 1], { extrapolateRight: "clamp" });
            const arrowOpacity = interpolate(frame, [delay + 8, delay + 15], [0, 1], { extrapolateRight: "clamp" });

            return (
              <div key={stage.label} style={{ display: "flex", alignItems: "center" }}>
                <div style={{
                  opacity,
                  transform: `scale(${scale})`,
                  padding: "20px 28px",
                  borderRadius: 16,
                  background: stage.isAI
                    ? "rgba(168,85,247,0.08)"
                    : "rgba(255,255,255,0.03)",
                  border: stage.isAI
                    ? "2px solid rgba(168,85,247,0.3)"
                    : "1px solid rgba(255,255,255,0.08)",
                  minWidth: 200,
                  textAlign: "center",
                  position: "relative",
                }}>
                  {stage.isAI && (
                    <div style={{
                      position: "absolute",
                      top: -12,
                      right: -12,
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      background: "linear-gradient(135deg, #a855f7 0%, #ec4899 100%)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 16,
                      fontWeight: 800,
                      color: "#ffffff",
                      border: "2px solid #0a0a0a",
                    }}>
                      AI
                    </div>
                  )}
                  <div style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: stage.color,
                    marginBottom: 6,
                  }}>
                    {actualIndex + 1}.
                  </div>
                  <div style={{
                    fontSize: 15,
                    color: "#e2e8f0",
                    fontWeight: 600,
                  }}>
                    {stage.label}
                  </div>
                </div>
                {i < 3 && (
                  <div style={{
                    opacity: arrowOpacity,
                    fontSize: 24,
                    color: "#64748b",
                    margin: "0 8px",
                  }}>
                    ←
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom stats */}
      <div style={{
        display: "flex",
        gap: 40,
        marginTop: 40,
      }}>
        {bottomStats.map((stat, i) => {
          const delay = 160 + i * 12;
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
          const scale = interpolate(frame, [delay, delay + 15], [0.85, 1], { extrapolateRight: "clamp" });

          return (
            <div key={stat.label} style={{
              opacity,
              transform: `scale(${scale})`,
              padding: "20px 40px",
              borderRadius: 16,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              textAlign: "center",
              backdropFilter: "blur(10px)",
            }}>
              <div style={{
                fontSize: 48,
                fontWeight: 800,
                color: stat.color,
                lineHeight: 1,
                marginBottom: 8,
              }}>
                {stat.value}
              </div>
              <div style={{
                fontSize: 16,
                color: "#94a3b8",
                fontWeight: 600,
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
