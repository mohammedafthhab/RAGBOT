import React from "react";
import Lottie from "lottie-react";
import animationData from "../assets/finger.json";

export default function Handscan({ size = 100 }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        overflow: "hidden",
        pointerEvents: "none",
      }}
    >
      <Lottie
        animationData={animationData}
        loop={true}
        style={{
          width: size,
          height: size,
          transform: "scale(1.4)", // ✅ optional zoom
        }}
      />
    </div>
  );
}


