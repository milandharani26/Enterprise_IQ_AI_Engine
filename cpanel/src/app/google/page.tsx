'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCredentialsHooks } from '@/hooks/api/useCredentials';
import { ShieldCheck, Loader2 } from 'lucide-react';

function GoogleOAuthCallbackContent() {
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

    exchangeMutation.mutate(
      { code, state },
      {
        onSuccess: () => {
          setStatus('Success! Redirecting back to credentials...');
          setTimeout(() => {
            router.push('/credentials');
          }, 1500);
        },
        onError: (error: any) => {
          const detail =
            error?.response?.data?.detail ||
            error?.response?.data?.message ||
            'Failed to exchange tokens. Please try again.';
          setErrorDetail(typeof detail === 'string' ? detail : JSON.stringify(detail));
          setStatus('Failed to connect Google Drive.');
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
            <p className="text-red-600 dark:text-red-400 text-xs mt-2 break-words">
              {errorDetail}
            </p>
          )}
        </div>
        
        {exchangeMutation.isError && (
          <button
            onClick={() => router.push('/credentials')}
            className="mt-4 px-4 py-2 text-sm rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 w-full"
          >
            Go Back
          </button>
        )}
      </div>
    </div>
  );
}

import { Suspense } from 'react';

export default function GoogleOAuthCallback() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center p-4">Loading...</div>}>
      <GoogleOAuthCallbackContent />
    </Suspense>
  );
}
