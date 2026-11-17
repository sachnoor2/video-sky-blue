import React from "react";
import {Body, Heading, Rise, Stage} from "./components/Bits";

// 2D scenes. One component per scene id; only the changed ones belong in a video repo.
export const SCENES: Record<string, React.FC<{dur: number}>> = {
  "01-hook": () => (
    <Stage>
      <Rise>
        <Heading>Ye tire aapko kabhi crush nahi karenge</Heading>
      </Rise>
    </Stage>
  ),
  "02-setup": () => (
    <Stage>
      <Rise delay={6}>
        <Body>Normal tire ke andar hawa hoti hai</Body>
      </Rise>
    </Stage>
  ),
  "03-mechanism": () => (
    <Stage>
      <Rise delay={6}>
        <Body>Andar hawa ki jagah solid blocks</Body>
      </Rise>
    </Stage>
  ),
  "04-twist": () => (
    <Stage>
      <Rise delay={6}>
        <Body>Ye blocks tootte nahi, shape badalte hain</Body>
      </Rise>
    </Stage>
  ),
};
