import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const EndSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp" });
  const scale = interpolate(frame, [0, 25], [0.9, 1], { extrapolateRight: "clamp" });
  const lineWidth = interpolate(frame, [20, 50], [0, 300], { extrapolateRight: "clamp" });
  const urlOpacity = interpolate(frame, [35, 55], [0, 1], { extrapolateRight: "clamp" });

  const gradAngle = interpolate(frame, [0, 120], [135, 145]);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${gradAngle}deg, #0a0a0a 0%, #1a1a2e 40%, #16213e 70%, #0f3460 100%)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      }}
    >
      {/* Decorative circles */}
      <div style={{
        position: "absolute", top: -100, left: -100,
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(239,68,68,0.06) 0%, transparent 70%)",
      }} />

      <div style={{
        opacity,
        transform: `scale(${scale})`,
        textAlign: "center",
      }}>
        <div style={{
          fontSize: 28,
          fontWeight: 800,
          letterSpacing: 10,
          color: "#ef4444",
          marginBottom: 20,
        }}>
          INFER FORGE
        </div>

        <div style={{
          fontSize: 64,
          fontWeight: 800,
          color: "#ffffff",
          lineHeight: 1.2,
          marginBottom: 10,
        }}>
          Pripraveno k nasazeni
        </div>

        <div style={{
          width: lineWidth,
          height: 3,
          background: "linear-gradient(90deg, transparent, #ef4444, transparent)",
          margin: "25px auto",
          borderRadius: 2,
        }} />

        <div style={{
          opacity: urlOpacity,
          fontSize: 24,
          color: "#94a3b8",
          marginBottom: 40,
        }}>
          Vsechny PRD faze F1-F6 kompletni | 557 testu | 11 sluzeb
        </div>

        <div style={{
          opacity: urlOpacity,
          display: "flex",
          gap: 20,
          justifyContent: "center",
        }}>
          <div style={{
            padding: "12px 28px",
            borderRadius: 12,
            background: "rgba(239,68,68,0.15)",
            border: "1px solid rgba(239,68,68,0.3)",
            color: "#ef4444",
            fontSize: 18,
            fontWeight: 600,
          }}>
            91.99.126.53:3000
          </div>
          <div style={{
            padding: "12px 28px",
            borderRadius: 12,
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.15)",
            color: "#cbd5e1",
            fontSize: 18,
            fontWeight: 600,
          }}>
            github.com/masserfx/infer-forge
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
