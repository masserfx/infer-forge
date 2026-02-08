import { AbsoluteFill, Sequence } from "remotion";
import { TitleSlide } from "./slides/TitleSlide";
import { ProblemSlide } from "./slides/ProblemSlide";
import { SolutionSlide } from "./slides/SolutionSlide";
import { EmailSlide } from "./slides/EmailSlide";
import { OrderSlide } from "./slides/OrderSlide";
import { CalculationSlide } from "./slides/CalculationSlide";
import { RagSlide } from "./slides/RagSlide";
import { OfferSlide } from "./slides/OfferSlide";
import { KanbanSlide } from "./slides/KanbanSlide";
import { OperationsSlide } from "./slides/OperationsSlide";
import { PohodaSlide } from "./slides/PohodaSlide";
import { AiAgentSlide } from "./slides/AiAgentSlide";
import { DashboardSlide } from "./slides/DashboardSlide";
import { ReportingSlide } from "./slides/ReportingSlide";
import { MaterialsSlide } from "./slides/MaterialsSlide";
import { DocumentsSlide } from "./slides/DocumentsSlide";
import { GamificationSlide } from "./slides/GamificationSlide";
import { SecuritySlide } from "./slides/SecuritySlide";
import { StatsSlide } from "./slides/StatsSlide";
import { EndSlide } from "./slides/EndSlide";

const FPS = 30;
const TRANSITION = 15; // 0.5s transition overlap

// Slide definitions with durations in seconds
const slideConfig: { element: React.ReactNode; durationSec: number }[] = [
  // ACT 1: Uvod (15s)
  { element: <TitleSlide />, durationSec: 5 },
  { element: <ProblemSlide />, durationSec: 5 },
  { element: <SolutionSlide />, durationSec: 5 },

  // ACT 2: Pribeh zakazky (60s)
  { element: <EmailSlide />, durationSec: 8 },
  { element: <OrderSlide />, durationSec: 8 },
  { element: <CalculationSlide />, durationSec: 8 },
  { element: <RagSlide />, durationSec: 6 },
  { element: <OfferSlide />, durationSec: 6 },
  { element: <KanbanSlide />, durationSec: 8 },
  { element: <OperationsSlide />, durationSec: 8 },
  { element: <PohodaSlide />, durationSec: 8 },

  // ACT 3: Inteligentni funkce (35s)
  { element: <AiAgentSlide />, durationSec: 7 },
  { element: <DashboardSlide />, durationSec: 7 },
  { element: <ReportingSlide />, durationSec: 7 },
  { element: <MaterialsSlide />, durationSec: 7 },
  { element: <DocumentsSlide />, durationSec: 7 },

  // ACT 4: Tym a vysledky (20s)
  { element: <GamificationSlide />, durationSec: 5 },
  { element: <SecuritySlide />, durationSec: 5 },
  { element: <StatsSlide />, durationSec: 5 },
  { element: <EndSlide />, durationSec: 5 },
];

export const InferForgePresentation: React.FC = () => {
  let frame = 0;

  const slides: { from: number; duration: number; element: React.ReactNode }[] = [];

  for (let i = 0; i < slideConfig.length; i++) {
    const { element, durationSec } = slideConfig[i];
    const duration = durationSec * FPS;
    slides.push({ from: frame, duration, element });
    // Overlap transition except for the last slide
    frame += duration - (i < slideConfig.length - 1 ? TRANSITION : 0);
  }

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
