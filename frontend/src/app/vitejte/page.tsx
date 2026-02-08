"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-provider";

/* ─── Hydration-safe mounted check ──────────────────────────── */

const emptySubscribe = () => () => {};
function useHydrated() {
  return useSyncExternalStore(emptySubscribe, () => true, () => false);
}

/* ─── Animated SVG Icons ──────────────────────────────────────── */

function IconEmail({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="10" width="40" height="28" rx="3" stroke="currentColor" strokeWidth="2.5" />
      <path d="M4 13l20 14 20-14" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
      <circle cx="38" cy="14" r="6" fill="#f97316" className="animate-pulse" />
    </svg>
  );
}

function IconBrain({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M24 6c-4 0-7 2-8.5 5C13 11.5 10 13.5 10 18c0 3 1.5 5.5 3.5 7C12 27 11 30 11 33c0 5 4 9 9 9h1" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M24 6c4 0 7 2 8.5 5C35 11.5 38 13.5 38 18c0 3-1.5 5.5-3.5 7C36 27 37 30 37 33c0 5-4 9-9 9h-1" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M24 6v36" stroke="currentColor" strokeWidth="2" strokeDasharray="3 3" opacity="0.5" />
      <circle cx="20" cy="18" r="2" fill="#8b5cf6" className="animate-pulse" />
      <circle cx="28" cy="18" r="2" fill="#8b5cf6" className="animate-pulse" style={{ animationDelay: "0.3s" }} />
      <circle cx="24" cy="26" r="2" fill="#8b5cf6" className="animate-pulse" style={{ animationDelay: "0.6s" }} />
      <path d="M20 18l4 8m4-8l-4 8" stroke="#8b5cf6" strokeWidth="1.5" opacity="0.6" />
    </svg>
  );
}

function IconDocument({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 6h16l10 10v26a2 2 0 01-2 2H12a2 2 0 01-2-2V8a2 2 0 012-2z" stroke="currentColor" strokeWidth="2.5" />
      <path d="M28 6v10h10" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
      <rect x="16" y="22" width="16" height="2" rx="1" fill="currentColor" opacity="0.4" />
      <rect x="16" y="28" width="12" height="2" rx="1" fill="currentColor" opacity="0.4" />
      <rect x="16" y="34" width="14" height="2" rx="1" fill="currentColor" opacity="0.4" />
      <circle cx="36" cy="36" r="8" fill="#10b981" stroke="white" strokeWidth="2" />
      <path d="M32 36l3 3 5-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconPipeline({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="8" width="12" height="12" rx="3" stroke="currentColor" strokeWidth="2.5" />
      <rect x="18" y="18" width="12" height="12" rx="3" stroke="currentColor" strokeWidth="2.5" />
      <rect x="32" y="28" width="12" height="12" rx="3" stroke="currentColor" strokeWidth="2.5" />
      <path d="M16 14l6 8" stroke="#f97316" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M30 24l6 8" stroke="#f97316" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="10" cy="14" r="3" fill="#3b82f6" className="animate-pulse" />
      <circle cx="24" cy="24" r="3" fill="#f97316" className="animate-pulse" style={{ animationDelay: "0.4s" }} />
      <circle cx="38" cy="34" r="3" fill="#10b981" className="animate-pulse" style={{ animationDelay: "0.8s" }} />
    </svg>
  );
}

function IconCalculator({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="4" width="32" height="40" rx="4" stroke="currentColor" strokeWidth="2.5" />
      <rect x="12" y="9" width="24" height="8" rx="2" fill="currentColor" opacity="0.15" />
      <circle cx="16" cy="25" r="2.5" fill="currentColor" opacity="0.4" />
      <circle cx="24" cy="25" r="2.5" fill="currentColor" opacity="0.4" />
      <circle cx="32" cy="25" r="2.5" fill="#3b82f6" />
      <circle cx="16" cy="33" r="2.5" fill="currentColor" opacity="0.4" />
      <circle cx="24" cy="33" r="2.5" fill="currentColor" opacity="0.4" />
      <circle cx="32" cy="33" r="2.5" fill="#f97316" />
      <rect x="28" y="37" width="8" height="4" rx="2" fill="#10b981" />
    </svg>
  );
}

