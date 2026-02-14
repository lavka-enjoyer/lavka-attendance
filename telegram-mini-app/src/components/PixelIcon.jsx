import React from 'react';

// Pixel art icons using SVG
const PixelIcons = {
  User: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="4" width="4" height="4" fill="currentColor" />
      <rect x="8" y="8" width="8" height="4" fill="currentColor" />
      <rect x="6" y="12" width="12" height="2" fill="currentColor" />
      <rect x="8" y="14" width="8" height="2" fill="currentColor" />
      <rect x="6" y="16" width="12" height="4" fill="currentColor" />
    </svg>
  ),
  Lock: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="4" width="8" height="2" fill="currentColor" />
      <rect x="6" y="6" width="2" height="6" fill="currentColor" />
      <rect x="16" y="6" width="2" height="6" fill="currentColor" />
      <rect x="6" y="12" width="12" height="8" fill="currentColor" />
      <rect x="10" y="14" width="4" height="4" fill="black" />
    </svg>
  ),
  QrCode: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="4" width="6" height="6" fill="currentColor" />
      <rect x="14" y="4" width="6" height="6" fill="currentColor" />
      <rect x="4" y="14" width="6" height="6" fill="currentColor" />
      <rect x="14" y="14" width="6" height="6" fill="currentColor" />
      <rect x="6" y="6" width="2" height="2" fill="white" />
      <rect x="16" y="6" width="2" height="2" fill="white" />
      <rect x="6" y="16" width="2" height="2" fill="white" />
      <rect x="16" y="16" width="2" height="2" fill="white" />
      <rect x="12" y="4" width="1" height="16" fill="currentColor" />
      <rect x="4" y="12" width="16" height="1" fill="currentColor" />
    </svg>
  ),
  CheckCircle2: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="4" width="8" height="2" fill="currentColor" />
      <rect x="6" y="6" width="2" height="2" fill="currentColor" />
      <rect x="16" y="6" width="2" height="2" fill="currentColor" />
      <rect x="4" y="8" width="2" height="8" fill="currentColor" />
      <rect x="18" y="8" width="2" height="8" fill="currentColor" />
      <rect x="6" y="16" width="2" height="2" fill="currentColor" />
      <rect x="16" y="16" width="2" height="2" fill="currentColor" />
      <rect x="8" y="18" width="8" height="2" fill="currentColor" />
      <rect x="10" y="12" width="2" height="2" fill="currentColor" />
      <rect x="12" y="14" width="2" height="2" fill="currentColor" />
      <rect x="14" y="10" width="2" height="2" fill="currentColor" />
    </svg>
  ),
  Loader2: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="4" width="8" height="2" fill="currentColor" />
      <rect x="6" y="6" width="2" height="2" fill="currentColor" />
      <rect x="16" y="6" width="2" height="2" fill="currentColor" />
      <rect x="4" y="8" width="2" height="8" fill="currentColor" />
      <rect x="18" y="8" width="2" height="8" fill="currentColor" />
      <rect x="6" y="16" width="2" height="2" fill="currentColor" />
      <rect x="16" y="16" width="2" height="2" fill="currentColor" />
      <rect x="8" y="18" width="8" height="2" fill="currentColor" />
    </svg>
  ),
  Users: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="6" y="4" width="4" height="4" fill="currentColor" />
      <rect x="14" y="4" width="4" height="4" fill="currentColor" />
      <rect x="4" y="8" width="8" height="2" fill="currentColor" />
      <rect x="12" y="8" width="8" height="2" fill="currentColor" />
      <rect x="2" y="10" width="10" height="2" fill="currentColor" />
      <rect x="12" y="10" width="10" height="2" fill="currentColor" />
      <rect x="4" y="12" width="6" height="2" fill="currentColor" />
      <rect x="14" y="12" width="6" height="2" fill="currentColor" />
      <rect x="2" y="14" width="10" height="4" fill="currentColor" />
      <rect x="12" y="14" width="10" height="4" fill="currentColor" />
    </svg>
  ),
  Warning: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="4" width="4" height="2" fill="currentColor" />
      <rect x="8" y="6" width="8" height="2" fill="currentColor" />
      <rect x="6" y="8" width="12" height="4" fill="currentColor" />
      <rect x="4" y="12" width="16" height="4" fill="currentColor" />
      <rect x="10" y="10" width="4" height="2" fill="black" />
      <rect x="10" y="14" width="4" height="2" fill="black" />
      <rect x="10" y="18" width="4" height="2" fill="currentColor" />
    </svg>
  ),
  ArrowLeft: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="10" width="12" height="4" fill="currentColor" />
      <rect x="6" y="8" width="2" height="2" fill="currentColor" />
      <rect x="6" y="14" width="2" height="2" fill="currentColor" />
      <rect x="4" y="10" width="2" height="4" fill="currentColor" />
    </svg>
  ),
  Check: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="16" y="6" width="2" height="2" fill="currentColor" />
      <rect x="14" y="8" width="2" height="2" fill="currentColor" />
      <rect x="12" y="10" width="2" height="2" fill="currentColor" />
      <rect x="10" y="12" width="2" height="2" fill="currentColor" />
      <rect x="8" y="14" width="2" height="2" fill="currentColor" />
      <rect x="6" y="12" width="2" height="2" fill="currentColor" />
    </svg>
  ),
  Group: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="4" width="4" height="4" fill="currentColor" />
      <rect x="16" y="4" width="4" height="4" fill="currentColor" />
      <rect x="10" y="6" width="4" height="4" fill="currentColor" />
      <rect x="2" y="8" width="6" height="2" fill="currentColor" />
      <rect x="16" y="8" width="6" height="2" fill="currentColor" />
      <rect x="8" y="10" width="8" height="2" fill="currentColor" />
      <rect x="4" y="14" width="16" height="6" fill="currentColor" />
    </svg>
  ),
};

const PixelIcon = ({ icon, className }) => {
  const IconComponent = PixelIcons[icon];
  
  if (!IconComponent) {
    console.error(`Icon '${icon}' not found`);
    return null;
  }
  
  return <IconComponent className={className} />;
};

export default PixelIcon;