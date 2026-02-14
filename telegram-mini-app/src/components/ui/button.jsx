import React from 'react';
import { cn } from '../../lib/utils';

const Button = React.forwardRef(({ 
  className, 
  variant = "default",
  size = "default",
  disabled,
  children,
  ...props 
}, ref) => {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center text-sm font-pixel transition-colors",
        "border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]",
        "active:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] active:translate-x-[2px] active:translate-y-[2px]",
        "disabled:pointer-events-none disabled:opacity-50",
        {
          "bg-[var(--pixel-primary)] text-white": variant === "default",
          "bg-[var(--pixel-destructive)] text-white": variant === "destructive",
          "bg-white text-black": variant === "outline",
          "bg-transparent shadow-none border-none text-[var(--pixel-link)] underline-offset-4 hover:underline": variant === "link",
        },
        {
          "h-9 px-4 py-2": size === "default",
          "h-8 px-3 text-xs": size === "sm",
          "h-10 px-8": size === "lg",
        },
        className
      )}
      ref={ref}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
});

Button.displayName = "Button";

export { Button };