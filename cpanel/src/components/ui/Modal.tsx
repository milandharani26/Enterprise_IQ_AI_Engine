"use client";

import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  maxWidth?: string;
}

export function Modal({ isOpen, onClose, title, description, children, maxWidth = "max-w-[480px]" }: ModalProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex sm:items-center sm:justify-center items-end justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/20 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className={`relative w-full ${maxWidth} bg-card-bg backdrop-blur-xl border border-border-color sm:rounded-[12px] rounded-t-[12px] shadow-2xl z-10 flex flex-col sm:max-h-[90vh] max-h-[85vh] animate-[slideUp_300ms_cubic-bezier(0.16,1,0.3,1)] sm:animate-none`}>
        <div className="flex items-start justify-between p-6 border-b border-border-color">
          <div>
            <h2 className="m-0 text-[18px] font-bold text-primary-text tracking-tight">{title}</h2>
            {description && <p className="m-0 mt-1 text-[13px] text-secondary-text">{description}</p>}
          </div>
          <button 
            onClick={onClose}
            className="cursor-pointer text-muted-text hover:text-primary-text transition-colors p-1 -mr-2 -mt-2 hover:bg-tertiary-bg"
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
