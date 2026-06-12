import React, { forwardRef } from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className={`flex flex-col gap-2 w-full ${className}`}>
        {label && <label className="text-sm font-medium text-secondary-text">{label}</label>}
        <textarea
          ref={ref}
          className={`w-full p-3 bg-card-bg border rounded-md text-primary-text text-sm transition-all duration-150 outline-none resize-y min-h-[100px]
            ${error 
              ? 'border-accent-danger focus:ring-2 focus:ring-accent-danger/20' 
              : 'border-border-color focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20'
            }
            placeholder:text-muted-text
          `}
          {...props}
        />
        {error && <span className="text-xs text-accent-danger">{error}</span>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
