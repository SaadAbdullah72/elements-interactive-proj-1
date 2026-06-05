import React from 'react';

const AdRotator = ({ page }) => {
  // Map page prop to a static banner image
  let currentAd = "/Banner_01.jpg.jpeg"; // Default
  if (page === "verification") {
    currentAd = "/Banner_01.jpg.jpeg";
  } else if (page === "consultation") {
    currentAd = "/Banner_02.jpg.jpeg";
  } else if (page === "login") {
    currentAd = "/Banner_03.jpg.jpeg";
  }

  return (
    <div className="mt-4 overflow-hidden w-full rounded-2xl border border-gray-100 shadow-sm">
      <a href="#" onClick={e => { e.preventDefault(); console.log('Ad clicked'); }} className="block w-full">
        <img 
          src={currentAd} 
          alt="Advertisement" 
          className="w-full h-[60px] object-cover block rounded-2xl" 
          onError={e => e.target.style.display = 'none'} 
        />
      </a>
    </div>
  );
};

export default AdRotator;
