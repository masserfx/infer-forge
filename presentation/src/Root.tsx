import { Composition } from "remotion";
import { InferForgePresentation } from "./Presentation";

// Total: 20 slides, 134s total duration, 19 transitions of 0.5s
// = 134*30 - 19*15 = 4020 - 285 = 3735 frames (~124.5s)
const TOTAL_FRAMES = 3750;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="InferForge"
        component={InferForgePresentation}
        durationInFrames={TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
