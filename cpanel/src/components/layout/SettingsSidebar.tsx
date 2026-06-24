"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { SlidersHorizontal, KeySquare, Blocks, ArrowLeft } from 'lucide-react';

const settingsNav = [
  { name: 'General', href: '/settings/general', icon: SlidersHorizontal },
  { name: 'Service Tokens', href: '/settings/service-token', icon: KeySquare },
];

export function SettingsSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[220px] h-screen bg-secondary-bg backdrop-blur-2xl backdrop-saturate-[180%] shadow-[4px_0_24px_rgba(0,0,0,0.02)] border-r border-border-color flex flex-col fixed top-0 left-0 z-40 overflow-hidden">
      <div className="h-[64px] border-b border-border-color flex items-center px-4 shrink-0">
        <Link href="/dashboard" className="flex items-center gap-4 text-secondary-text hover:text-primary-text transition-colors duration-300 min-w-[200px]">
          <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-[8px] group-hover:bg-white/10 transition-colors">
            <ArrowLeft size={18} />
          </div>
          <span className="text-[13px] font-bold tracking-tight opacity-100 truncate uppercase">Dashboard</span>
        </Link>
      </div>
      
      <div className="py-4 flex flex-col gap-1 overflow-y-auto overflow-x-hidden">
        <div className="px-4 mb-2 flex items-center min-w-[200px]">
          <div className="w-8 shrink-0" />
          <h3 className="text-[11px] font-bold text-muted-text uppercase tracking-[0.06em] opacity-100">SETTINGS</h3>
        </div>
        <nav className="flex flex-col gap-1">
          {settingsNav.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link 
                key={item.name} 
                href={item.href} 
                className={`flex items-center gap-4 py-2 px-4 font-medium text-[13px] transition-all duration-300 ${
                  isActive 
                    ? 'bg-accent-primary/15 text-accent-primary border-r-2 border-accent-primary shadow-[inset_4px_0_15px_rgba(91,106,248,0.1)]' 
                    : 'text-secondary-text hover:bg-white/20 dark:hover:bg-white/5 hover:text-primary-text border-r-2 border-transparent'
                }`}
              >
                <div className={`shrink-0 flex items-center justify-center w-8 h-8 rounded-[8px] transition-colors ${isActive ? 'bg-accent-primary/20 backdrop-blur-md' : 'hover:bg-white/10'}`}>
                  <item.icon size={18} strokeWidth={isActive ? 2.5 : 2} className={isActive ? "text-accent-primary" : ""} />
                </div>
                <span className="opacity-100 whitespace-nowrap">{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
