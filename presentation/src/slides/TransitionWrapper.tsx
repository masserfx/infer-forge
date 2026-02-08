import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

const FADE_FRAMES = 15; // 0.5s at 30fps

export const TransitionWrapper: React.FC<{
  durationInFrames: number;
  children: React.ReactNode;
}> = ({ durationInFrames, children }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(
    frame,
    [0, FADE_FRAMES, durationInFrames - FADE_FRAMES, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return <div style={{ opacity, width: "100%", height: "100%" }}>{children}</div>;
};
