import { create } from 'zustand';

interface AppState {
  user: { name: string; email: string } | null;
  setUser: (user: { name: string; email: string } | null) => void;
  
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (isOpen: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // User State
  user: null,
  setUser: (user) => set({ user }),

  // UI State
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
}));
