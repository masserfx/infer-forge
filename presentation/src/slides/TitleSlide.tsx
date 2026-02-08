import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const TitleSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const logoScale = interpolate(frame, [0, 30], [0.3, 1], { extrapolateRight: "clamp" });
  const logoOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [20, 50], [60, 0], { extrapolateRight: "clamp" });
  const titleOpacity = interpolate(frame, [20, 45], [0, 1], { extrapolateRight: "clamp" });
  const subtitleOpacity = interpolate(frame, [40, 65], [0, 1], { extrapolateRight: "clamp" });
  const lineWidth = interpolate(frame, [50, 90], [0, 400], { extrapolateRight: "clamp" });
  const badgeOpacity = interpolate(frame, [70, 95], [0, 1], { extrapolateRight: "clamp" });

  // Subtle background gradient animation
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
        fontSize: 28,
        fontWeight: 800,
        letterSpacing: 12,
        color: "#ef4444",
        textTransform: "uppercase",
        marginBottom: 20,
      }}>
        INFER FORGE
      </div>

      {/* Title */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        fontSize: 72,
        fontWeight: 800,
        color: "#ffffff",
        textAlign: "center",
        lineHeight: 1.1,
        maxWidth: 1200,
      }}>
        Automatizacni platforma
        <br />
        <span style={{ color: "#ef4444" }}>pro strojirenstvi</span>
      </div>

      {/* Divider line */}
      <div style={{
        width: lineWidth,
        height: 3,
        background: "linear-gradient(90deg, transparent, #ef4444, transparent)",
        margin: "30px 0",
        borderRadius: 2,
      }} />

      {/* Subtitle */}
      <div style={{
        opacity: subtitleOpacity,
        fontSize: 28,
        color: "#94a3b8",
        textAlign: "center",
        lineHeight: 1.6,
        maxWidth: 900,
      }}>
        Infer s.r.o. — potrubni dily, svarence, ocelove konstrukce
        <br />
        ISO 9001:2016 | ICO: 04856562
      </div>

      {/* Tech badges */}
      <div style={{
        opacity: badgeOpacity,
        display: "flex",
        gap: 16,
        marginTop: 40,
      }}>
        {["Python + FastAPI", "Next.js 16", "PostgreSQL + pgvector", "Claude AI"].map((tech) => (
          <div key={tech} style={{
            padding: "8px 20px",
            borderRadius: 20,
            border: "1px solid rgba(255,255,255,0.15)",
            color: "#cbd5e1",
            fontSize: 16,
            fontWeight: 500,
            background: "rgba(255,255,255,0.05)",
          }}>
            {tech}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
