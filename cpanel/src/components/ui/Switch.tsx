import React from 'react';

interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  description?: string;
}

export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ label, description, className = '', ...props }, ref) => {
    return (
      <div className={`flex items-center justify-between ${className}`}>
        {(label || description) && (
          <div className="flex flex-col">
            {label && <span className="text-sm font-medium text-primary-text">{label}</span>}
            {description && <span className="text-xs text-secondary-text mt-0.5">{description}</span>}
          </div>
        )}
        <label className="relative inline-flex items-center cursor-pointer ml-4 shrink-0">
          <input type="checkbox" className="sr-only peer" ref={ref} {...props} />
          <div className="w-11 h-6 bg-tertiary-bg peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-accent-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent-primary border border-border-color"></div>
        </label>
      </div>
    );
  }
);

Switch.displayName = 'Switch';
