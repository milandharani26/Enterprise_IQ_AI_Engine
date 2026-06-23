"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Bot, 
  Link as LinkIcon, 
  Key, 
  Settings,
  LogOut,
  FileText
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Assistants', href: '/assistants', icon: Bot },
  { name: 'Connectors', href: '/connector', icon: LinkIcon },
  { name: 'Credentials', href: '/credentials', icon: Key },
];

import { SettingsSidebar } from './SettingsSidebar';
import { useAppStore } from '@/store/useAppStore';
import { useOrganizationHooks } from '@/hooks/api/useOrganization';

export function Sidebar() {
  const pathname = usePathname();
  const { activeOrganizationId } = useAppStore();
  const { useOrganizationsQuery } = useOrganizationHooks();
  const { data: organizations } = useOrganizationsQuery();

  const activeOrg = Array.isArray(organizations) 
    ? organizations.find((org: any) => org.id === activeOrganizationId) 
    : undefined;
  const companyName = activeOrg ? activeOrg.name : 'Enterprise GPT';

  if (pathname.startsWith('/settings')) {
    return <SettingsSidebar />;
  }

  return (
    <aside className="w-[64px] hover:w-[220px] transition-all duration-300 h-screen bg-secondary-bg backdrop-blur-2xl backdrop-saturate-[180%] shadow-[4px_0_24px_rgba(0,0,0,0.02)] border-r border-border-color flex flex-col fixed top-0 left-0 z-40 group overflow-hidden">
      <div className="h-[64px] border-b border-border-color flex items-center px-4 shrink-0">
        <div className="flex items-center gap-4 min-w-[200px]">
          <div className="text-accent-primary shrink-0 flex items-center justify-center">
            <Bot size={20} />
          </div>
          <div className="flex flex-col opacity-0 group-hover:opacity-100 transition-opacity duration-75">
            <h2 className="m-0 text-[13px] font-bold tracking-tight text-primary-text truncate uppercase">{companyName}</h2>
          </div>
        </div>
      </div>

      <nav className="flex-1 py-4 flex flex-col gap-1 overflow-y-auto overflow-x-hidden">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
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
              <div className={`shrink-0 flex items-center justify-center w-8 h-8 rounded-[8px] transition-colors ${isActive ? 'bg-accent-primary/20 backdrop-blur-md' : 'group-hover:bg-white/10'}`}>
                <item.icon size={18} strokeWidth={isActive ? 2.5 : 2} className={isActive ? "text-accent-primary" : ""} />
              </div>
              <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="py-4 border-t border-border-color flex flex-col gap-1">
        <div className="flex items-center gap-4 py-2 px-4 mb-2 min-w-[200px]">
          <div className="w-8 h-8 shrink-0 rounded-[10px] bg-accent-secondary/20 backdrop-blur-md border border-accent-secondary/30 text-accent-secondary flex items-center justify-center font-bold text-[13px] shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:shadow-[0_0_15px_rgba(255,255,255,0.1)]">
            A
          </div>
          <div className="flex flex-col opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <span className="text-[13px] font-medium text-primary-text truncate">
              admin@company.com
            </span>
          </div>
        </div>
        <Link 
          href="/settings/general" 
          className={`flex items-center gap-4 py-2 px-4 font-medium text-[13px] transition-all duration-300 ${
            pathname.startsWith('/settings') 
              ? 'bg-accent-primary/15 text-accent-primary border-r-2 border-accent-primary shadow-[inset_4px_0_15px_rgba(91,106,248,0.1)]' 
              : 'text-secondary-text hover:bg-white/20 dark:hover:bg-white/5 hover:text-primary-text border-r-2 border-transparent'
          }`}
        >
          <div className="shrink-0 flex items-center justify-center">
            <Settings size={20} />
          </div>
          <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-75 whitespace-nowrap">Settings</span>
        </Link>
        <Link href="/login" className="flex items-center gap-4 py-2 px-4 font-medium text-[13px] text-secondary-text transition-colors duration-75 hover:bg-card-bg hover:text-primary-text border-r-2 border-transparent">
          <div className="shrink-0 flex items-center justify-center">
            <LogOut size={20} />
          </div>
          <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-75 whitespace-nowrap">Logout</span>
        </Link>
      </div>
    </aside>
  );
}
