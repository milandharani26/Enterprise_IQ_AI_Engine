import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export default function GeneralSettingsPage() {
  return (
    <div className="max-w-[600px]">
      <h1 className="m-0 mb-6 text-2xl font-bold text-primary-text">General Settings</h1>
      
      <Card className="bg-secondary-bg">
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4">
            <Input label="Name" defaultValue="Admin User" />
            <Input label="Email" type="email" defaultValue="admin@company.com" disabled />
            <div className="mt-4">
              <Button type="button">Save Changes</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
