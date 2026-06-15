import { create } from 'zustand';

import Cookies from 'js-cookie';

export interface User {
  id?: string;
  email: string;
  role?: string;
  is_active?: boolean;
}

interface AppState {
  user: User | null;
  isAuthenticated: boolean;
  activeOrganizationId: string | null;
  setUser: (user: User | null) => void;
  setOrganization: (id: string | null) => void;
  logout: () => void;
  
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (isOpen: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // User State
  user: null,
  isAuthenticated: false,
  activeOrganizationId: Cookies.get('active_org_id') || null,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setOrganization: (id) => {
    if (id) {
      Cookies.set('active_org_id', id, { expires: 365 });
    } else {
      Cookies.remove('active_org_id');
    }
    set({ activeOrganizationId: id });
  },
  logout: () => {
    Cookies.remove('active_org_id');
    set({ user: null, isAuthenticated: false, activeOrganizationId: null });
  },

  // UI State
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
}));
