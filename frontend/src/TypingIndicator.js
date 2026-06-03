// TypingIndicator.js
// Small animation component used to show AI processing/typing state.
// Keep this stateless and purely presentational for reuse in multiple
// chat contexts.
import React from 'react';
import { motion } from 'framer-motion';
import { FaRobot } from 'react-icons/fa';

const TypingIndicator = () => {
  const dotVariants = {
    initial: { y: 0 },
    animate: {
      y: -5,
      transition: {
        yoyo: Infinity,
        duration: 0.4,
      },
    },
  };

  return (
    <div className="flex items-start gap-3">
      <FaRobot className="text-gray-500 mt-2 text-xl" />
      <div className="bg-muted p-3 rounded-lg flex items-center space-x-1 shadow">
        <motion.span variants={dotVariants} initial="initial" animate="animate" className="w-2 h-2 bg-gray-500 rounded-full" />
        <motion.span variants={dotVariants} initial="initial" animate="animate" style={{ animationDelay: '0.2s' }} className="w-2 h-2 bg-gray-500 rounded-full" />
        <motion.span variants={dotVariants} initial="initial" animate="animate" style={{ animationDelay: '0.4s' }} className="w-2 h-2 bg-gray-500 rounded-full" />
      </div>
    </div>
  );
};

export default TypingIndicator;