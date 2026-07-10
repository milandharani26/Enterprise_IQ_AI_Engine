import React, { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon, className = '', ...props }, ref) => {
    return (
      <div className={`flex flex-col gap-1 w-full ${className}`}>
        {label && <label className="text-[13px] font-bold text-secondary-text tracking-tight">{label}</label>}
        <div className="relative flex items-center">
          {icon && (
            <span className="absolute left-3 text-muted-text flex items-center justify-center pointer-events-none">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            className={`w-full py-2 pr-4 bg-card-bg border rounded-[6px] text-primary-text text-[13px] transition-colors duration-75 outline-none
              ${icon ? 'pl-10' : 'pl-4'}
              ${error 
                ? 'border-accent-danger' 
                : 'border-border-color focus:border-accent-primary'
              }
              placeholder:text-muted-text
            `}
            {...props}
          />
        </div>
        {error && <span className="text-[11px] font-medium text-accent-danger">{error}</span>}
      </div>
    );
  }
);

Input.displayName = 'Input';
