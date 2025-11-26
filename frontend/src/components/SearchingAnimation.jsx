import React, { forwardRef } from "react";
import Lottie from "lottie-react";
import searchingAnimation from "../assets/Searching.json";

const SearchingAnimation = forwardRef(({ size = 70, scale = 1.8 }, ref) => {
  return (
    <div
      style={{
        width: size,
        height: size,
        overflow: "visible",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Lottie
        lottieRef={ref}       // ✅ This lets parent control the animation
        animationData={searchingAnimation}
        loop={true}
        autoplay={true}
        style={{
          width: size,
          height: size,
          transform: `scale(${scale}) translate(3px, 1px)`,
          transformOrigin: "center center",
        }}
      />
    </div>
  );
});

export default SearchingAnimation;
