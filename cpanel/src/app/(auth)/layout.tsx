export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative overflow-y-auto overflow-x-hidden bg-primary-bg">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-screen h-screen bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.1)_0%,transparent_50%)] pointer-events-none" />
      <div className="relative z-10 w-full flex justify-center p-4 sm:p-6 lg:p-8">
        {children}
      </div>
    </div>
  );
}
