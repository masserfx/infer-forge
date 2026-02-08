import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const EndSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp" });
  const scale = interpolate(frame, [0, 25], [0.9, 1], { extrapolateRight: "clamp" });
  const lineWidth = interpolate(frame, [20, 50], [0, 400], { extrapolateRight: "clamp" });
  const urlOpacity = interpolate(frame, [35, 55], [0, 1], { extrapolateRight: "clamp" });
  const urlY = interpolate(frame, [35, 55], [15, 0], { extrapolateRight: "clamp" });
  const ctaOpacity = interpolate(frame, [60, 80], [0, 1], { extrapolateRight: "clamp" });
  const ctaScale = interpolate(frame, [60, 80], [0.9, 1], { extrapolateRight: "clamp" });

  const gradAngle = interpolate(frame, [0, 150], [135, 145]);

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
        position: "absolute", bottom: -100, right: -100,
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(59,130,246,0.06) 0%, transparent 70%)",
      }} />

      <div style={{
        opacity,
        transform: `scale(${scale})`,
        textAlign: "center",
      }}>
        <div style={{
          fontSize: 32,
          fontWeight: 800,
          letterSpacing: 12,
          color: "#ef4444",
          marginBottom: 24,
        }}>
          INFER FORGE
        </div>

        <div style={{
          fontSize: 68,
          fontWeight: 800,
          color: "#ffffff",
          lineHeight: 1.2,
          marginBottom: 10,
        }}>
          Od poptavky po fakturaci
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
          transform: `translateY(${urlY}px)`,
          fontSize: 22,
          color: "#94a3b8",
          marginBottom: 50,
          lineHeight: 1.6,
        }}>
          Kompletni automatizace pro strojirenstvi
          <br />
          Vsechny PRD faze F1–F6 dokonceny
        </div>

        <div style={{
          opacity: urlOpacity,
          transform: `translateY(${urlY}px)`,
          display: "flex",
          gap: 20,
          justifyContent: "center",
          marginBottom: 30,
        }}>
          <div style={{
            padding: "14px 32px",
            borderRadius: 14,
            background: "rgba(239,68,68,0.15)",
            border: "1px solid rgba(239,68,68,0.3)",
            color: "#ef4444",
            fontSize: 20,
            fontWeight: 600,
          }}>
            Demo: 91.99.126.53:3000
          </div>
          <div style={{
            padding: "14px 32px",
            borderRadius: 14,
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.15)",
            color: "#cbd5e1",
            fontSize: 20,
            fontWeight: 600,
          }}>
            github.com/masserfx/infer-forge
          </div>
        </div>

        <div style={{
          opacity: ctaOpacity,
          transform: `scale(${ctaScale})`,
          padding: "16px 40px",
          borderRadius: 16,
          background: "linear-gradient(135deg, rgba(239,68,68,0.2) 0%, rgba(168,85,247,0.2) 100%)",
          border: "1px solid rgba(239,68,68,0.3)",
          color: "#ffffff",
          fontSize: 24,
          fontWeight: 700,
          display: "inline-block",
        }}>
          Pripraveno k nasazeni
        </div>
      </div>
    </AbsoluteFill>
  );
};
