import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hoverable?: boolean;
}

export function Card({ 
  children, 
  padding = 'md', 
  hoverable = false,
  className = '', 
  ...props 
}: CardProps) {
  const paddingClasses = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  };

  const baseClasses = `bg-card-bg backdrop-blur-2xl backdrop-saturate-[180%] border border-border-color rounded-[16px] shadow-[0_4px_24px_rgba(0,0,0,0.02)] flex flex-col overflow-hidden transition-all duration-300 ${paddingClasses[padding]}`;
  const hoverClasses = hoverable ? 'hover:border-border-hover hover:bg-card-hover hover:shadow-[0_12px_40px_rgba(0,0,0,0.08)] hover:-translate-y-1' : '';

  return (
    <div className={`${baseClasses} ${hoverClasses} ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`flex flex-col gap-1 mb-4 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '', ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={`m-0 text-[18px] font-bold text-primary-text tracking-tight ${className}`} {...props}>
      {children}
    </h3>
  );
}

export function CardContent({ children, className = '', ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`flex-1 ${className}`} {...props}>
      {children}
    </div>
  );
}
