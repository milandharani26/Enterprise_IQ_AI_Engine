"use client";

import React, { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { Search, Bell, Moon, Sun } from 'lucide-react';
import { Input } from '../ui/Input';

export function Header() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  const currentTheme = resolvedTheme || theme;

  return (
    <header className="h-[64px] px-6 flex items-center justify-between border-b border-border-color bg-primary-bg sticky top-0 z-30 transition-colors duration-300">
      <div className="w-full max-w-[400px]">
        <Input 
          placeholder="Search..." 
          icon={<Search size={18} />}
          className="m-0"
        />
      </div>
      
      <div className="flex items-center gap-4">
        <button 
          onClick={() => setTheme(currentTheme === 'dark' ? 'light' : 'dark')}
          className="text-secondary-text relative w-9 h-9 flex items-center justify-center rounded-full transition-all duration-150 hover:bg-card-bg hover:text-primary-text outline-none" 
          aria-label="Toggle theme"
        >
          {mounted && currentTheme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>
        <button className="text-secondary-text relative w-9 h-9 flex items-center justify-center rounded-full transition-all duration-150 hover:bg-card-bg hover:text-primary-text outline-none" aria-label="Notifications">
          <Bell size={20} />
          <span className="absolute top-1 right-1 w-4 h-4 bg-accent-danger text-white rounded-full text-[10px] font-bold flex items-center justify-center border-2 border-primary-bg">3</span>
        </button>
      </div>
    </header>
  );
}
