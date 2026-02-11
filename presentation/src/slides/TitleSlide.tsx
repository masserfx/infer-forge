import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const TitleSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const logoScale = interpolate(frame, [0, 30], [0.3, 1], { extrapolateRight: "clamp" });
  const logoOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [15, 45], [60, 0], { extrapolateRight: "clamp" });
  const titleOpacity = interpolate(frame, [15, 40], [0, 1], { extrapolateRight: "clamp" });
  const taglineOpacity = interpolate(frame, [40, 60], [0, 1], { extrapolateRight: "clamp" });
  const taglineY = interpolate(frame, [40, 60], [20, 0], { extrapolateRight: "clamp" });
  const lineWidth = interpolate(frame, [55, 90], [0, 500], { extrapolateRight: "clamp" });
  const descOpacity = interpolate(frame, [70, 90], [0, 1], { extrapolateRight: "clamp" });
  const badgeOpacity = interpolate(frame, [90, 115], [0, 1], { extrapolateRight: "clamp" });
  const badgeY = interpolate(frame, [90, 115], [15, 0], { extrapolateRight: "clamp" });

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
        position: "absolute", top: -200, right: -200,
        width: 600, height: 600, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(239,68,68,0.08) 0%, transparent 70%)",
      }} />
      <div style={{
        position: "absolute", bottom: -150, left: -150,
        width: 500, height: 500, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(59,130,246,0.06) 0%, transparent 70%)",
      }} />

      {/* Logo */}
      <div style={{
        opacity: logoOpacity,
        transform: `scale(${logoScale})`,
        fontSize: 32,
        fontWeight: 800,
        letterSpacing: 14,
        color: "#ef4444",
        textTransform: "uppercase",
        marginBottom: 24,
      }}>
        inferbox
      </div>

      {/* Title */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        fontSize: 76,
        fontWeight: 800,
        color: "#ffffff",
        textAlign: "center",
        lineHeight: 1.1,
        maxWidth: 1200,
      }}>
        Od poptávky po fakturaci
        <br />
        <span style={{ color: "#ef4444" }}>— automaticky</span>
      </div>

      {/* Animated tagline */}
      <div style={{
        opacity: taglineOpacity,
        transform: `translateY(${taglineY}px)`,
        fontSize: 30,
        color: "#cbd5e1",
        textAlign: "center",
        marginTop: 20,
        fontWeight: 500,
      }}>
        Automatizační platforma pro strojírenství
      </div>

      {/* Divider line */}
      <div style={{
        width: lineWidth,
        height: 3,
        background: "linear-gradient(90deg, transparent, #ef4444, transparent)",
        margin: "30px 0",
        borderRadius: 2,
      }} />

      {/* Company description */}
      <div style={{
        opacity: descOpacity,
        fontSize: 24,
        color: "#94a3b8",
        textAlign: "center",
        lineHeight: 1.6,
        maxWidth: 900,
      }}>
        Infer s.r.o. — potrubní díly, svařence, ocelové konstrukce, montáže
      </div>

      {/* ISO badge + tech */}
      <div style={{
        opacity: badgeOpacity,
        transform: `translateY(${badgeY}px)`,
        display: "flex",
        gap: 16,
        marginTop: 35,
      }}>
        <div style={{
          padding: "10px 24px",
          borderRadius: 20,
          background: "rgba(239,68,68,0.12)",
          border: "1px solid rgba(239,68,68,0.3)",
          color: "#ef4444",
          fontSize: 16,
          fontWeight: 600,
        }}>
          ISO 9001:2016
        </div>
        <div style={{
          padding: "10px 24px",
          borderRadius: 20,
          border: "1px solid rgba(255,255,255,0.15)",
          color: "#cbd5e1",
          fontSize: 16,
          fontWeight: 500,
          background: "rgba(255,255,255,0.05)",
        }}>
          IČO: 04856562
        </div>
      </div>
    </AbsoluteFill>
  );
};
