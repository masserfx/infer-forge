import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { TitleSlide } from "./slides/TitleSlide";
import { ScreenshotSlide } from "./slides/ScreenshotSlide";
import { StatsSlide } from "./slides/StatsSlide";
import { ArchitectureSlide } from "./slides/ArchitectureSlide";
import { FeaturesSlide } from "./slides/FeaturesSlide";
import { TechStackSlide } from "./slides/TechStackSlide";
import { EndSlide } from "./slides/EndSlide";

const FPS = 30;
const SLIDE_DURATION = 4 * FPS; // 4 seconds per slide
const TRANSITION = 15; // 0.5s transition overlap

const screenshots = [
  { file: "02-dashboard.png", title: "Dashboard", subtitle: "Celkovy prehled zakazek, pipeline a aktivit" },
  { file: "03-zakazky.png", title: "Zakazky", subtitle: "Sprava 8 zakazek s prioritami a terminy" },
  { file: "14-zakazka-detail-top.png", title: "Detail zakazky", subtitle: "Kompletni informace, polozky, kalkulace, operace" },
  { file: "04-kanban.png", title: "Kanban Pipeline", subtitle: "Drag & drop sprava vyrobnich fazi" },
  { file: "05-kalkulace.png", title: "Kalkulace", subtitle: "Material, prace, kooperace, rezie, marze" },
  { file: "17-kalkulace-detail.png", title: "Detail kalkulace", subtitle: "Rozpocet s rozpady nakladu a marzi" },
  { file: "09-materialy.png", title: "Cenik materialu", subtitle: "17 polozek - ocel, trubky, priruby, svar. material" },
  { file: "10-subdodavatele.png", title: "Subdodavatele", subtitle: "NDT, povrchove upravy, CNC, doprava" },
  { file: "08-inbox.png", title: "AI Email Agent", subtitle: "Automaticka klasifikace a prirazeni zprav" },
  { file: "07-reporting.png", title: "Reporting", subtitle: "Trzby, pipeline, vytizenost, PDF export" },
  { file: "06-dokumenty.png", title: "Dokumenty", subtitle: "Verzovani, sifrovani AES-256, kategorie" },
  { file: "11-pohoda.png", title: "Pohoda Integrace", subtitle: "XML synchronizace - nabidky, faktury, sklad" },
  { file: "12-zebricek.png", title: "Gamifikace", subtitle: "Body, zebricek, motivace tymu" },
  { file: "13-nastaveni.png", title: "Nastaveni", subtitle: "Sprava uzivatelu a systemu" },
];

export const InferForgePresentation: React.FC = () => {
  let frame = 0;

  const slides: { from: number; duration: number; element: React.ReactNode }[] = [];

  // Title slide (5s)
  const titleDuration = 5 * FPS;
  slides.push({ from: frame, duration: titleDuration, element: <TitleSlide /> });
  frame += titleDuration - TRANSITION;

  // Architecture (4s)
  slides.push({ from: frame, duration: SLIDE_DURATION, element: <ArchitectureSlide /> });
  frame += SLIDE_DURATION - TRANSITION;

  // Tech stack (4s)
  slides.push({ from: frame, duration: SLIDE_DURATION, element: <TechStackSlide /> });
  frame += SLIDE_DURATION - TRANSITION;

  // Features overview (5s)
  const featuresDuration = 5 * FPS;
  slides.push({ from: frame, duration: featuresDuration, element: <FeaturesSlide /> });
  frame += featuresDuration - TRANSITION;

  // Screenshots
  for (const ss of screenshots) {
    slides.push({
      from: frame,
      duration: SLIDE_DURATION,
      element: (
        <ScreenshotSlide
          imageSrc={staticFile(`pages/${ss.file}`)}
          title={ss.title}
          subtitle={ss.subtitle}
        />
      ),
    });
    frame += SLIDE_DURATION - TRANSITION;
  }

  // Stats (5s)
  const statsDuration = 5 * FPS;
  slides.push({ from: frame, duration: statsDuration, element: <StatsSlide /> });
  frame += statsDuration - TRANSITION;

  // End (4s)
  slides.push({ from: frame, duration: SLIDE_DURATION, element: <EndSlide /> });

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {slides.map((slide, i) => (
        <Sequence key={i} from={slide.from} durationInFrames={slide.duration}>
          {slide.element}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
