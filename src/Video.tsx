import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import shotlist from "../shotlist.json";
import {manifest} from "./manifest";
import {theme} from "./theme";

const FrameSeq: React.FC<{start: number; end: number}> = ({start, end}) => {
  const frame = useCurrentFrame();
  const absolute = start + frame;
  // Motion carry: one shared number, so the exit of a shot and the entry of the next agree.
  const drift = interpolate(frame, [0, 6, end - start - 6, end - start], [6, 0, 0, -6], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <Img
        src={staticFile(`out/frame_${String(absolute).padStart(6, "0")}.png`)}
        style={{
          transform: `translateX(${drift}px) scale(${1 + Math.abs(drift) * 0.0006})`,
          filter: Math.abs(drift) > 3 ? `blur(${Math.min(Math.abs(drift) / 6, 4)}px)` : undefined,
        }}
      />
    </AbsoluteFill>
  );
};

const Captions: React.FC = () => {
  const frame = useCurrentFrame();
  let at = 0;
  for (const scene of manifest.scenes) {
    const end = at + scene.frames;
    if (frame >= at && frame < end && scene.caption) {
      return (
        <AbsoluteFill style={{justifyContent: "flex-end", alignItems: "center", paddingBottom: "18%"}}>
          <div style={theme.caption}>{scene.caption}</div>
        </AbsoluteFill>
      );
    }
    at = end;
  }
  return null;
};

export const Video: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: theme.ink}}>
    {shotlist.shots.map((shot) => (
      <Sequence
        key={shot.id}
        from={shot.start}
        durationInFrames={shot.end - shot.start + 1}
        name={shot.id}
      >
        <FrameSeq start={shot.start} end={shot.end} />
      </Sequence>
    ))}

    {manifest.scenes.map((scene, i) => {
      const from = manifest.scenes.slice(0, i).reduce((a, s) => a + s.frames, 0);
      return (
        <Sequence key={scene.id} from={from} durationInFrames={scene.frames} name={`audio-${scene.id}`}>
          <Audio src={staticFile(`audio/${scene.id}.wav`)} />
        </Sequence>
      );
    })}

    <Captions />
  </AbsoluteFill>
);
