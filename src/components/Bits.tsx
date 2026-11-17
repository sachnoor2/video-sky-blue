import React from "react";
import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";
import {theme} from "../theme";

export const Rise: React.FC<{delay?: number; children: React.ReactNode}> = ({delay = 0, children}) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <div style={{opacity: t, transform: `translateY(${(1 - t) * 24}px)`}}>{children}</div>;
};

export const Stage: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill
    style={{
      backgroundColor: theme.ink,
      justifyContent: "center",
      alignItems: "center",
      padding: 64,
    }}
  >
    {children}
  </AbsoluteFill>
);

export const Heading: React.FC<{children: React.ReactNode}> = ({children}) => (
  <h1 style={{color: theme.paper, fontSize: 72, fontWeight: 800, margin: 0, textAlign: "center"}}>
    {children}
  </h1>
);

export const Body: React.FC<{children: React.ReactNode}> = ({children}) => (
  <p style={{color: theme.paper, fontSize: 40, lineHeight: 1.35, textAlign: "center", marginTop: 24}}>
    {children}
  </p>
);