function IconSync({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 24c0-8.837 7.163-16 16-16 5.5 0 10.3 2.8 13.2 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M40 24c0 8.837-7.163 16-16 16-5.5 0-10.3-2.8-13.2-7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M34 8l4 7h-7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 40l-4-7h7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <text x="17" y="29" fill="currentColor" fontSize="12" fontWeight="bold" fontFamily="monospace">XML</text>
    </svg>
  );
}

function IconShield({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M24 4L6 12v12c0 11 8 18 18 22 10-4 18-11 18-22V12L24 4z" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
      <path d="M18 24l4 4 8-8" stroke="#10b981" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ─── Pipeline Step Animation Component ──────────────────────── */

function PipelineStep({
  icon,
  label,
  sublabel,
  delay,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  sublabel: string;
  delay: number;
  color: string;
}) {
  return (
    <div
      className="flex flex-col items-center gap-2 opacity-0 animate-[fadeSlideUp_0.6s_ease-out_forwards]"
      style={{ animationDelay: `${delay}s` }}
    >
      <div
        className={`relative w-16 h-16 sm:w-20 sm:h-20 rounded-2xl flex items-center justify-center shadow-lg ${color}`}
      >
        {icon}
        <div className="absolute inset-0 rounded-2xl animate-ping opacity-10" style={{ backgroundColor: "currentColor", animationDuration: "3s", animationDelay: `${delay}s` }} />
      </div>
      <span className="text-xs sm:text-sm font-semibold text-white/90 text-center leading-tight">{label}</span>
      <span className="text-[10px] sm:text-xs text-white/50 text-center leading-tight max-w-[90px]">{sublabel}</span>
    </div>
  );
}

function PipelineArrow({ delay }: { delay: number }) {
  return (
    <div
      className="hidden sm:flex items-center opacity-0 animate-[fadeSlideUp_0.4s_ease-out_forwards] mt-[-2rem]"
      style={{ animationDelay: `${delay}s` }}
    >
      <svg width="40" height="20" viewBox="0 0 40 20" fill="none">
        <path d="M0 10h30" stroke="white" strokeWidth="2" strokeDasharray="4 3" opacity="0.3" />
        <path d="M28 5l7 5-7 5" stroke="white" strokeWidth="2" opacity="0.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

/* ─── Spark Particle Effect ───────────────────────────────────── */

const SPARK_POSITIONS = [
  { left: "12%", top: "18%", delay: "0.2s", dur: "3.8s", op: 0.5 },
  { left: "87%", top: "25%", delay: "1.1s", dur: "4.2s", op: 0.7 },
  { left: "34%", top: "72%", delay: "2.3s", dur: "3.5s", op: 0.6 },
  { left: "65%", top: "15%", delay: "0.8s", dur: "5.1s", op: 0.4 },
  { left: "23%", top: "55%", delay: "3.2s", dur: "4.8s", op: 0.8 },
  { left: "78%", top: "68%", delay: "1.5s", dur: "3.2s", op: 0.5 },
  { left: "45%", top: "82%", delay: "0.5s", dur: "4.5s", op: 0.7 },
  { left: "91%", top: "42%", delay: "2.8s", dur: "3.9s", op: 0.6 },
  { left: "8%",  top: "38%", delay: "1.9s", dur: "5.3s", op: 0.4 },
  { left: "56%", top: "28%", delay: "3.6s", dur: "4.1s", op: 0.5 },
  { left: "19%", top: "88%", delay: "0.9s", dur: "3.6s", op: 0.7 },
  { left: "72%", top: "52%", delay: "2.1s", dur: "4.7s", op: 0.6 },
  { left: "41%", top: "35%", delay: "3.4s", dur: "3.3s", op: 0.5 },
  { left: "83%", top: "78%", delay: "0.3s", dur: "5.0s", op: 0.4 },
  { left: "29%", top: "22%", delay: "2.6s", dur: "4.4s", op: 0.8 },
  { left: "62%", top: "62%", delay: "1.7s", dur: "3.7s", op: 0.6 },
  { left: "50%", top: "48%", delay: "3.0s", dur: "4.9s", op: 0.5 },
  { left: "15%", top: "75%", delay: "0.7s", dur: "3.4s", op: 0.7 },
] as const;

const SPARK_COLORS = ["#f97316", "#fbbf24", "#ef4444", "#fb923c"] as const;

function Sparks() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden>
      {SPARK_POSITIONS.map((spark, i) => (
        <div
          key={i}
          className="absolute w-1 h-1 rounded-full animate-[sparkFloat_4s_ease-in-out_infinite]"
          style={{
            left: spark.left,
            top: spark.top,
            backgroundColor: SPARK_COLORS[i % 4],
            animationDelay: spark.delay,
            animationDuration: spark.dur,
            opacity: spark.op,
          }}
        />
      ))}
    </div>
  );
}

/* ─── Stats Counter Animation ─────────────────────────────────── */

function AnimatedStat({ value, suffix, label, delay }: { value: number; suffix: string; label: string; delay: number }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      const duration = 1500;
      const steps = 40;
      const increment = value / steps;
      let current = 0;
      const interval = setInterval(() => {
        current += increment;
        if (current >= value) {
          setCount(value);
          clearInterval(interval);
        } else {
          setCount(Math.floor(current));
        }
      }, duration / steps);
    }, delay * 1000);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className="text-center opacity-0 animate-[fadeSlideUp_0.6s_ease-out_forwards]"
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="text-3xl sm:text-4xl font-bold text-white tabular-nums">
        {count}{suffix}
      </div>
      <div className="text-xs sm:text-sm text-white/60 mt-1">{label}</div>
    </div>
  );
}

