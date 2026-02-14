import React from 'react';
import { cn } from "../lib/utils";
import PixelIcon from './PixelIcon';

const PixelCheckbox = React.forwardRef(({
  checked,
  onChange,
  className,
  label,
  ...props
}, ref) => {
  return (
    <div className="flex items-center space-x-2">
      <div 
        className={cn(
          "w-6 h-6 border-2 border-black cursor-pointer flex items-center justify-center transition-colors",
          checked ? "bg-[var(--button-color)]" : "bg-white",
          className
        )}
        onClick={() => onChange && onChange(!checked)}
        {...props}
        ref={ref}
        style={{
          borderColor: 'var(--text-color)',
          backgroundColor: checked ? 'var(--button-color)' : 'var(--bg-color)'
        }}
      >
        {checked && (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="16" y="6" width="2" height="2" fill="var(--button-text-color)" />
            <rect x="14" y="8" width="2" height="2" fill="var(--button-text-color)" />
            <rect x="12" y="10" width="2" height="2" fill="var(--button-text-color)" />
            <rect x="10" y="12" width="2" height="2" fill="var(--button-text-color)" />
            <rect x="8" y="14" width="2" height="2" fill="var(--button-text-color)" />
            <rect x="6" y="12" width="2" height="2" fill="var(--button-text-color)" />
          </svg>
        )}
      </div>
      {label && <span className="text-sm font-pixel" style={{color: 'var(--text-color)'}}>{label}</span>}
    </div>
  );
});

PixelCheckbox.displayName = "PixelCheckbox";

export { PixelCheckbox };