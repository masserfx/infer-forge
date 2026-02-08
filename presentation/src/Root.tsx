import { Composition } from "remotion";
import { InferForgePresentation } from "./Presentation";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="InferForge"
        component={InferForgePresentation}
        durationInFrames={30 * 75}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