/* ─── Main Welcome Page ───────────────────────────────────────── */

export default function WelcomePage() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();
  const mounted = useHydrated();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-orange-500 border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-zinc-950 text-white overflow-x-hidden">
      {/* ── Global Keyframe Styles ── */}
      <style jsx global>{`
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(30px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeSlideDown {
          from { opacity: 0; transform: translateY(-20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes sparkFloat {
          0%, 100% { transform: translateY(0) scale(1); opacity: 0; }
          10% { opacity: 1; }
          50% { transform: translateY(-40px) scale(1.5); opacity: 0.8; }
          90% { opacity: 0.2; }
        }
        @keyframes drawLine {
          from { stroke-dashoffset: 200; }
          to { stroke-dashoffset: 0; }
        }
        @keyframes glowPulse {
          0%, 100% { box-shadow: 0 0 20px rgba(249,115,22,0.1); }
          50% { box-shadow: 0 0 40px rgba(249,115,22,0.25); }
        }
        @keyframes logoReveal {
          0% { opacity: 0; letter-spacing: 0.5em; filter: blur(8px); }
          100% { opacity: 1; letter-spacing: 0.15em; filter: blur(0); }
        }
        @keyframes subtitleReveal {
          0% { opacity: 0; transform: translateY(10px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes borderGlow {
          0%, 100% { border-color: rgba(249,115,22,0.2); }
          50% { border-color: rgba(249,115,22,0.5); }
        }
      `}</style>

      {/* ── HERO SECTION ── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-4 sm:px-8">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(249,115,22,0.08)_0%,transparent_70%)]" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-orange-500/30 to-transparent" />

        <Sparks />

        {/* Forge anvil icon */}
        <div
          className={`mb-6 transition-all duration-1000 ${mounted ? "opacity-100 scale-100" : "opacity-0 scale-75"}`}
        >
          <svg width="72" height="72" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M36 8L12 22v20l24 14 24-14V22L36 8z" stroke="#f97316" strokeWidth="2" fill="none" opacity="0.3" />
            <path d="M36 14L18 25v16l18 11 18-11V25L36 14z" stroke="#f97316" strokeWidth="1.5" fill="rgba(249,115,22,0.05)" />
            <path d="M26 32h20M30 28h12v8H30z" stroke="#f97316" strokeWidth="2" strokeLinejoin="round" />
            <path d="M36 36v10" stroke="#f97316" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M30 46h12" stroke="#f97316" strokeWidth="2.5" strokeLinecap="round" />
            <circle cx="36" cy="30" r="2" fill="#f97316" className="animate-pulse" />
          </svg>
        </div>

        {/* Logo */}
        <h1
          className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-[0.15em] text-white"
          style={{ animation: mounted ? "logoReveal 1.2s ease-out forwards" : "none" }}
        >
          INFER <span className="text-orange-500">FORGE</span>
        </h1>

        {/* Tagline */}
        <p
          className="mt-4 text-lg sm:text-xl text-zinc-400 text-center max-w-xl opacity-0"
          style={{ animation: mounted ? "subtitleReveal 0.8s ease-out 0.6s forwards" : "none" }}
        >
          Automatizační platforma pro strojírenství
        </p>

        {/* Greeting */}
        {user && (
          <p
            className="mt-8 text-sm text-zinc-500 opacity-0"
            style={{ animation: mounted ? "subtitleReveal 0.6s ease-out 1s forwards" : "none" }}
          >
            Vítejte, <span className="text-zinc-300 font-medium">{user.full_name}</span>
          </p>
        )}

        {/* Stats row */}
        <div className="mt-12 grid grid-cols-3 gap-8 sm:gap-16">
          <AnimatedStat value={40} suffix="%" label="Úspora času" delay={1.2} />
          <AnimatedStat value={0} suffix=" tokenů" label="Klasifikace emailu" delay={1.5} />
          <AnimatedStat value={60} suffix="s" label="Email → Zakázka" delay={1.8} />
        </div>

        {/* Scroll hint */}
        <div className="absolute bottom-8 flex flex-col items-center gap-2 opacity-0 animate-[fadeSlideUp_0.6s_ease-out_2.5s_forwards]">
          <span className="text-xs text-zinc-600 uppercase tracking-widest">Posuňte dolů</span>
          <svg width="20" height="28" viewBox="0 0 20 28" fill="none" className="animate-bounce">
            <rect x="1" y="1" width="18" height="26" rx="9" stroke="white" strokeWidth="1.5" opacity="0.2" />
            <circle cx="10" cy="9" r="2" fill="white" opacity="0.4">
              <animate attributeName="cy" values="9;17;9" dur="2s" repeatCount="indefinite" />
            </circle>
          </svg>
        </div>
      </section>

      {/* ── PIPELINE VISUALIZATION ── */}
      <section className="relative py-20 sm:py-32 px-4 sm:px-8">
        <div className="absolute inset-0 bg-gradient-to-b from-zinc-950 via-zinc-900/50 to-zinc-950" />

        <div className="relative max-w-5xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-center mb-4 opacity-0 animate-[fadeSlideUp_0.6s_ease-out_0.2s_forwards]">
            Od emailu k nabídce za <span className="text-orange-500">60 sekund</span>
          </h2>
          <p className="text-zinc-500 text-center mb-16 max-w-xl mx-auto opacity-0 animate-[fadeSlideUp_0.6s_ease-out_0.4s_forwards]">
            Celý proces automaticky. Bez ručního přepisování, bez prodlev.
          </p>

          {/* Pipeline flow */}
          <div className="flex flex-wrap sm:flex-nowrap items-start justify-center gap-4 sm:gap-2">
            <PipelineStep
              icon={<IconEmail className="w-8 h-8 text-white" />}
              label="Email"
              sublabel="IMAP polling"
              delay={0.6}
              color="bg-blue-600/20 border border-blue-500/30"
            />
            <PipelineArrow delay={0.8} />
            <PipelineStep
              icon={<IconBrain className="w-8 h-8 text-white" />}
              label="AI klasifikace"
              sublabel="0 tokenů"
              delay={1.0}
              color="bg-violet-600/20 border border-violet-500/30"
            />
            <PipelineArrow delay={1.2} />
            <PipelineStep
              icon={<IconDocument className="w-8 h-8 text-white" />}
              label="Parsování"
              sublabel="Extrakce dat"
              delay={1.4}
              color="bg-emerald-600/20 border border-emerald-500/30"
            />
            <PipelineArrow delay={1.6} />
            <PipelineStep
              icon={<IconPipeline className="w-8 h-8 text-white" />}
              label="Zakázka"
              sublabel="Auto-vytvoření"
              delay={1.8}
              color="bg-orange-600/20 border border-orange-500/30"
            />
            <PipelineArrow delay={2.0} />
            <PipelineStep
              icon={<IconCalculator className="w-8 h-8 text-white" />}
              label="Kalkulace"
              sublabel="AI odhad ceny"
              delay={2.2}
              color="bg-amber-600/20 border border-amber-500/30"
            />
          </div>
        </div>
      </section>

      {/* ── FEATURE CARDS ── */}
      <section className="relative py-20 sm:py-28 px-4 sm:px-8">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-center mb-4">
            Co pro vás <span className="text-orange-500">INFER FORGE</span> udělá
          </h2>
          <p className="text-zinc-500 text-center mb-16 max-w-lg mx-auto">
            Každý email, každý výkres, každá poptávka — zpracováno automaticky
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Card 1 */}
            <FeatureCard
              icon={<IconBrain className="w-10 h-10 text-violet-400" />}
              title="Inteligentní email"
              description="AI klasifikuje příchozí emaily bez jediného API tokenu. Regex heuristiky rozpoznají poptávky, objednávky i reklamace. Claude přebírá jen složité případy."
              badge="0 tokenů / email"
              badgeColor="bg-violet-500/10 text-violet-400"
              delay={0}
            />
            {/* Card 2 */}
            <FeatureCard
              icon={<IconDocument className="w-10 h-10 text-emerald-400" />}
              title="Generování dokumentů"
              description="Nabídky, průvodky, faktury — generované z dat zakázky do PDF jedním klikem. Šablony v češtině s logem firmy. Export do Pohoda XML."
              badge="PDF + XML"
              badgeColor="bg-emerald-500/10 text-emerald-400"
              delay={0.1}
            />
            {/* Card 3 */}
            <FeatureCard
              icon={<IconPipeline className="w-10 h-10 text-orange-400" />}
              title="Kanban pipeline"
              description="Drag & drop pipeline od poptávky po dokončení. 7 stavů zakázky, automatické přechody, notifikace a gamifikace pro celý tým."
              badge="Drag & Drop"
              badgeColor="bg-orange-500/10 text-orange-400"
              delay={0.2}
            />
            {/* Card 4 */}
            <FeatureCard
              icon={<IconCalculator className="w-10 h-10 text-amber-400" />}
              title="AI kalkulace"
              description="Claude analyzuje požadavky, navrhne materiál, operace a cenu. Kalkulant jen schválí. Podpora BOM, operací, subdodavatelů."
              badge="Anthropic Claude"
              badgeColor="bg-amber-500/10 text-amber-400"
              delay={0.3}
            />
            {/* Card 5 */}
            <FeatureCard
              icon={<IconSync className="w-10 h-10 text-blue-400" />}
              title="Pohoda integrace"
              description="Obousměrná synchronizace se systémem Pohoda. Adresář, nabídky, objednávky, faktury — vše v XML Windows-1250 validované proti XSD."
              badge="Automatická sync"
              badgeColor="bg-blue-500/10 text-blue-400"
              delay={0.4}
            />
            {/* Card 6 */}
            <FeatureCard
              icon={<IconShield className="w-10 h-10 text-zinc-400" />}
              title="On-premise bezpečnost"
              description="Data zákazníků nikdy neopustí vaši síť. AES-256 šifrování dokumentů, RBAC, audit trail, GDPR smazání. ISO 9001 trasovatelnost."
              badge="AES-256"
              badgeColor="bg-zinc-500/10 text-zinc-400"
              delay={0.5}
            />
          </div>
        </div>
      </section>

      {/* ── AUTOMATION SHOWCASE ── */}
      <section className="relative py-20 sm:py-28 px-4 sm:px-8">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom,rgba(249,115,22,0.06)_0%,transparent_60%)]" />

        <div className="relative max-w-4xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-center mb-16">
            Automatizace, která <span className="text-orange-500">pracuje za vás</span>
          </h2>

          <div className="space-y-6">
            <AutomationRow
              step="01"
              title="Příchozí email s výkresem"
              description="Zákazník pošle poptávku s PDF výkresem. Systém stáhne email přes IMAP, uloží přílohy, spustí OCR."
              time="< 2s"
              delay={0}
            />
            <AutomationRow
              step="02"
              title="Heuristická klasifikace"
              description="Regex patterny rozpoznají 'poptáváme', 'cenovou nabídku' → kategorie poptávka s 92% jistotou. Nula tokenů."
              time="< 50ms"
              delay={0.1}
            />
            <AutomationRow
              step="03"
              title="AI extrakce dat"
              description="Claude parsuje email: IČO, kontaktní osobu, požadované položky, termín, materiál. Strukturovaný JSON."
              time="< 2s"
              delay={0.2}
            />
            <AutomationRow
              step="04"
              title="Zákazník + zakázka"
              description="Systém matchne zákazníka dle IČO → email → název. Nenajde? Vytvoří nového. Založí zakázku ORD-XXXXXX."
              time="< 200ms"
              delay={0.3}
            />
            <AutomationRow
              step="05"
              title="Auto-reply zákazníkovi"
              description="Odesílá se potvrzovací email: 'Vaši poptávku jsme přijali, cenovou nabídku zašleme do 2 pracovních dnů.'"
              time="Okamžitě"
              delay={0.4}
            />
          </div>
        </div>
      </section>

      {/* ── CTA SECTION ── */}
      <section className="relative py-24 sm:py-32 px-4 sm:px-8">
        <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-900/30 to-zinc-950" />
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-orange-500/20 to-transparent" />

        <div className="relative max-w-2xl mx-auto text-center">
          <div className="mb-8">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="mx-auto mb-4">
              <path d="M24 4l6 12h12l-10 8 4 12-12-8-12 8 4-12L6 16h12l6-12z" stroke="#f97316" strokeWidth="2" fill="rgba(249,115,22,0.1)" />
            </svg>
          </div>

          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Připraveni začít?
          </h2>
          <p className="text-zinc-500 mb-10 text-lg">
            Podívejte se na 2minutovou video prezentaci, nebo rovnou vstupte do aplikace.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            {/* Primary CTA - Presentation */}
            <Link
              href="/prezentace"
              className="group relative inline-flex items-center gap-3 px-8 py-4 bg-orange-500 hover:bg-orange-400 text-white font-semibold rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(249,115,22,0.3)] hover:scale-[1.02] active:scale-[0.98]"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M5 3l14 9-14 9V3z" fill="currentColor" />
              </svg>
              Zobrazit prezentaci
              <span className="text-orange-200 text-sm">(2 min)</span>
            </Link>

            {/* Secondary CTA - Dashboard */}
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-8 py-4 border border-zinc-700 hover:border-zinc-500 text-zinc-300 hover:text-white font-medium rounded-xl transition-all duration-300 hover:bg-zinc-800/50"
            >
              Přeskočit do aplikace
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="py-8 px-4 text-center">
        <p className="text-xs text-zinc-700">
          INFER FORGE v2.0 &middot; Infer s.r.o. &middot; ISO 9001:2016
        </p>
      </footer>
    </div>
  );
}

