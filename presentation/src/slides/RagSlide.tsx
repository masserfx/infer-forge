import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const similarOrders = [
  { name: "ZAK-2024-042", desc: "Koleno DN80 PN16, 30ks", match: 96 },
  { name: "ZAK-2024-018", desc: "Oblouk DN100, 45ks", match: 87 },
  { name: "ZAK-2023-156", desc: "Koleno DN80 PN10, 20ks", match: 82 },
];

export const RagSlide: React.FC = () => {
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
            infer-forge.hradev.cz/zakazky
          </div>
        </div>
        <Img
          src={staticFile("pages/18-zakazka-detail-full.png")}
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
            Krok 4
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            Podobné
            <br />
            <span style={{ color: "#a855f7" }}>zakázky</span>
          </div>
        </div>

        {/* Embedding visualization */}
        <div style={{
          opacity: interpolate(frame, [20, 35], [0, 1], { extrapolateRight: "clamp" }),
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(168,85,247,0.06)",
          border: "1px solid rgba(168,85,247,0.15)",
        }}>
          <div style={{ fontSize: 13, color: "#a855f7", fontWeight: 600, marginBottom: 8 }}>pgvector embedding</div>
          <div style={{ fontSize: 12, color: "#64748b", fontFamily: "monospace" }}>
            [0.234, -0.891, 0.445, 0.123, ...]
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>
            sentence-transformers/multilingual
          </div>
        </div>

        {/* Similar orders cards */}
        {similarOrders.map((order, i) => {
          const delay = 35 + i * 15;
          const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
          const x = interpolate(frame, [delay, delay + 12], [30, 0], { extrapolateRight: "clamp" });
          const matchWidth = interpolate(frame, [delay + 8, delay + 25], [0, order.match], { extrapolateRight: "clamp" });

          return (
            <div key={order.name} style={{
              opacity,
              transform: `translateX(${x}px)`,
              padding: "16px 20px",
              borderRadius: 14,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 16, color: "#e2e8f0", fontWeight: 700 }}>{order.name}</span>
                <span style={{ fontSize: 18, color: "#22c55e", fontWeight: 800 }}>
                  {Math.round(matchWidth)}%
                </span>
              </div>
              <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 10 }}>{order.desc}</div>
              <div style={{ width: "100%", height: 6, borderRadius: 3, background: "rgba(255,255,255,0.06)" }}>
                <div style={{
                  width: `${matchWidth}%`, height: "100%", borderRadius: 3,
                  background: `linear-gradient(90deg, #a855f7, #22c55e)`,
                }} />
              </div>
            </div>
          );
        })}

        {/* Description */}
        <div style={{
          opacity: interpolate(frame, [90, 110], [0, 1], { extrapolateRight: "clamp" }),
          fontSize: 16,
          color: "#94a3b8",
          lineHeight: 1.6,
          padding: "16px 20px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          pgvector embedding nachází historicky podobné projekty
        </div>
      </div>
    </AbsoluteFill>
  );
};
