import React from 'react';
import { cn } from '../../lib/utils';

const Input = React.forwardRef(({ className, type = "text", ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        "flex h-9 w-full px-3 py-1 text-sm font-pixel transition-colors",
        "bg-white text-black",
        "border-2 border-black",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium",
        "placeholder:text-gray-500",
        "focus:outline-none focus:ring-2 focus:ring-[var(--pixel-primary)]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      ref={ref}
      {...props}
    />
  );
});

Input.displayName = "Input";

export { Input };