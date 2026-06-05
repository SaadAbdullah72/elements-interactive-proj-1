import React, { useState, useEffect } from 'react';

// You can add your webp/jpg banners here
const ADS = [
  "/edited-photo.png",
  "/myimage.png",
  "/myimage.jpeg"
];

const AdRotator = () => {
  const [currentAd, setCurrentAd] = useState('');

  useEffect(() => {
    // Pick a random ad when the component mounts (e.g., when doctor logs in/views page)
    const randomAd = ADS[Math.floor(Math.random() * ADS.length)];
    setCurrentAd(randomAd);
  }, []);

  if (!currentAd) return null;

  return (
    <div className="mt-4 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden w-full h-[48px]">
      <a href="#" onClick={e => { e.preventDefault(); console.log('Ad clicked'); }} className="block w-full h-full">
        {/* The image will span the full width of its container and adjust height automatically */}
        <img 
          src={currentAd} 
          alt="Advertisement" 
          className="w-full h-full object-cover" 
          onError={e => e.target.style.display = 'none'} 
        />
      </a>
    </div>
  );
};

export default AdRotator;
