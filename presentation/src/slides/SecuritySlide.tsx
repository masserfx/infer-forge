import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const roles = [
  { role: "Admin", color: "#ef4444", perms: "Plný přístup" },
  { role: "Obchodník", color: "#3b82f6", perms: "Zakázky, nabídky" },
  { role: "Technolog", color: "#22c55e", perms: "Kalkulace, výroba" },
  { role: "Vedení", color: "#a855f7", perms: "Reporting, analýza" },
  { role: "Účetní", color: "#f59e0b", perms: "Pohoda, faktury" },
];

const securityFeatures = [
  { icon: "🔐", title: "AES-256 šifrování", desc: "Dokumenty šifrované at-rest", color: "#3b82f6" },
  { icon: "📋", title: "Audit trail", desc: "ISO 9001 trasovatelnost", color: "#22c55e" },
  { icon: "🛡", title: "GDPR", desc: "Právo na výmaz dat", color: "#a855f7" },
  { icon: "🔑", title: "JWT + bcrypt", desc: "Bezpečná autentizace", color: "#f59e0b" },
];

export const SecuritySlide: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 20], [30, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(160deg, #0a0a0a 0%, #111827 50%, #1e1b4b 100%)",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "60px 100px",
      }}
    >
      {/* Decorative circle */}
      <div style={{
        position: "absolute", bottom: -100, right: -100,
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(168,85,247,0.06) 0%, transparent 70%)",
      }} />

      {/* Title */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        fontSize: 48,
        fontWeight: 800,
        color: "#ffffff",
        marginBottom: 50,
        textAlign: "center",
      }}>
        Bezpečnost a <span style={{ color: "#22c55e" }}>kvalita</span>
      </div>

      <div style={{ display: "flex", gap: 60, width: "100%", maxWidth: 1400 }}>
        {/* Left: RBAC roles */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{
            opacity: interpolate(frame, [15, 28], [0, 1], { extrapolateRight: "clamp" }),
            fontSize: 20,
            fontWeight: 700,
            color: "#ef4444",
            marginBottom: 8,
          }}>
            RBAC Role
          </div>
          {roles.map((r, i) => {
            const delay = 20 + i * 10;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const x = interpolate(frame, [delay, delay + 12], [-30, 0], { extrapolateRight: "clamp" });

            return (
              <div key={r.role} style={{
                opacity,
                transform: `translateX(${x}px)`,
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "16px 20px",
                borderRadius: 12,
                background: `${r.color}06`,
                border: `1px solid ${r.color}20`,
              }}>
                <div style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: r.color,
                  flexShrink: 0,
                }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 18, color: r.color, fontWeight: 700 }}>{r.role}</div>
                  <div style={{ fontSize: 14, color: "#94a3b8" }}>{r.perms}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Security features */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{
            opacity: interpolate(frame, [40, 53], [0, 1], { extrapolateRight: "clamp" }),
            fontSize: 20,
            fontWeight: 700,
            color: "#22c55e",
            marginBottom: 8,
          }}>
            Enterprise bezpečnost
          </div>
          {securityFeatures.map((sf, i) => {
            const delay = 50 + i * 12;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const scale = interpolate(frame, [delay, delay + 12], [0.9, 1], { extrapolateRight: "clamp" });

            return (
              <div key={sf.title} style={{
                opacity,
                transform: `scale(${scale})`,
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "20px 24px",
                borderRadius: 14,
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)",
              }}>
                <span style={{ fontSize: 32 }}>{sf.icon}</span>
                <div>
                  <div style={{ fontSize: 18, color: sf.color, fontWeight: 700 }}>{sf.title}</div>
                  <div style={{ fontSize: 14, color: "#94a3b8" }}>{sf.desc}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom tagline */}
      <div style={{
        opacity: interpolate(frame, [110, 130], [0, 1], { extrapolateRight: "clamp" }),
        marginTop: 40,
        fontSize: 18,
        color: "#94a3b8",
        textAlign: "center",
      }}>
        Enterprise bezpečnost pro citlivá zákaznická data
      </div>
    </AbsoluteFill>
  );
};
