import raw from "./manifest.json";

export type Scene = {
  id: string;
  seconds: number;
  frames: number;
  caption: string;
  lexicon?: string[];
};

export type Manifest = {
  fps: number;
  pad: number;
  engine: string;
  voice: string;
  totalFrames: number;
  scenes: Scene[];
};

export const manifest = raw as Manifest;
