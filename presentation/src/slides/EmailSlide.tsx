import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

export const EmailSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const imageScale = interpolate(frame, [0, 25], [1.05, 1], { extrapolateRight: "clamp" });
  const imageOpacity = interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" });

  // Overlay animations
  const overlayOpacity = interpolate(frame, [40, 55], [0, 1], { extrapolateRight: "clamp" });
  const overlayY = interpolate(frame, [40, 55], [20, 0], { extrapolateRight: "clamp" });
  const badgeScale = interpolate(frame, [60, 80], [0.5, 1], { extrapolateRight: "clamp" });
  const badgeOpacity = interpolate(frame, [60, 75], [0, 1], { extrapolateRight: "clamp" });
  const confBarWidth = interpolate(frame, [75, 110], [0, 94], { extrapolateRight: "clamp" });
  const descOpacity = interpolate(frame, [90, 110], [0, 1], { extrapolateRight: "clamp" });

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

      {/* Right panel - overlay info */}
      <div style={{
        position: "absolute",
        top: 60,
        right: 60,
        width: 380,
        display: "flex",
        flexDirection: "column",
        gap: 24,
      }}>
        {/* Title */}
        <div style={{
          opacity: overlayOpacity,
          transform: `translateY(${overlayY}px)`,
        }}>
          <div style={{ fontSize: 14, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 3, marginBottom: 8 }}>
            Krok 1
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            Email
            <br />
            <span style={{ color: "#3b82f6" }}>přichází</span>
          </div>
        </div>

        {/* New email notification */}
        <div style={{
          opacity: overlayOpacity,
          transform: `translateY(${overlayY}px)`,
          padding: "20px 24px",
          borderRadius: 16,
          background: "rgba(59,130,246,0.08)",
          border: "1px solid rgba(59,130,246,0.2)",
        }}>
          <div style={{ fontSize: 14, color: "#3b82f6", fontWeight: 600, marginBottom: 8 }}>Nový email</div>
          <div style={{ fontSize: 18, color: "#e2e8f0", fontWeight: 600 }}>Poptávka na 50ks koleno DN80</div>
          <div style={{ fontSize: 14, color: "#94a3b8", marginTop: 6 }}>Od: jan.novak@firma.cz</div>
        </div>

        {/* AI Classification badge */}
        <div style={{
          opacity: badgeOpacity,
          transform: `scale(${badgeScale})`,
          padding: "20px 24px",
          borderRadius: 16,
          background: "rgba(168,85,247,0.08)",
          border: "1px solid rgba(168,85,247,0.2)",
        }}>
          <div style={{ fontSize: 14, color: "#a855f7", fontWeight: 600, marginBottom: 10 }}>AI Klasifikace</div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div style={{
              padding: "6px 16px", borderRadius: 20,
              background: "rgba(168,85,247,0.2)", color: "#a855f7",
              fontSize: 16, fontWeight: 700,
            }}>
              poptavka
            </div>
            <span style={{ fontSize: 14, color: "#94a3b8" }}>confidence</span>
          </div>
          {/* Confidence bar */}
          <div style={{
            width: "100%", height: 8, borderRadius: 4,
            background: "rgba(255,255,255,0.06)",
          }}>
            <div style={{
              width: `${confBarWidth}%`, height: "100%", borderRadius: 4,
              background: "linear-gradient(90deg, #a855f7, #22c55e)",
            }} />
          </div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "#22c55e", marginTop: 8, textAlign: "right" }}>
            {Math.round(confBarWidth)}%
          </div>
        </div>

        {/* Description */}
        <div style={{
          opacity: descOpacity,
          fontSize: 16,
          color: "#94a3b8",
          lineHeight: 1.6,
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          AI agent automaticky rozpozná typ zprávy a přiřadí ji k zakázce
        </div>
      </div>
    </AbsoluteFill>
  );
};
