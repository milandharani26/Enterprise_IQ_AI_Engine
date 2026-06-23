import React, { forwardRef } from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className={`flex flex-col gap-1 w-full ${className}`}>
        {label && <label className="text-[13px] font-bold text-secondary-text tracking-tight">{label}</label>}
        <textarea
          ref={ref}
          className={`w-full p-3 bg-card-bg border rounded-[6px] text-primary-text text-[13px] transition-colors duration-75 outline-none resize-y min-h-[100px]
            ${error 
              ? 'border-accent-danger' 
              : 'border-border-color focus:border-accent-primary'
            }
            placeholder:text-muted-text
          `}
          {...props}
        />
        {error && <span className="text-[11px] font-medium text-accent-danger">{error}</span>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
