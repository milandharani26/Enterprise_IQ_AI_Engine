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
          <div className="flex flex-col gap-1">
            {label && <span className="text-[13px] font-bold text-primary-text">{label}</span>}
            {description && <span className="text-[11px] text-secondary-text">{description}</span>}
          </div>
        )}
        <label className="relative inline-flex items-center cursor-pointer ml-4 shrink-0">
          <input type="checkbox" className="sr-only peer" ref={ref} {...props} />
          <div className="w-11 h-6 bg-tertiary-bg peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 peer-checked:bg-accent-primary border border-border-color" style={{ transition: 'all 150ms cubic-bezier(0.16, 1, 0.3, 1)' }}></div>
          <div className="absolute top-[2px] left-[2px] bg-white rounded-full h-5 w-5 pointer-events-none peer-checked:translate-x-full shadow-[0_1px_2px_rgba(0,0,0,0.1)]" style={{ transition: 'all 150ms cubic-bezier(0.16, 1, 0.3, 1)' }}></div>
        </label>
      </div>
    );
  }
);

Switch.displayName = 'Switch';
