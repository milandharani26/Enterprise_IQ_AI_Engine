"use client";

import React, { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { Moon, Sun, ArrowLeftRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '../ui/Button';

export function Header() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  // Avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  const currentTheme = resolvedTheme || theme;

  return (
    <header className="h-[64px] px-6 flex items-center justify-end border-b border-border-color bg-primary-bg sticky top-0 z-30 transition-colors duration-300">
      <div className="flex items-center gap-4">
        <Button 
          variant="secondary" 
          size="sm"
          className="flex items-center gap-2 rounded-full"
          onClick={() => router.push('/organization')}
        >
          <ArrowLeftRight size={16} />
          Switch Organization
        </Button>
        <button
          onClick={() => setTheme(currentTheme === 'dark' ? 'light' : 'dark')}
          className="text-secondary-text relative w-9 h-9 flex items-center justify-center rounded-full transition-all duration-150 hover:bg-card-bg hover:text-primary-text outline-none"
          aria-label="Toggle theme"
        >
          {mounted && currentTheme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </div>
    </header>
  );
}
