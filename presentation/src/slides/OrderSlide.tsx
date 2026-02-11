import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

export const OrderSlide: React.FC = () => {
  const frame = useCurrentFrame();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const imageOpacity = interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" });
  const imageScale = interpolate(frame, [0, 25], [1.05, 1], { extrapolateRight: "clamp" });

  // Animation: email transforms to order
  const emailX = interpolate(frame, [30, 60], [0, -200], { extrapolateRight: "clamp" });
  const emailOpacity = interpolate(frame, [30, 55], [1, 0], { extrapolateRight: "clamp" });
  const arrowOpacity = interpolate(frame, [40, 55], [0, 1], { extrapolateRight: "clamp" });
  const arrowWidth = interpolate(frame, [40, 60], [0, 80], { extrapolateRight: "clamp" });
  const orderOpacity = interpolate(frame, [50, 70], [0, 1], { extrapolateRight: "clamp" });
  const orderScale = interpolate(frame, [50, 70], [0.8, 1], { extrapolateRight: "clamp" });

  const infoDelay = 80;
  const infoOpacity = interpolate(frame, [infoDelay, infoDelay + 15], [0, 1], { extrapolateRight: "clamp" });

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
            inferbox.hradev.cz/zakazky
          </div>
        </div>
        <Img
          src={staticFile("pages/14-zakazka-detail-top.png")}
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
        {/* Step label */}
        <div>
          <div style={{ fontSize: 14, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 3, marginBottom: 8 }}>
            Krok 2
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            Zakázka
            <br />
            <span style={{ color: "#22c55e" }}>vzniká</span>
          </div>
        </div>

        {/* Email to Order animation */}
        <div style={{
          position: "relative",
          height: 80,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}>
          {/* Email icon */}
          <div style={{
            opacity: emailOpacity,
            transform: `translateX(${emailX}px)`,
            padding: "12px 20px",
            borderRadius: 12,
            background: "rgba(59,130,246,0.1)",
            border: "1px solid rgba(59,130,246,0.2)",
            color: "#3b82f6",
            fontSize: 16,
            fontWeight: 600,
            position: "absolute",
          }}>
            ✉ Email
          </div>

          {/* Arrow */}
          <div style={{
            opacity: arrowOpacity,
            display: "flex",
            alignItems: "center",
          }}>
            <div style={{
              width: arrowWidth,
              height: 3,
              background: "linear-gradient(90deg, #3b82f6, #22c55e)",
              borderRadius: 2,
            }} />
            <div style={{
              width: 0, height: 0,
              borderTop: "8px solid transparent",
              borderBottom: "8px solid transparent",
              borderLeft: "12px solid #22c55e",
            }} />
          </div>

          {/* Order icon */}
          <div style={{
            opacity: orderOpacity,
            transform: `scale(${orderScale})`,
            padding: "12px 20px",
            borderRadius: 12,
            background: "rgba(34,197,94,0.1)",
            border: "1px solid rgba(34,197,94,0.2)",
            color: "#22c55e",
            fontSize: 16,
            fontWeight: 600,
            position: "absolute",
            right: 0,
          }}>
            📋 Zakázka
          </div>
        </div>

        {/* Order details */}
        <div style={{
          opacity: infoOpacity,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}>
          {[
            { label: "Zákazník", value: "Firma ABC s.r.o." },
            { label: "Položky", value: "50ks koleno DN80 PN16" },
            { label: "Priorita", value: "Vysoká" },
            { label: "Termín", value: "15.03.2025" },
          ].map((item, i) => {
            const d = infoDelay + i * 6;
            const o = interpolate(frame, [d, d + 12], [0, 1], { extrapolateRight: "clamp" });
            return (
              <div key={item.label} style={{
                opacity: o,
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 16px",
                borderRadius: 10,
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.06)",
              }}>
                <span style={{ fontSize: 14, color: "#64748b", fontWeight: 500 }}>{item.label}</span>
                <span style={{ fontSize: 14, color: "#e2e8f0", fontWeight: 600 }}>{item.value}</span>
              </div>
            );
          })}
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
          Automatické přiřazení k zákazníkovi podle emailu
        </div>
      </div>
    </AbsoluteFill>
  );
};
