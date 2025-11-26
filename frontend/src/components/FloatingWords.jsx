import React, { useEffect, useRef } from "react";

const FloatingWords = ({
  words = [
    "SEED", "STARTUP", "AI", "INNOVATE", "GROWTH", "FUNDING",
    "VISION", "TEAM", "SCALING", "MVP", "PRODUCT", "STRATEGY"
  ],
  count = 18,
  speed = 0.4,
}) => {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    const wordElements = [];

    // Generate floating words
    for (let i = 0; i < count; i++) {
      const word = document.createElement("div");
      word.className = "floating-word";
      word.innerText = words[Math.floor(Math.random() * words.length)];

      // Random position
      word.style.left = Math.random() * 100 + "%";
      word.style.top = Math.random() * 100 + "%";

      // Random animation duration
      word.style.animationDuration = 8 + Math.random() * 8 + "s";

      // Random delay
      word.style.animationDelay = Math.random() * 5 + "s";

      container.appendChild(word);
      wordElements.push(word);
    }

    return () => {
      wordElements.forEach((el) => el.remove());
    };
  }, [words, count]);

  return <div ref={containerRef} className="floating-words-container"></div>;
};

export default FloatingWords;
