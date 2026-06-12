"use client";

import React from 'react';
import { Bot, ShieldCheck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { useSystemHooks } from '@/hooks/api/useSystem';
import { useAssistantsHooks } from '@/hooks/api/useAssistants';

export default function DashboardPage() {
  const { useHealthQuery } = useSystemHooks();
  const { data: healthData, isLoading: isHealthLoading } = useHealthQuery();

  const { useAssistantsQuery } = useAssistantsHooks();
  const { data: assistants = [] } = useAssistantsQuery();

  return (
    <div className="flex flex-col gap-8">
      <div className="mb-2">
        <h1 className="text-2xl font-bold text-primary-text m-0 mb-1 tracking-tight">Dashboard</h1>
        <p className="text-secondary-text text-sm m-0">Overview of your Enterprise IQ system</p>
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-4">
        <StatCard title="Total Assistants" value={assistants.length.toString()} icon={Bot} />
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-4">
        <Card hoverable className="bg-secondary-bg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bot size={18} className="text-accent-primary" />
              <CardTitle>Top Assistants</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-3">
              {assistants.slice(0, 5).map((ast, idx) => (
                <li key={ast.assistant_id || idx} className="flex justify-between items-center text-sm">
                  <div className="flex gap-2">
                    <span className="text-muted-text">{idx + 1}.</span>
                    <span className="font-medium text-primary-text">{ast.assistant_name}</span>
                  </div>
                  <span className="text-secondary-text">{ast.type}</span>
                </li>
              ))}
              {assistants.length === 0 && (
                <li className="text-sm text-secondary-text">No assistants found.</li>
              )}
            </ul>
          </CardContent>
        </Card>

        <Card hoverable className="bg-secondary-bg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck size={18} className="text-accent-primary" />
              <CardTitle>System Health</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {isHealthLoading ? (
              <p className="text-sm text-secondary-text">Checking health...</p>
            ) : (
              <ul className="flex flex-col gap-3">
                <li className="flex justify-between items-center text-sm">
                  <span className="font-medium text-primary-text">Backend API</span>
                  {healthData?.status === 'ok' ? (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium text-accent-success">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-success" /> Operational
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium text-accent-danger">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-danger" /> Offline
                    </span>
                  )}
                </li>
                <li className="flex justify-between items-center text-sm">
                  <span className="font-medium text-primary-text">Environment</span>
                  <span className="text-secondary-text capitalize">{healthData?.env || 'Unknown'}</span>
                </li>
                <li className="flex justify-between items-center text-sm">
                  <span className="font-medium text-primary-text">Database</span>
                  {healthData?.database === 'connected' ? (
                    <span className="text-secondary-text">Connected</span>
                  ) : (
                    <span className="text-accent-danger">Disconnected</span>
                  )}
                </li>
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon }: any) {
  return (
    <Card hoverable padding="md" className="bg-secondary-bg">
      <div className="flex justify-between items-center mb-4">
        <span className="text-sm text-secondary-text font-medium">{title}</span>
        <div className="w-8 h-8 rounded-md bg-tertiary-bg flex items-center justify-center text-muted-text">
          <Icon size={18} />
        </div>
      </div>
      <div>
        <span className="text-3xl font-bold text-primary-text tracking-tight">{value}</span>
      </div>
    </Card>
  );
}
