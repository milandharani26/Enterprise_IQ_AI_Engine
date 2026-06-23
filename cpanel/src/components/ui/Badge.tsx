import React from 'react';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'outline';
  size?: 'sm' | 'md';
}

export function Badge({ 
  children, 
  variant = 'default', 
  size = 'md',
  className = '', 
  ...props 
}: BadgeProps) {
  const baseClasses = "inline-flex items-center justify-center font-bold rounded-full transition-all duration-300 h-5 uppercase tracking-[0.06em] backdrop-blur-md";
  
  const variantClasses = {
    default: "bg-white/20 dark:bg-white/10 text-primary-text border border-white/30 dark:border-white/10",
    success: "bg-accent-success/15 text-accent-success border border-accent-success/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]",
    warning: "bg-accent-warning/15 text-accent-warning border border-accent-warning/30 shadow-[0_0_10px_rgba(245,158,11,0.2)]",
    danger: "bg-accent-danger/15 text-accent-danger border border-accent-danger/30 shadow-[0_0_10px_rgba(239,68,68,0.2)]",
    outline: "bg-transparent text-secondary-text border border-border-color hover:bg-white/10 dark:hover:bg-white/5",
  };

  const sizeClasses = {
    sm: "px-1.5 text-[10px]",
    md: "px-2 text-[11px]",
  };

  return (
    <span className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`.trim()} {...props}>
      {children}
    </span>
  );
}