/* ─── Feature Card Component ──────────────────────────────────── */

function FeatureCard({
  icon,
  title,
  description,
  badge,
  badgeColor,
  delay,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  badge: string;
  badgeColor: string;
  delay: number;
}) {
  return (
    <div
      className="group relative p-6 rounded-2xl border border-zinc-800 bg-zinc-900/50 hover:border-zinc-700 transition-all duration-500 hover:bg-zinc-900/80 animate-[glowPulse_4s_ease-in-out_infinite]"
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="flex items-start justify-between mb-4">
        {icon}
        <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider ${badgeColor}`}>
          {badge}
        </span>
      </div>
      <h3 className="text-lg font-semibold mb-2 text-white group-hover:text-orange-400 transition-colors">
        {title}
      </h3>
      <p className="text-sm text-zinc-500 leading-relaxed">
        {description}
      </p>
    </div>
  );
}

/* ─── Automation Row Component ────────────────────────────────── */

function AutomationRow({
  step,
  title,
  description,
  time,
  delay,
}: {
  step: string;
  title: string;
  description: string;
  time: string;
  delay: number;
}) {
  return (
    <div
      className="flex items-start gap-4 sm:gap-6 p-4 sm:p-6 rounded-xl border border-zinc-800/50 bg-zinc-900/30 hover:border-orange-500/20 hover:bg-zinc-900/50 transition-all duration-300 opacity-0 animate-[fadeSlideUp_0.6s_ease-out_forwards]"
      style={{ animationDelay: `${delay + 0.5}s` }}
    >
      <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center font-mono text-orange-500 font-bold text-sm">
        {step}
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-semibold text-white mb-1">{title}</h4>
        <p className="text-sm text-zinc-500 leading-relaxed">{description}</p>
      </div>
      <div className="flex-shrink-0 text-xs font-mono text-orange-500/70 bg-orange-500/5 px-3 py-1.5 rounded-lg border border-orange-500/10 whitespace-nowrap hidden sm:block">
        {time}
      </div>
    </div>
  );
}
