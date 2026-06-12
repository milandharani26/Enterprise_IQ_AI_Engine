import React from 'react';
import Link from 'next/link';
import { Bot } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export default function LoginPage() {
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
        <form className="flex flex-col gap-5">
          <Input 
            label="Work Email"
            type="email" 
            placeholder="name@company.com" 
            autoComplete="email"
          />
          
          <div>
            <Input 
              label="Password"
              type="password" 
              placeholder="••••••••" 
              autoComplete="current-password"
            />
          </div>
          
          <div className="mt-4">
            <Button type="button" fullWidth variant="primary" size="lg" className="shadow-lg shadow-accent-primary/20 rounded-xl">
              Login
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
