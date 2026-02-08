import { AbsoluteFill, Img, interpolate, useCurrentFrame } from "remotion";

interface Props {
  imageSrc: string;
  title: string;
  subtitle: string;
}

export const ScreenshotSlide: React.FC<Props> = ({ imageSrc, title, subtitle }) => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const imageScale = interpolate(frame, [0, 25], [1.05, 1], { extrapolateRight: "clamp" });
  const imageOpacity = interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleX = interpolate(frame, [10, 30], [-40, 0], { extrapolateRight: "clamp" });
  const titleOpacity = interpolate(frame, [10, 28], [0, 1], { extrapolateRight: "clamp" });
  const subtitleOpacity = interpolate(frame, [20, 38], [0, 1], { extrapolateRight: "clamp" });
  const barWidth = interpolate(frame, [15, 40], [0, 4], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        opacity: containerOpacity,
        background: "linear-gradient(160deg, #0a0a0a 0%, #111827 50%, #1e1b4b 100%)",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      }}
    >
      {/* Screenshot with frame */}
      <div style={{
        position: "absolute",
        top: 95,
        left: 100,
        right: 100,
        bottom: 30,
        opacity: imageOpacity,
        transform: `scale(${imageScale})`,
        borderRadius: 16,
        overflow: "hidden",
        boxShadow: "0 25px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.08)",
      }}>
        {/* Browser chrome bar */}
        <div style={{
          height: 36,
          background: "linear-gradient(180deg, #2a2a3a 0%, #1f1f2e 100%)",
          display: "flex",
          alignItems: "center",
          paddingLeft: 16,
          gap: 8,
          borderBottom: "1px solid rgba(255,255,255,0.05)",
        }}>
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#ff5f57" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#febc2e" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#28c840" }} />
          <div style={{
            marginLeft: 20,
            padding: "4px 80px",
            borderRadius: 6,
            background: "rgba(255,255,255,0.06)",
            color: "#64748b",
            fontSize: 12,
          }}>
            91.99.126.53:3000
          </div>
        </div>
        <Img
          src={imageSrc}
          style={{
            width: "100%",
            height: "calc(100% - 36px)",
            objectFit: "cover",
            objectPosition: "top left",
          }}
        />
      </div>

      {/* Title overlay at top */}
      <div style={{
        position: "absolute",
        top: 20,
        left: 100,
        display: "flex",
        alignItems: "center",
        gap: 16,
        opacity: titleOpacity,
        transform: `translateX(${titleX}px)`,
      }}>
        {/* Red accent bar */}
        <div style={{
          width: barWidth,
          height: 50,
          background: "#ef4444",
          borderRadius: 2,
        }} />
        <div>
          <div style={{
            fontSize: 32,
            fontWeight: 700,
            color: "#ffffff",
            lineHeight: 1.2,
          }}>
            {title}
          </div>
          <div style={{
            opacity: subtitleOpacity,
            fontSize: 18,
            color: "#94a3b8",
            marginTop: 2,
          }}>
            {subtitle}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
