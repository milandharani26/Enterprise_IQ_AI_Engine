"use client";

import React, { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { Moon, Sun, ArrowLeftRight, Menu } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '../ui/Button';
import { useAppStore } from '@/store/useAppStore';
import { useOrganizationHooks } from '@/hooks/api/useOrganization';

export function Header() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  const { activeOrganizationId, toggleSidebar } = useAppStore();
  const { useOrganizationsQuery } = useOrganizationHooks();
  const { data: organizations } = useOrganizationsQuery();

  const activeOrg = Array.isArray(organizations) 
    ? organizations.find((org: any) => org.id === activeOrganizationId) 
    : undefined;
  const companyName = activeOrg ? activeOrg.name : '';

  // Avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  const currentTheme = resolvedTheme || theme;

  return (
    <header className="h-[64px] px-4 md:px-6 flex items-center justify-between md:justify-end border-b border-border-color bg-primary-bg/50 backdrop-blur-2xl backdrop-saturate-[180%] sticky top-0 z-30 transition-colors duration-300 shadow-[0_4px_24px_rgba(0,0,0,0.02)]">
      <div className="md:hidden flex items-center">
        <button
          onClick={toggleSidebar}
          className="p-2 -ml-2 text-secondary-text hover:text-primary-text transition-colors"
          aria-label="Toggle Menu"
        >
          <Menu size={24} />
        </button>
      </div>

      <div className="flex items-center gap-2 md:gap-4 ml-auto">
        {companyName && (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-card-bg border border-border-color rounded-full shrink-0">
            <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse shrink-0" />
            <span className="text-[13px] font-bold text-primary-text tracking-tight truncate max-w-[120px] lg:max-w-[200px]">
              {companyName}
            </span>
          </div>
        )}
        <Button 
          variant="secondary" 
          size="sm"
          className="flex items-center gap-2 rounded-full px-3 md:px-4 shrink-0"
          onClick={() => router.push('/organization')}
        >
          <ArrowLeftRight size={16} />
          <span className="hidden sm:inline">Switch Organization</span>
          <span className="sm:hidden">Switch</span>
        </Button>
        <button
          onClick={() => setTheme(currentTheme === 'dark' ? 'light' : 'dark')}
          className="cursor-pointer text-secondary-text relative w-9 h-9 flex items-center justify-center rounded-full transition-all duration-150 hover:bg-card-bg hover:text-primary-text outline-none"
          aria-label="Toggle theme"
        >
          {mounted && currentTheme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </div>
    </header>
  );
}
