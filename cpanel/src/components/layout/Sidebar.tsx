"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
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
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { isSidebarOpen, setSidebarOpen } = useAppStore();
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);

  // Close sidebar on route change on mobile
  React.useEffect(() => {
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  }, [pathname, setSidebarOpen]);

  if (pathname.startsWith('/settings')) {
    return <SettingsSidebar />;
  }

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 md:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      <aside className={`w-[220px] h-screen bg-secondary-bg backdrop-blur-2xl backdrop-saturate-[180%] shadow-[4px_0_24px_rgba(0,0,0,0.02)] border-r border-border-color flex flex-col fixed top-0 left-0 z-40 overflow-hidden transition-transform duration-300 ease-in-out ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div data-tour="sidebar-logo" className="h-[64px] border-b border-border-color flex items-center px-4 shrink-0">
        <div className="flex items-center gap-4 min-w-[200px]">
          <div className="text-accent-primary shrink-0 flex items-center justify-center">
            <Bot size={20} />
          </div>
          <div className="flex flex-col opacity-100">
            <h2 className="m-0 text-[13px] font-bold tracking-tight text-primary-text truncate uppercase">EnterpriseIQ AI</h2>
          </div>
        </div>
      </div>

      <nav data-tour="sidebar-menu" className="flex-1 py-4 flex flex-col gap-1 overflow-y-auto overflow-x-hidden">
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
              <div className={`shrink-0 flex items-center justify-center w-8 h-8 rounded-[8px] transition-colors ${isActive ? 'bg-accent-primary/20 backdrop-blur-md' : 'hover:bg-white/10'}`}>
                <item.icon size={18} strokeWidth={isActive ? 2.5 : 2} className={isActive ? "text-accent-primary" : ""} />
              </div>
              <span className="opacity-100 whitespace-nowrap">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="py-4 border-t border-border-color flex flex-col gap-1">
        <div className="flex items-center gap-4 py-2 px-4 mb-2 min-w-[200px]">
          <div className="w-8 h-8 shrink-0 rounded-[10px] bg-accent-secondary/20 backdrop-blur-md border border-accent-secondary/30 text-accent-secondary flex items-center justify-center font-bold text-[13px] shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:shadow-[0_0_15px_rgba(255,255,255,0.1)]">
            A
          </div>
          <div className="flex flex-col opacity-100">
            <span className="text-[13px] font-medium text-primary-text truncate">
              admin@company.com
            </span>
          </div>
        </div>
        <Link 
          href="/settings/general" 
          data-tour="sidebar-settings"
          className={`flex items-center gap-4 py-2 px-4 font-medium text-[13px] transition-all duration-300 ${
            pathname.startsWith('/settings') 
              ? 'bg-accent-primary/15 text-accent-primary border-r-2 border-accent-primary shadow-[inset_4px_0_15px_rgba(91,106,248,0.1)]' 
              : 'text-secondary-text hover:bg-white/20 dark:hover:bg-white/5 hover:text-primary-text border-r-2 border-transparent'
          }`}
        >
          <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-[8px]">
            <Settings size={18} strokeWidth={pathname.startsWith('/settings') ? 2.5 : 2} className={pathname.startsWith('/settings') ? "text-accent-primary" : ""} />
          </div>
          <span className="opacity-100 whitespace-nowrap">Settings</span>
        </Link>
        <button 
          onClick={() => setIsLogoutModalOpen(true)}
          className="cursor-pointer flex items-center gap-4 py-2 px-4 font-medium text-[13px] text-accent-danger transition-colors duration-75 hover:bg-accent-danger/10 border-r-2 border-transparent w-full text-left"
        >
          <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-[8px]">
            <LogOut size={18} />
          </div>
          <span className="opacity-100 whitespace-nowrap">Logout</span>
        </button>
      </div>

      </aside>

      <Modal
        isOpen={isLogoutModalOpen}
        onClose={() => setIsLogoutModalOpen(false)}
        title="Confirm Logout"
        description="Are you sure you want to log out?"
      >
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="ghost" onClick={() => setIsLogoutModalOpen(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={() => router.push('/login')}>
            Logout
          </Button>
        </div>
      </Modal>
    </>
  );
}
