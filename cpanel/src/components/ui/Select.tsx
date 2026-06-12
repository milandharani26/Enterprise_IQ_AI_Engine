import React, { forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { label: string; value: string }[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, className = '', ...props }, ref) => {
    return (
      <div className={`flex flex-col gap-2 w-full ${className}`}>
        {label && <label className="text-sm font-medium text-secondary-text">{label}</label>}
        <div className="relative flex items-center">
          <select
            ref={ref}
            className={`w-full py-2.5 pl-4 pr-10 bg-card-bg border rounded-md text-primary-text text-sm transition-all duration-150 outline-none appearance-none cursor-pointer
              ${error 
                ? 'border-accent-danger focus:ring-2 focus:ring-accent-danger/20' 
                : 'border-border-color hover:border-border-hover focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20'
              }
            `}
            {...props}
          >
            {options.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <div className="absolute right-3 text-muted-text pointer-events-none">
            <ChevronDown size={16} />
          </div>
        </div>
        {error && <span className="text-xs text-accent-danger">{error}</span>}
      </div>
    );
  }
);

Select.displayName = 'Select';
