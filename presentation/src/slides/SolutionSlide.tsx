import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const flowSteps = [
  { label: "Email", color: "#3b82f6", icon: "✉" },
  { label: "AI Agent", color: "#a855f7", icon: "🤖" },
  { label: "Zakázka", color: "#22c55e", icon: "📋" },
  { label: "Kalkulace", color: "#f59e0b", icon: "🔢" },
  { label: "Výroba", color: "#06b6d4", icon: "⚙" },
  { label: "Fakturace", color: "#ef4444", icon: "📄" },
];

export const SolutionSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 20], [30, 0], { extrapolateRight: "clamp" });
  const subtitleOpacity = interpolate(frame, [15, 35], [0, 1], { extrapolateRight: "clamp" });

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
      {/* Decorative circle */}
      <div style={{
        position: "absolute", top: -100, right: -100,
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(34,197,94,0.06) 0%, transparent 70%)",
      }} />

      {/* Title */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        fontSize: 52,
        fontWeight: 800,
        color: "#ffffff",
        marginBottom: 12,
        textAlign: "center",
      }}>
        Jedna platforma, <span style={{ color: "#22c55e" }}>celý proces</span>
      </div>

      {/* Subtitle */}
      <div style={{
        opacity: subtitleOpacity,
        fontSize: 24,
        color: "#94a3b8",
        marginBottom: 70,
        textAlign: "center",
      }}>
        INFER FORGE automatizuje kompletní životní cyklus zakázky
      </div>

      {/* Flow diagram */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 0,
      }}>
        {flowSteps.map((step, i) => {
          const delay = 25 + i * 15;
          const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
          const scale = interpolate(frame, [delay, delay + 12], [0.7, 1], { extrapolateRight: "clamp" });
          const arrowOpacity = i < flowSteps.length - 1
            ? interpolate(frame, [delay + 8, delay + 18], [0, 1], { extrapolateRight: "clamp" })
            : 0;
          const arrowWidth = i < flowSteps.length - 1
            ? interpolate(frame, [delay + 8, delay + 18], [0, 60], { extrapolateRight: "clamp" })
            : 0;

          return (
            <div key={step.label} style={{ display: "flex", alignItems: "center" }}>
              {/* Step box */}
              <div style={{
                opacity,
                transform: `scale(${scale})`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 12,
                padding: "28px 24px",
                borderRadius: 20,
                background: `${step.color}10`,
                border: `2px solid ${step.color}40`,
                minWidth: 140,
              }}>
                <span style={{ fontSize: 36 }}>{step.icon}</span>
                <span style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: step.color,
                }}>
                  {step.label}
                </span>
              </div>

              {/* Arrow */}
              {i < flowSteps.length - 1 && (
                <div style={{
                  opacity: arrowOpacity,
                  display: "flex",
                  alignItems: "center",
                  margin: "0 4px",
                }}>
                  <div style={{
                    width: arrowWidth,
                    height: 3,
                    background: `linear-gradient(90deg, ${step.color}, ${flowSteps[i + 1].color})`,
                    borderRadius: 2,
                  }} />
                  <div style={{
                    width: 0,
                    height: 0,
                    borderTop: "8px solid transparent",
                    borderBottom: "8px solid transparent",
                    borderLeft: `12px solid ${flowSteps[i + 1].color}`,
                  }} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
