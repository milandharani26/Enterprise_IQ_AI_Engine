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
  LogOut
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Assistants', href: '/assistants', icon: Bot },
  { name: 'Connectors', href: '/connector', icon: LinkIcon },
  { name: 'Credentials', href: '/credentials', icon: Key },
];

import { SettingsSidebar } from './SettingsSidebar';

export function Sidebar() {
  const pathname = usePathname();

  if (pathname.startsWith('/settings')) {
    return <SettingsSidebar />;
  }

  return (
    <aside className="w-[260px] h-screen bg-secondary-bg border-r border-border-color flex flex-col fixed top-0 left-0 z-40">
      <div className="p-6 border-b border-border-color">
        <div className="flex items-center gap-3">
          <div className="text-accent-primary bg-accent-primary/10 p-1 rounded w-8 h-8 flex items-center justify-center">
            <Bot size={24} />
          </div>
          <div className="flex flex-col">
            <h2 className="m-0 text-base font-bold tracking-tight text-primary-text">Enterprise GPT</h2>
            <span className="text-xs text-muted-text">Management Platform</span>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 flex flex-col gap-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link 
              key={item.name} 
              href={item.href} 
              className={`flex items-center gap-3 py-3 px-4 rounded-md font-medium text-sm transition-all duration-150 ${
                isActive 
                  ? 'bg-accent-primary/10 text-accent-primary' 
                  : 'text-secondary-text hover:bg-card-bg hover:text-primary-text'
              }`}
            >
              <item.icon size={20} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border-color flex flex-col gap-2">
        <div className="flex items-center gap-3 py-3 px-4 rounded-md bg-tertiary-bg mb-2">
          <div className="w-8 h-8 rounded-full bg-accent-secondary text-white flex items-center justify-center font-semibold text-sm">
            A
          </div>
          <div className="flex flex-col overflow-hidden">
            <span className="text-sm font-medium text-primary-text whitespace-nowrap overflow-hidden text-ellipsis">
              admin@company.com
            </span>
          </div>
        </div>
        <Link 
          href="/settings/general" 
          className={`flex items-center gap-3 py-3 px-4 rounded-md font-medium text-sm transition-all duration-150 ${
            pathname.startsWith('/settings') 
              ? 'bg-accent-primary/10 text-accent-primary' 
              : 'text-secondary-text hover:bg-card-bg hover:text-primary-text'
          }`}
        >
          <Settings size={20} />
          <span>Settings</span>
        </Link>
        <Link href="/login" className="flex items-center gap-3 py-3 px-4 rounded-md font-medium text-sm text-secondary-text transition-all duration-150 hover:bg-card-bg hover:text-primary-text">
          <LogOut size={20} />
          <span>Logout</span>
        </Link>
      </div>
    </aside>
  );
}
