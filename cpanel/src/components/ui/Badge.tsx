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
  const baseClasses = "inline-flex items-center justify-center font-medium rounded-full transition-colors";
  
  const variantClasses = {
    default: "bg-tertiary-bg text-primary-text",
    success: "bg-accent-success/15 text-accent-success border border-accent-success/30",
    warning: "bg-accent-warning/15 text-accent-warning border border-accent-warning/30",
    danger: "bg-accent-danger/15 text-accent-danger border border-accent-danger/30",
    outline: "bg-transparent text-secondary-text border border-border-color",
  };

  const sizeClasses = {
    sm: "px-2 py-0.5 text-[10px] tracking-wider uppercase",
    md: "px-2.5 py-1 text-xs tracking-wide",
  };

  return (
    <span className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`.trim()} {...props}>
      {children}
    </span>
  );
}
