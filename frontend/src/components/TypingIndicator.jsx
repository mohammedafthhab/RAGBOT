import React from "react";
import Lottie from "lottie-react";
import botThinking from "../assets/bot-thinking.json"; // your file

const TypingIndicator = () => {
  return (
    <div
      style={{
        width: "50px",
        height: "17px",
        margin: "auto",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        opacity: 0.8,
      }}
    >
      <Lottie animationData={botThinking} loop={true} />
    </div>
  );
};

export default TypingIndicator;
