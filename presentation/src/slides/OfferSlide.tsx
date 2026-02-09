import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

export const OfferSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const imageOpacity = interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" });
  const imageScale = interpolate(frame, [0, 25], [1.05, 1], { extrapolateRight: "clamp" });

  // Button click animation
  const btnScale = interpolate(frame, [40, 50, 55], [1, 0.95, 1], { extrapolateRight: "clamp" });
  const btnGlow = interpolate(frame, [50, 65], [0, 1], { extrapolateRight: "clamp" });

  // PDF generation animation
  const pdfOpacity = interpolate(frame, [55, 70], [0, 1], { extrapolateRight: "clamp" });
  const pdfScale = interpolate(frame, [55, 70], [0.5, 1], { extrapolateRight: "clamp" });
  const pdfY = interpolate(frame, [70, 100], [0, -20], { extrapolateRight: "clamp" });
  const pdfRotate = interpolate(frame, [70, 100], [0, -5], { extrapolateRight: "clamp" });

  // Envelope animation
  const envOpacity = interpolate(frame, [90, 105], [0, 1], { extrapolateRight: "clamp" });
  const envX = interpolate(frame, [100, 140], [0, 200], { extrapolateRight: "clamp" });
  const envY = interpolate(frame, [100, 140], [0, -100], { extrapolateRight: "clamp" });
  const envScale = interpolate(frame, [100, 140], [1, 0.3], { extrapolateRight: "clamp" });

  const descOpacity = interpolate(frame, [110, 130], [0, 1], { extrapolateRight: "clamp" });

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
            91.99.126.53:3000/zakazky
          </div>
        </div>
        <Img
          src={staticFile("pages/06-dokumenty.png")}
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
            Krok 5
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            Nabídka
            <br />
            <span style={{ color: "#06b6d4" }}>zákazníkovi</span>
          </div>
        </div>

        {/* Generate button */}
        <div style={{
          transform: `scale(${btnScale})`,
          padding: "16px 24px",
          borderRadius: 14,
          background: `rgba(6,182,212,${0.1 + btnGlow * 0.15})`,
          border: `2px solid rgba(6,182,212,${0.2 + btnGlow * 0.3})`,
          textAlign: "center",
          cursor: "pointer",
          boxShadow: btnGlow > 0 ? `0 0 ${20 * btnGlow}px rgba(6,182,212,0.3)` : "none",
        }}>
          <span style={{ fontSize: 18, color: "#06b6d4", fontWeight: 700 }}>
            Generovat PDF nabídku
          </span>
        </div>

        {/* PDF document animation */}
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          position: "relative",
          height: 200,
        }}>
          {/* PDF icon */}
          <div style={{
            opacity: pdfOpacity,
            transform: `scale(${pdfScale}) translateY(${pdfY}px) rotate(${pdfRotate}deg)`,
            width: 160,
            height: 200,
            borderRadius: 12,
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.12)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            position: "absolute",
          }}>
            <div style={{ fontSize: 48, marginBottom: 8 }}>📄</div>
            <div style={{ fontSize: 14, color: "#e2e8f0", fontWeight: 600 }}>Nabídka_2025.pdf</div>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Jinja2 + WeasyPrint</div>
          </div>

          {/* Envelope flying away */}
          <div style={{
            opacity: envOpacity * (1 - interpolate(frame, [130, 140], [0, 1], { extrapolateRight: "clamp" })),
            transform: `translate(${envX}px, ${envY}px) scale(${envScale})`,
            position: "absolute",
            top: 40,
            fontSize: 60,
          }}>
            ✉
          </div>
        </div>

        {/* Pipeline */}
        <div style={{
          opacity: interpolate(frame, [80, 95], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex",
          gap: 8,
        }}>
          {["Jinja2", "WeasyPrint", "PDF"].map((step, i) => (
            <div key={step} style={{
              flex: 1,
              padding: "8px 12px",
              borderRadius: 8,
              background: "rgba(6,182,212,0.08)",
              border: "1px solid rgba(6,182,212,0.15)",
              textAlign: "center",
              fontSize: 13,
              color: "#06b6d4",
              fontWeight: 600,
            }}>
              {step}
              {i < 2 && <span style={{ marginLeft: 8, color: "#64748b" }}>→</span>}
            </div>
          ))}
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
          Jinja2 + WeasyPrint vygeneruje profesionální PDF nabídku
        </div>
      </div>
    </AbsoluteFill>
  );
};
