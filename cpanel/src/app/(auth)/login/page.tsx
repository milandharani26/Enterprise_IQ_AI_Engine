"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Bot } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useAuthHooks } from '@/hooks/api/useAuth';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const { useLoginMutation } = useAuthHooks();
  const loginMutation = useLoginMutation();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loginMutation.mutate(
      { email, password },
      {
        onSuccess: () => {
          toast.success('Successfully logged in!');
          router.push('/dashboard');
        },
        onError: (error: any) => {
          const msg = error?.response?.data?.message || 'Login failed. Please check your credentials.';
          toast.error(msg);
        }
      }
    );
  };

  return (
    <Card className="w-full max-w-[400px] bg-card-bg border-border-color shadow-xl rounded-2xl overflow-hidden" padding="lg">
      <CardHeader className="text-center mb-8">
        <div className="flex flex-col items-center gap-4">
          <div className="w-14 h-14 bg-accent-primary/10 flex items-center justify-center rounded-2xl text-accent-primary border border-accent-primary/20">
            <Bot size={28} />
          </div>
          <div>
            <h1 className="m-0 text-2xl font-bold tracking-tight text-primary-text">Welcome Back</h1>
            <p className="m-0 mt-1.5 text-sm text-secondary-text">Sign in to Enterprise GPT</p>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
          <Input 
            label="Work Email"
            type="email" 
            placeholder="name@company.com" 
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          
          <div>
            <Input 
              label="Password"
              type="password" 
              placeholder="••••••••" 
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <div className="mt-4">
            <Button 
              type="submit" 
              fullWidth 
              variant="primary" 
              size="lg" 
              className="shadow-lg shadow-accent-primary/20 rounded-xl"
              disabled={loginMutation.isPending}
            >
              {loginMutation.isPending ? 'Logging in...' : 'Login'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
