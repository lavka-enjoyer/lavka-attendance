import React from 'react';
import { cn } from '../../lib/utils';

const Alert = React.forwardRef(({ className, variant = "default", ...props }, ref) => {
  const variants = {
    default: "bg-white text-black border-black",
    destructive: "bg-[var(--pixel-destructive)] text-white border-black"
  };

  return (
    <div
      ref={ref}
      role="alert"
      className={cn(
        "border-2 p-4",
        "shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]",
        variants[variant],
        className
      )}
      {...props}
    />
  );
});

Alert.displayName = "Alert";

const AlertDescription = React.forwardRef(({ className, ...props }, ref) => (
  <div 
    ref={ref} 
    className={cn("text-sm mt-1 font-pixel", className)}
    {...props} 
  />
));

AlertDescription.displayName = "AlertDescription";

export { Alert, AlertDescription };