import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const categories = [
  { name: "Výkres", icon: "📐", color: "#3b82f6" },
  { name: "Atestace", icon: "📜", color: "#22c55e" },
  { name: "WPS", icon: "🔥", color: "#f59e0b" },
  { name: "Průvodka", icon: "📋", color: "#a855f7" },
  { name: "Faktura", icon: "💰", color: "#ef4444" },
];

const ocrSteps = [
  { label: "PDF Upload", color: "#64748b" },
  { label: "Tesseract OCR", color: "#f59e0b" },
  { label: "Fulltext", color: "#22c55e" },
];

export const DocumentsSlide: React.FC = () => {
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
            91.99.126.53:3000/dokumenty
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
            DMS
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            Dokumenty
            <br />
            <span style={{ color: "#06b6d4" }}>+ OCR</span>
          </div>
        </div>

        {/* OCR pipeline */}
        <div style={{
          opacity: interpolate(frame, [20, 35], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "14px 18px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          {ocrSteps.map((step, i) => {
            const delay = 25 + i * 12;
            const opacity = interpolate(frame, [delay, delay + 10], [0, 1], { extrapolateRight: "clamp" });
            return (
              <div key={step.label} style={{ display: "flex", alignItems: "center", opacity }}>
                <div style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  background: `${step.color}15`,
                  border: `1px solid ${step.color}30`,
                  fontSize: 13,
                  color: step.color,
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                }}>
                  {step.label}
                </div>
                {i < ocrSteps.length - 1 && (
                  <span style={{ color: "#64748b", margin: "0 6px", fontSize: 14 }}>→</span>
                )}
              </div>
            );
          })}
        </div>

        {/* Document categories */}
        <div style={{
          opacity: interpolate(frame, [50, 60], [0, 1], { extrapolateRight: "clamp" }),
          fontSize: 14, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 2,
        }}>
          Kategorie dokumentů
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          {categories.map((cat, i) => {
            const delay = 55 + i * 8;
            const opacity = interpolate(frame, [delay, delay + 10], [0, 1], { extrapolateRight: "clamp" });
            const scale = interpolate(frame, [delay, delay + 10], [0.8, 1], { extrapolateRight: "clamp" });
            return (
              <div key={cat.name} style={{
                opacity,
                transform: `scale(${scale})`,
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "10px 16px",
                borderRadius: 10,
                background: `${cat.color}08`,
                border: `1px solid ${cat.color}20`,
              }}>
                <span style={{ fontSize: 18 }}>{cat.icon}</span>
                <span style={{ fontSize: 14, color: cat.color, fontWeight: 600 }}>{cat.name}</span>
              </div>
            );
          })}
        </div>

        {/* Features */}
        <div style={{
          opacity: interpolate(frame, [90, 105], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}>
          {[
            { feat: "Verzování dokumentů", icon: "🔄" },
            { feat: "AES-256 šifrování", icon: "🔒" },
            { feat: "Fulltextové vyhledávání", icon: "🔍" },
          ].map((f, i) => {
            const delay = 95 + i * 8;
            const opacity = interpolate(frame, [delay, delay + 10], [0, 1], { extrapolateRight: "clamp" });
            return (
              <div key={f.feat} style={{
                opacity,
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 14px",
                borderRadius: 8,
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.06)",
              }}>
                <span style={{ fontSize: 16 }}>{f.icon}</span>
                <span style={{ fontSize: 14, color: "#e2e8f0", fontWeight: 500 }}>{f.feat}</span>
              </div>
            );
          })}
        </div>

        {/* Description */}
        <div style={{
          opacity: interpolate(frame, [125, 145], [0, 1], { extrapolateRight: "clamp" }),
          fontSize: 16,
          color: "#94a3b8",
          lineHeight: 1.6,
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          Verzované dokumenty s OCR extrakcí textu
        </div>
      </div>
    </AbsoluteFill>
  );
};
