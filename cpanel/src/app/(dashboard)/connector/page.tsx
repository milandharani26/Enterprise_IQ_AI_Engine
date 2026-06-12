import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

export default function ConnectorPage() {
  return (
    <div>
      <h1 className="m-0 mb-6 text-2xl font-bold text-primary-text">Connectors</h1>
      <Card>
        <CardHeader>
          <CardTitle>Manage Connectors</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-secondary-text">Connectors management feature coming soon.</p>
        </CardContent>
      </Card>
    </div>
  );
}
