import React from "react";
import {Composition} from "remotion";
import {Video} from "./Video";
import {manifest} from "./manifest";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Video"
    component={Video}
    durationInFrames={Math.max(manifest.totalFrames, 1)}
    fps={manifest.fps}
    width={720}
    height={1280}
  />
);
