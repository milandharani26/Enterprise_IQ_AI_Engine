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
    <aside className="w-[260px] h-screen bg-secondary-bg border-r border-border-color flex flex-col fixed top-0 left-0 z-40">
      <div className="p-6">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-secondary-text text-sm font-medium transition-colors duration-150 hover:text-primary-text">
          <ArrowLeft size={16} />
          <span>Back to Dashboard</span>
        </Link>
      </div>
      
      <div className="px-4 mt-4">
        <h3 className="text-xs font-semibold text-muted-text tracking-widest mb-3 px-2">SETTINGS</h3>
        <nav className="flex flex-col gap-[2px]">
          {settingsNav.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link 
                key={item.name} 
                href={item.href} 
                className={`flex items-center gap-3 py-2 px-3 rounded-md text-sm transition-all duration-150 ${
                  isActive 
                    ? 'bg-tertiary-bg text-primary-text font-semibold' 
                    : 'text-secondary-text font-medium hover:bg-card-bg hover:text-primary-text'
                }`}
              >
                <item.icon size={18} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
