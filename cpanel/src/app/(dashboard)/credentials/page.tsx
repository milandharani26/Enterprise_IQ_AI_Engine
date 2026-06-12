"use client";

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export default function CredentialsPage() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="m-0 text-2xl font-bold text-primary-text">Credentials</h1>
          <p className="mt-1 text-sm text-secondary-text">Manage external API keys and authentication credentials.</p>
        </div>
        <Button variant="primary">Add Credential</Button>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Configured Credentials</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center p-10 text-center">
            <p className="text-primary-text font-medium mb-1">No credentials found</p>
            <p className="text-sm text-secondary-text">You haven't added any external credentials yet.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
