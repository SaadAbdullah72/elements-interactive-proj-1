import React, { useState, useEffect } from 'react';

const ADS = [
  "/Banner_01.jpg.jpeg",
  "/Banner_02.jpg.jpeg",
  "/Banner_03.jpg.jpeg"
];

const AdRotator = ({ page }) => {
  // Determine start index based on the page prop
  const getStartIndex = () => {
    if (page === "verification") return 0;
    if (page === "consultation") return 1;
    return Math.floor(Math.random() * ADS.length);
  };

  const [currentIndex, setCurrentIndex] = useState(getStartIndex());

  useEffect(() => {
    // Reset index if page prop changes
    setCurrentIndex(getStartIndex());
  }, [page]);

  useEffect(() => {
    // Rotate/change the banner every 7 seconds
    const interval = setInterval(() => {
      setCurrentIndex((prevIndex) => (prevIndex + 1) % ADS.length);
    }, 7000);

    return () => clearInterval(interval);
  }, []);

  const currentAd = ADS[currentIndex];

  if (!currentAd) return null;

  return (
    <div className="mt-4 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden w-full flex justify-center items-center">
      <a href="#" onClick={e => { e.preventDefault(); console.log('Ad clicked'); }} className="block w-full">
        <img 
          src={currentAd} 
          alt="Advertisement" 
          className="w-full h-auto max-h-[120px] object-contain block mx-auto rounded-2xl transition-all duration-500" 
          onError={e => e.target.style.display = 'none'} 
        />
      </a>
    </div>
  );
};

export default AdRotator;
