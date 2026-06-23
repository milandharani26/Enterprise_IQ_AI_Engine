import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { StoreHydrator } from '@/components/StoreHydrator';
import { PageTransition } from '@/components/layout/PageTransition';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <StoreHydrator>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 ml-[64px] flex flex-col min-h-screen">
          <Header />
          <main className="flex-1 p-8 overflow-y-auto bg-primary-bg">
            <PageTransition>
              {children}
            </PageTransition>
          </main>
        </div>
      </div>
    </StoreHydrator>
  );
}
