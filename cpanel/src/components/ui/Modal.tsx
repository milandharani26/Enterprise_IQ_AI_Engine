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

export function Modal({ isOpen, onClose, title, description, children, maxWidth = "max-w-md" }: ModalProps) {
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
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-primary-bg/80 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className={`relative w-full ${maxWidth} bg-card-bg border border-border-color rounded-2xl shadow-2xl z-10 m-4 flex flex-col max-h-[90vh]`}>
        <div className="flex items-start justify-between p-6 border-b border-border-color">
          <div>
            <h2 className="m-0 text-xl font-bold text-primary-text">{title}</h2>
            {description && <p className="m-0 mt-1 text-sm text-secondary-text">{description}</p>}
          </div>
          <button 
            onClick={onClose}
            className="text-muted-text hover:text-primary-text transition-colors p-1 -mr-2 -mt-2 rounded-lg hover:bg-tertiary-bg"
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
