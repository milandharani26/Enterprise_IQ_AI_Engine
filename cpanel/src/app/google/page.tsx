'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCredentialsHooks } from '@/hooks/api/useCredentials';
import { ShieldCheck, Loader2 } from 'lucide-react';

export default function GoogleOAuthCallback() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { useExchangeGoogleOAuthCodeMutation } = useCredentialsHooks();
  const exchangeMutation = useExchangeGoogleOAuthCodeMutation();
  
  const [status, setStatus] = useState('Exchanging secure tokens...');
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (!code || !state) {
      setStatus('Invalid OAuth callback parameters. Missing code or state.');
      return;
    }

    // Use sessionStorage as a cross-remount guard.
    // React Strict Mode (and Next.js App Router) mounts → unmounts → remounts
    // the component in development, which resets useRef — causing the exchange
    // to fire twice. The second attempt always fails with invalid_grant because
    // Google authorization codes are single-use.
    const guardKey = `oauth_exchange_fired_${state}`;
    if (sessionStorage.getItem(guardKey)) {
      return;
    }
    sessionStorage.setItem(guardKey, '1');

    exchangeMutation.mutate(
      { code, state },
      {
        onSuccess: () => {
          setStatus('Success! Redirecting back to credentials...');
          sessionStorage.removeItem(guardKey);
          setTimeout(() => {
            router.push('/credentials');
          }, 1500);
        },
        onError: (error: any) => {
          sessionStorage.removeItem(guardKey);
          const detail = error?.response?.data?.detail || 'Failed to exchange tokens.';
          setStatus('Authorization failed.');
          setErrorDetail(detail);
        }
      }
    );
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-white dark:bg-[#111113] flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white dark:bg-[#1c1c1f] rounded-2xl shadow-xl border border-gray-100 dark:border-white/10 p-8 text-center space-y-6">
        <div className="flex justify-center">
          <div className="w-16 h-16 bg-blue-50 dark:bg-blue-500/10 rounded-2xl flex items-center justify-center border border-blue-100 dark:border-blue-500/20">
            {exchangeMutation.isPending || status === 'Exchanging secure tokens...' ? (
              <Loader2 className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin" />
            ) : exchangeMutation.isSuccess ? (
              <ShieldCheck className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <ShieldCheck className="w-8 h-8 text-red-600 dark:text-red-400" />
            )}
          </div>
        </div>
        
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            Google Authentication
          </h2>
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            {status}
          </p>
          {errorDetail && (
            <p className="mt-3 text-xs text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/30 rounded-lg px-3 py-2 text-left">
              {errorDetail}
            </p>
          )}
        </div>
        
        {(exchangeMutation.isError || errorDetail) && (
          <button
            onClick={() => router.push('/credentials')}
            className="mt-4 px-4 py-2 text-sm rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 w-full"
          >
            Go Back &amp; Retry
          </button>
        )}
      </div>
    </div>
  );
}
