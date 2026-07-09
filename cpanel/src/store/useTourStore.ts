import { create } from 'zustand';

interface TourState {
  run: boolean;
  stepIndex: number;
  completedTours: Record<string, boolean>;
  startTour: () => void;
  stopTour: () => void;
  setStepIndex: (index: number) => void;
  completeTour: (tourId: string) => void;
  initializeCompletedTours: () => void;
}

export const useTourStore = create<TourState>((set) => ({
  run: false,
  stepIndex: 0,
  completedTours: {},
  startTour: () => set({ run: true, stepIndex: 0 }),
  stopTour: () => set({ run: false }),
  setStepIndex: (index) => set({ stepIndex: index }),
  completeTour: (tourId) => {
    set((state) => {
      const updated = { ...state.completedTours, [tourId]: true };
      if (typeof window !== 'undefined') {
        localStorage.setItem('enterpriseiq-completed-tours', JSON.stringify(updated));
      }
      return { completedTours: updated, run: false };
    });
  },
  initializeCompletedTours: () => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('enterpriseiq-completed-tours');
      if (stored) {
        try {
          set({ completedTours: JSON.parse(stored) });
        } catch (e) {
          console.error(e);
        }
      }
    }
  },
}));
