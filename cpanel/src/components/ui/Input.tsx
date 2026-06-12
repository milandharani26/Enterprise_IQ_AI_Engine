import React, { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon, className = '', ...props }, ref) => {
    return (
      <div className={`flex flex-col gap-2 w-full ${className}`}>
        {label && <label className="text-sm font-medium text-secondary-text">{label}</label>}
        <div className="relative flex items-center">
          {icon && (
            <span className="absolute left-3 text-muted-text flex items-center justify-center pointer-events-none">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            className={`w-full py-2.5 pr-4 bg-card-bg border rounded-md text-primary-text text-sm transition-all duration-150 outline-none
              ${icon ? 'pl-10' : 'pl-4'}
              ${error 
                ? 'border-accent-danger focus:ring-2 focus:ring-accent-danger/20' 
                : 'border-border-color focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20'
              }
              placeholder:text-muted-text
            `}
            {...props}
          />
        </div>
        {error && <span className="text-xs text-accent-danger">{error}</span>}
      </div>
    );
  }
);

Input.displayName = 'Input';
