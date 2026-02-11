import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

const leaderboard = [
  { rank: 1, name: "Jan Novák", points: 2450, badge: "🥇" },
  { rank: 2, name: "Petra Svoboda", points: 2180, badge: "🥈" },
  { rank: 3, name: "Martin Král", points: 1950, badge: "🥉" },
  { rank: 4, name: "Eva Machová", points: 1720, badge: "4." },
  { rank: 5, name: "Tomáš Horák", points: 1540, badge: "5." },
];

export const GamificationSlide: React.FC = () => {
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
            inferbox.hradev.cz/trziste-ukolu
          </div>
        </div>
        <Img
          src={staticFile("pages/15-trziste-ukolu.png")}
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
            Motivace
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: "#ffffff", lineHeight: 1.2 }}>
            <span style={{ color: "#f59e0b" }}>Tržiště úkolů</span>
          </div>
        </div>

        {/* Leaderboard */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {leaderboard.map((user, i) => {
            const delay = 20 + i * 10;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
            const x = interpolate(frame, [delay, delay + 12], [30, 0], { extrapolateRight: "clamp" });
            const countUp = interpolate(frame, [delay + 5, delay + 25], [0, user.points], { extrapolateRight: "clamp" });
            const isTop3 = user.rank <= 3;

            return (
              <div key={user.name} style={{
                opacity,
                transform: `translateX(${x}px)`,
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "14px 18px",
                borderRadius: 12,
                background: isTop3 ? "rgba(245,158,11,0.05)" : "rgba(255,255,255,0.03)",
                border: `1px solid ${isTop3 ? "rgba(245,158,11,0.15)" : "rgba(255,255,255,0.06)"}`,
              }}>
                <span style={{ fontSize: 24, width: 36, textAlign: "center" }}>{user.badge}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 16, color: "#e2e8f0", fontWeight: 600 }}>{user.name}</div>
                </div>
                <div style={{
                  fontSize: 18,
                  fontWeight: 800,
                  color: isTop3 ? "#f59e0b" : "#94a3b8",
                }}>
                  {Math.round(countUp)}
                </div>
                <span style={{ fontSize: 12, color: "#64748b" }}>bodů</span>
              </div>
            );
          })}
        </div>

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
          Interní marketplace — úkoly s bodovými odměnami
        </div>
      </div>
    </AbsoluteFill>
  );
};
