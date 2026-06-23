"use client";

import React from 'react';
import { 
  Bot, 
  Link as LinkIcon, 
  KeyRound, 
  MessageSquare,
  Activity,
  Globe,
  ShieldCheck,
  ArrowUpRight
} from 'lucide-react';
import { useAssistantsHooks } from '@/hooks/api/useAssistants';
import { useConnectorsHooks } from '@/hooks/api/useConnectors';
import { useCredentialsHooks } from '@/hooks/api/useCredentials';
import { useAppStore } from '@/store/useAppStore';

export default function Dashboard() {
  const { activeOrganizationId } = useAppStore();
  const { useAssistantsQuery } = useAssistantsHooks();
  const { useConnectorsQuery } = useConnectorsHooks();
  const { useCredentialsQuery } = useCredentialsHooks();
  
  const { data: assistants = [] } = useAssistantsQuery();
  const { data: connectors = [] } = useConnectorsQuery(activeOrganizationId);
  const { data: credentials = [] } = useCredentialsQuery(activeOrganizationId);

  const enabledConnectors = connectors.filter((c: any) => c.status === 'enabled');
  const activeCredentials = credentials.slice(0, 5);

  return (
    <div className="min-h-full p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-gray-200 dark:border-white/10 pb-6">
          <div>
            <h1 className="text-3xl font-semibold text-gray-900 dark:text-white tracking-tight">Dashboard</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">
              System overview and real-time metrics for Enterprise IQ.
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 font-medium border border-emerald-200 dark:border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              All systems operational
            </span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard title="Total Assistants" value={assistants.length.toString()} icon={Bot} trend="+12%" />
          <StatCard title="Active Connectors" value={enabledConnectors.length.toString()} icon={LinkIcon} trend="+3" />
          <StatCard title="Secure Credentials" value={credentials.length.toString()} icon={KeyRound} trend="Stable" />
          <StatCard title="Live Chat Sessions" value="12" icon={MessageSquare} trend="+24%" />
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Top Assistants Card */}
          <div className="rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden flex flex-col">
            <div className="p-5 flex justify-between items-center border-b border-gray-100 dark:border-white/5">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Bot className="w-4 h-4 text-gray-400" />
                Deployed Assistants
              </h2>
            </div>
            
            <div className="flex-1 p-0">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-gray-50/50 dark:bg-white/5 border-b border-gray-100 dark:border-white/5">
                    <th className="px-5 py-3 font-medium text-gray-500 dark:text-gray-400">Name</th>
                    <th className="px-5 py-3 font-medium text-gray-500 dark:text-gray-400 text-right">Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-white/5">
                  {assistants.slice(0, 5).map((ast, idx) => (
                    <tr key={ast.assistant_id || idx} className="hover:bg-gray-50 dark:hover:bg-white/5 transition-colors group">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-3">
                          <span className="text-gray-400 dark:text-gray-500 text-xs font-mono">{idx + 1}</span>
                          <span className="font-medium text-gray-900 dark:text-white">{ast.assistant_name}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-300">
                          {ast.type}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {assistants.length === 0 && (
                    <tr>
                      <td colSpan={2} className="px-5 py-8 text-center text-gray-500 dark:text-gray-400">
                        No assistants deployed yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Integrations Card */}
          <div className="rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden flex flex-col">
            <div className="p-5 flex justify-between items-center border-b border-gray-100 dark:border-white/5">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-gray-400" />
                Recent Credentials
              </h2>
            </div>
            
            <div className="flex-1 p-0">
              <ul className="divide-y divide-gray-100 dark:divide-white/5">
                {activeCredentials.map((cred) => (
                  <li key={cred.id} className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-md bg-gray-100 dark:bg-white/10 flex items-center justify-center border border-gray-200 dark:border-white/5">
                        <Globe className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{cred.name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{cred.provider}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-500" />
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                        {cred.status}
                      </span>
                    </div>
                  </li>
                ))}
                {activeCredentials.length === 0 && (
                  <li className="px-5 py-8 text-center text-gray-500 dark:text-gray-400 text-sm">
                    No credentials added yet.
                  </li>
                )}
              </ul>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, trend }: any) {
  return (
    <div className="p-5 rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm flex flex-col justify-between hover:border-gray-300 dark:hover:border-white/20 transition-colors">
      <div className="flex justify-between items-start mb-4">
        <span className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</span>
        <div className="p-1.5 rounded-md text-gray-400 dark:text-gray-500 border border-transparent">
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="flex items-baseline justify-between">
        <span className="text-2xl font-semibold text-gray-900 dark:text-white tracking-tight">{value}</span>
        {trend && (
          <span className={`flex items-center text-xs font-medium ${trend === 'Stable' ? 'text-gray-500' : 'text-emerald-600 dark:text-emerald-400'}`}>
            {trend !== 'Stable' && <ArrowUpRight className="w-3 h-3 mr-0.5" />}
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
