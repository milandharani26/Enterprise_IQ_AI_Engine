import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
}

export function Button({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  fullWidth = false,
  className = '',
  ...props 
}: ButtonProps) {
  
  const baseClasses = "inline-flex items-center justify-center font-medium rounded-[10px] transition-all duration-300 outline-none disabled:opacity-50 disabled:cursor-not-allowed backdrop-blur-md";
  
  const variantClasses = {
    primary: "bg-accent-primary/80 text-white border border-white/20 shadow-[0_0_15px_rgba(91,106,248,0.4)] hover:bg-accent-primary hover:shadow-[0_0_20px_rgba(91,106,248,0.6)] hover:-translate-y-0.5",
    secondary: "bg-white/20 dark:bg-white/5 text-primary-text border border-white/30 dark:border-white/10 hover:bg-white/30 dark:hover:bg-white/10 hover:shadow-[0_4px_15px_rgba(0,0,0,0.05)]",
    danger: "bg-accent-danger/80 text-white border border-white/20 shadow-[0_0_15px_rgba(239,68,68,0.4)] hover:bg-accent-danger hover:-translate-y-0.5",
    ghost: "bg-transparent text-secondary-text hover:bg-white/20 dark:hover:bg-white/10 hover:text-primary-text"
  };

  const sizeClasses = {
    sm: "h-7 px-3 text-[13px]",
    md: "h-8 px-4 text-[13px]",
    lg: "h-10 px-6 text-sm"
  };

  const widthClass = fullWidth ? "w-full" : "";

  const classes = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${widthClass} ${className}`;

  return (
    <button className={classes.trim()} {...props}>
      {children}
    </button>
  );
}
