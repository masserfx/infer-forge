import { Composition } from "remotion";
import { InferboxPresentation } from "./Presentation";

// Total: 23 slides, 161s total duration, 22 transitions of 0.5s
// = 161*30 - 22*15 = 4830 - 330 = 4500 frames (~150s)
const TOTAL_FRAMES = 4500;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Inferbox"
        component={InferboxPresentation}
        durationInFrames={TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
