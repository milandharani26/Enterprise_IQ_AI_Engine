import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { StoreHydrator } from '@/components/StoreHydrator';
import { PageTransition } from '@/components/layout/PageTransition';
import { Tour } from '@/components/layout/Tour';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <StoreHydrator>
      <Tour />
      <div className="flex min-h-screen relative">
        <Sidebar />
        <div className="flex-1 md:ml-[220px] flex flex-col min-h-screen w-full transition-all duration-300">
          <Header />
          <main className="flex-1 p-4 md:p-8 overflow-y-auto bg-primary-bg w-full">
            <PageTransition>
              {children}
            </PageTransition>
          </main>
        </div>
      </div>
    </StoreHydrator>
  );
}
