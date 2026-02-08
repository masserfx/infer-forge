import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const problems = [
  { text: "Emaily se ztraceji v inboxu", icon: "✉" },
  { text: "Kalkulace v Excelu, kopirovani rucne", icon: "📊" },
  { text: "Kde je zakazka? Nikdo nevi", icon: "❓" },
  { text: "Pohoda nesynchronizuje", icon: "🔄" },
  { text: "Dokumenty roztrousene vsude", icon: "📁" },
];

const oldTools = ["Excel", "Outlook", "Papir", "Telefon"];

export const ProblemSlide: React.FC = () => {
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
        justifyContent: "center",
        padding: "60px 100px",
      }}
    >
      {/* Title */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        fontSize: 52,
        fontWeight: 800,
        color: "#ffffff",
        marginBottom: 50,
        textAlign: "center",
      }}>
        S cim se <span style={{ color: "#ef4444" }}>potykame</span>?
      </div>

      <div style={{ display: "flex", gap: 80, alignItems: "flex-start" }}>
        {/* Problems list */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
          {problems.map((problem, i) => {
            const delay = 15 + i * 12;
            const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
            const x = interpolate(frame, [delay, delay + 15], [-40, 0], { extrapolateRight: "clamp" });

            return (
              <div key={i} style={{
                opacity,
                transform: `translateX(${x}px)`,
                display: "flex",
                alignItems: "center",
                gap: 20,
                padding: "18px 28px",
                borderRadius: 16,
                background: "rgba(239,68,68,0.06)",
                border: "1px solid rgba(239,68,68,0.15)",
              }}>
                <span style={{ fontSize: 28 }}>{problem.icon}</span>
                <span style={{
                  fontSize: 24,
                  color: "#e2e8f0",
                  fontWeight: 500,
                }}>
                  {problem.text}
                </span>
              </div>
            );
          })}
        </div>

        {/* Old tools - crossed out */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24, alignItems: "center", minWidth: 300 }}>
          <div style={{
            opacity: interpolate(frame, [50, 65], [0, 1], { extrapolateRight: "clamp" }),
            fontSize: 20,
            color: "#64748b",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: 4,
            marginBottom: 10,
          }}>
            Stare nastroje
          </div>
          {oldTools.map((tool, i) => {
            const delay = 60 + i * 10;
            const opacity = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateRight: "clamp" });
            const strikeWidth = interpolate(frame, [delay + 10, delay + 20], [0, 100], { extrapolateRight: "clamp" });

            return (
              <div key={tool} style={{
                opacity,
                position: "relative",
                padding: "14px 40px",
                borderRadius: 12,
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)",
              }}>
                <span style={{
                  fontSize: 26,
                  color: "#94a3b8",
                  fontWeight: 600,
                }}>
                  {tool}
                </span>
                {/* Strikethrough line */}
                <div style={{
                  position: "absolute",
                  top: "50%",
                  left: "10%",
                  width: `${strikeWidth * 0.8}%`,
                  height: 3,
                  background: "#ef4444",
                  borderRadius: 2,
                  transform: "rotate(-5deg)",
                }} />
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
