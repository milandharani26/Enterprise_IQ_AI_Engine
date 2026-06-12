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
  
  const baseClasses = "inline-flex items-center justify-center font-medium rounded-md transition-all duration-150 outline-none disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variantClasses = {
    primary: "bg-accent-primary text-white hover:bg-accent-primary-hover hover:shadow-[0_0_15px_rgba(59,130,246,0.3)]",
    secondary: "bg-card-bg text-primary-text border border-border-color hover:bg-card-hover hover:border-border-hover",
    danger: "bg-accent-danger text-white hover:brightness-110",
    ghost: "bg-transparent text-secondary-text hover:bg-card-bg hover:text-primary-text"
  };

  const sizeClasses = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base"
  };

  const widthClass = fullWidth ? "w-full" : "";

  const classes = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${widthClass} ${className}`;

  return (
    <button className={classes.trim()} {...props}>
      {children}
    </button>
  );
}
