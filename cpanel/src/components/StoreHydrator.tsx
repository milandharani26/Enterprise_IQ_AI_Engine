'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';

/** Sync cookie-backed state after mount so SSR and client HTML match. */
export function StoreHydrator({ children }: { children: React.ReactNode }) {
  const hydrateFromCookies = useAppStore((s) => s.hydrateFromCookies);

  useEffect(() => {
    hydrateFromCookies();
  }, [hydrateFromCookies]);

  return <>{children}</>;
}
