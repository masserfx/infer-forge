import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const docTypes = [
  { type: "Nabidka", tag: "ofr:offer", color: "#3b82f6", icon: "📋" },
  { type: "Objednavka", tag: "ord:order", color: "#f59e0b", icon: "📦" },
  { type: "Faktura", tag: "inv:invoice", color: "#22c55e", icon: "💰" },
];

export const PohodaSlide: React.FC = () => {
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
            91.99.126.53:3000/pohoda
          </div>
        </div>
        <Img
          src={staticFile("pages/11-pohoda.png")}
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
            Krok 8
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            Pohoda
            <br />
            <span style={{ color: "#22c55e" }}>synchronizace</span>
          </div>
        </div>

        {/* XML generation animation */}
        <div style={{
          opacity: interpolate(frame, [20, 35], [0, 1], { extrapolateRight: "clamp" }),
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}>
          <div style={{ fontSize: 13, color: "#64748b", fontWeight: 600, marginBottom: 8 }}>XML Struktura</div>
          <div style={{ fontFamily: "monospace", fontSize: 12, color: "#94a3b8", lineHeight: 1.6 }}>
            <span style={{ color: "#64748b" }}>&lt;</span>
            <span style={{ color: "#3b82f6" }}>dat:dataPack</span>
            <span style={{ color: "#64748b" }}>&gt;</span>
            <br />
            {"  "}<span style={{ color: "#64748b" }}>&lt;</span>
            <span style={{ color: "#22c55e" }}>dat:dataPackItem</span>
            <span style={{ color: "#64748b" }}>&gt;</span>
            <br />
            {"    "}<span style={{ color: "#64748b" }}>&lt;</span>
            <span style={{ color: "#f59e0b" }}>ofr:offer</span>
            <span style={{ color: "#64748b" }}> /&gt;</span>
            <br />
            {"  "}<span style={{ color: "#64748b" }}>&lt;/</span>
            <span style={{ color: "#22c55e" }}>dat:dataPackItem</span>
            <span style={{ color: "#64748b" }}>&gt;</span>
            <br />
            <span style={{ color: "#64748b" }}>&lt;/</span>
            <span style={{ color: "#3b82f6" }}>dat:dataPack</span>
            <span style={{ color: "#64748b" }}>&gt;</span>
          </div>
        </div>

        {/* Document types */}
        {docTypes.map((doc, i) => {
          const delay = 40 + i * 18;
          const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
          const arrowWidth = interpolate(frame, [delay + 8, delay + 20], [0, 60], { extrapolateRight: "clamp" });

          return (
            <div key={doc.type} style={{
              opacity,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}>
              {/* Document card */}
              <div style={{
                flex: 1,
                padding: "14px 18px",
                borderRadius: 12,
                background: `${doc.color}08`,
                border: `1px solid ${doc.color}25`,
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}>
                <span style={{ fontSize: 24 }}>{doc.icon}</span>
                <div>
                  <div style={{ fontSize: 16, color: "#e2e8f0", fontWeight: 600 }}>{doc.type}</div>
                  <div style={{ fontSize: 12, color: doc.color, fontFamily: "monospace" }}>{doc.tag}</div>
                </div>
              </div>

              {/* Arrow to Pohoda */}
              <div style={{ display: "flex", alignItems: "center" }}>
                <div style={{
                  width: arrowWidth,
                  height: 2,
                  background: doc.color,
                  borderRadius: 1,
                }} />
                <div style={{
                  width: 0, height: 0,
                  borderTop: "6px solid transparent",
                  borderBottom: "6px solid transparent",
                  borderLeft: `8px solid ${doc.color}`,
                }} />
              </div>

              {/* Pohoda badge */}
              <div style={{
                padding: "8px 14px",
                borderRadius: 8,
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                fontSize: 12,
                color: "#94a3b8",
                fontWeight: 600,
              }}>
                Pohoda
              </div>
            </div>
          );
        })}

        {/* Technical details */}
        <div style={{
          opacity: interpolate(frame, [110, 130], [0, 1], { extrapolateRight: "clamp" }),
          display: "flex",
          gap: 8,
        }}>
          {["Windows-1250", "XSD 2.0", "lxml"].map((tag) => (
            <div key={tag} style={{
              padding: "6px 14px",
              borderRadius: 8,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              fontSize: 13,
              color: "#94a3b8",
              fontWeight: 500,
            }}>
              {tag}
            </div>
          ))}
        </div>

        {/* Description */}
        <div style={{
          opacity: interpolate(frame, [120, 140], [0, 1], { extrapolateRight: "clamp" }),
          fontSize: 16,
          color: "#94a3b8",
          lineHeight: 1.6,
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          XML export do ucetnictvi — Windows-1250, XSD validace
        </div>
      </div>
    </AbsoluteFill>
  );
};
