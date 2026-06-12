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

  const baseClasses = `bg-card-bg border border-border-color rounded-xl shadow-sm flex flex-col overflow-hidden transition-all duration-250 ${paddingClasses[padding]}`;
  const hoverClasses = hoverable ? 'hover:-translate-y-0.5 hover:shadow-md hover:border-border-hover hover:bg-card-hover' : '';

  return (
    <div className={`${baseClasses} ${hoverClasses} ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`flex flex-col gap-2 mb-4 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '', ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={`m-0 text-lg font-semibold text-primary-text tracking-tight ${className}`} {...props}>
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
