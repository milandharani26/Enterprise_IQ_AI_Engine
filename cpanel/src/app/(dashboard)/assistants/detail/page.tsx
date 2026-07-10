import React, { Suspense } from 'react';
import AssistantDetailsClient from './ClientPage';

export default function AssistantDetailsPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center p-10 text-secondary-text">Loading details...</div>}>
      <AssistantDetailsClient />
    </Suspense>
  );
}
