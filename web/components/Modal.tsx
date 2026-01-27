'use client';

import { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

export default function Modal({ 
  isOpen, 
  onClose, 
  title, 
  children,
  size = 'md',
}: ModalProps) {
  // Handle escape key
  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleEscape]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
  };

  const modalContent = (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      onClick={(e) => {
        // Stop propagation to prevent Terminal's click handler
        e.stopPropagation();
      }}
      onMouseDown={(e) => e.stopPropagation()}
      onMouseUp={(e) => e.stopPropagation()}
    >
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal content */}
      <div 
        className={`relative bg-terminal-surface border border-terminal-border rounded-lg 
                   shadow-xl w-full ${sizeClasses[size]} animate-fade-in`}
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-terminal-border">
            <h2 className="text-lg font-semibold text-terminal-text">{title}</h2>
            <button
              onClick={onClose}
              className="text-terminal-muted hover:text-terminal-text transition-colors p-1"
              aria-label="Close modal"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
        
        {/* Body */}
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  );

  // Use portal to render modal at document body level
  if (typeof window !== 'undefined') {
    return createPortal(modalContent, document.body);
  }
  
  return null;
}

// Reusable modal footer with standard button layout
interface ModalFooterProps {
  children: React.ReactNode;
}

export function ModalFooter({ children }: ModalFooterProps) {
  return (
    <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-terminal-border">
      {children}
    </div>
  );
}

// Reusable modal buttons
interface ModalButtonProps {
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  children: React.ReactNode;
}

export function ModalButton({ 
  onClick, 
  variant = 'secondary', 
  disabled = false,
  children 
}: ModalButtonProps) {
  const variantClasses = {
    primary: 'bg-terminal-accent text-terminal-bg hover:bg-terminal-accent/80',
    secondary: 'text-terminal-muted hover:text-terminal-text',
    danger: 'bg-terminal-error text-white hover:bg-terminal-error/80',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                ${variantClasses[variant]}`}
    >
      {children}
    </button>
  );
}
