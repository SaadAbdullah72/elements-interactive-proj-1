import React, { useState } from 'react';

const ADS = [
  "/Banner_01.jpg.jpeg",
  "/Banner_02.jpg.jpeg",
  "/Banner_03.jpg.jpeg"
];

const AdRotator = () => {
  // Choose a random banner once on mount/refresh
  const [currentAd] = useState(() => {
    const randomIndex = Math.floor(Math.random() * ADS.length);
    return ADS[randomIndex];
  });

  return (
    <div className="mt-6 w-full flex justify-center items-center">
      <a 
        href="#" 
        onClick={e => { e.preventDefault(); console.log('Ad clicked'); }} 
        className="block w-full max-w-[420px]"
      >
        <img 
          src={currentAd} 
          alt="Advertisement" 
          className="w-full h-auto object-contain block rounded-2xl shadow-sm border border-gray-100/80 hover:shadow-md transition-all duration-300" 
          onError={e => e.target.style.display = 'none'} 
        />
      </a>
    </div>
  );
};

export default AdRotator;
