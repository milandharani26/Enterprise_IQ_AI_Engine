import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

export default function ChatPage() {
  return (
    <div>
      <h1 className="m-0 mb-6 text-2xl font-bold text-primary-text">Chat</h1>
      <Card>
        <CardHeader>
          <CardTitle>Chat Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-secondary-text">Chat feature coming soon.</p>
        </CardContent>
      </Card>
    </div>
  );
}
