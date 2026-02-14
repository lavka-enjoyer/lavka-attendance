import React from 'react';
import { motion } from 'framer-motion';

const PageTransition = ({ children, className = "" }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.1, ease: "easeOut" }}
      className={`w-full h-full ${className}`}
    >
      {children}
    </motion.div>
  );
};

export default PageTransition;
