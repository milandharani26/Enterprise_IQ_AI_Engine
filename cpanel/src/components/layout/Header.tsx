"use client";

import React, { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { Moon, Sun, ArrowLeftRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '../ui/Button';
import { useAppStore } from '@/store/useAppStore';
import { useOrganizationHooks } from '@/hooks/api/useOrganization';

export function Header() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  const { activeOrganizationId } = useAppStore();
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
    <header className="h-[64px] px-6 flex items-center justify-end border-b border-border-color bg-primary-bg/50 backdrop-blur-2xl backdrop-saturate-[180%] sticky top-0 z-30 transition-colors duration-300 shadow-[0_4px_24px_rgba(0,0,0,0.02)]">
      <div className="flex items-center gap-4">
        {companyName && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-card-bg border border-border-color rounded-full">
            <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
            <span className="text-[13px] font-bold text-primary-text tracking-tight">
              {companyName}
            </span>
          </div>
        )}
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
          className="cursor-pointer text-secondary-text relative w-9 h-9 flex items-center justify-center rounded-full transition-all duration-150 hover:bg-card-bg hover:text-primary-text outline-none"
          aria-label="Toggle theme"
        >
          {mounted && currentTheme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </div>
    </header>
  );
}
