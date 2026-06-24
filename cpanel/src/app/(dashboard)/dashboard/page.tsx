"use client";

import React from 'react';
import { 
  Bot, 
  Link as LinkIcon, 
  MessageSquare,
  Activity,
  ArrowUpRight,
  Loader2,
  PieChart as PieChartIcon,
  BarChart3
} from 'lucide-react';
import { useDashboardHooks } from '@/hooks/api/useDashboard';
import { useAppStore } from '@/store/useAppStore';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  BarChart, Bar
} from 'recharts';

const COLORS = ['#5B6AF8', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

export default function Dashboard() {
  const { activeOrganizationId } = useAppStore();
  const { useDashboardMetricsQuery } = useDashboardHooks();
  
  const { data: metrics, isLoading } = useDashboardMetricsQuery(activeOrganizationId);

  if (isLoading || !metrics) {
    return (
      <div className="min-h-full p-4 md:p-8 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
      </div>
    );
  }

  const isDegraded = metrics.system_health === "Degraded";

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
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard title="Total Assistants" value={metrics.total_assistants.toString()} icon={Bot} />
          <StatCard title="Active Connectors" value={metrics.active_connectors.toString()} icon={LinkIcon} />
          <StatCard title="Total Conversations" value={metrics.total_conversations.toString()} icon={MessageSquare} />
          <StatCard title="Total Messages" value={metrics.total_messages.toString()} icon={Activity} />
        </div>

        {/* Details Grid Top Row: Main Chart + Donut */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Engagement Depth Chart (Dual Area) */}
          <div className="lg:col-span-2 rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden flex flex-col">
            <div className="p-5 flex justify-between items-center border-b border-gray-100 dark:border-white/5">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-gray-400" />
                Engagement Depth (7 Days)
              </h2>
            </div>
            
            <div className="p-5 w-full" style={{ height: '350px' }}>
              {metrics.activity_chart.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={metrics.activity_chart}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="colorConvos" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#5B6AF8" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#5B6AF8" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorMsgs" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" opacity={0.2} />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#888' }} dy={10} />
                    <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#888' }} />
                    <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#888' }} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#111113', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Legend verticalAlign="top" height={36}/>
                    <Area yAxisId="left" type="monotone" dataKey="messages" name="Total Messages" stroke="#10B981" strokeWidth={2} fillOpacity={1} fill="url(#colorMsgs)" />
                    <Area yAxisId="right" type="monotone" dataKey="conversations" name="Conversations" stroke="#5B6AF8" strokeWidth={3} fillOpacity={1} fill="url(#colorConvos)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full w-full flex items-center justify-center text-gray-500">
                  Not enough data yet.
                </div>
              )}
            </div>
          </div>

          {/* Knowledge Composition Donut */}
          <div className="rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden flex flex-col">
            <div className="p-5 flex justify-between items-center border-b border-gray-100 dark:border-white/5">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <PieChartIcon className="w-4 h-4 text-gray-400" />
                Knowledge Base Composition
              </h2>
            </div>
            
            <div className="p-5 w-full flex flex-col items-center justify-center" style={{ height: '350px' }}>
              {metrics.knowledge_composition.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={metrics.knowledge_composition}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="count"
                      nameKey="source"
                    >
                      {metrics.knowledge_composition.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#111113', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Legend verticalAlign="bottom" height={36}/>
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full w-full flex items-center justify-center text-gray-500">
                  No documents synced yet.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Details Grid Bottom Row: Bar Chart + List */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Top Assistants Bar Chart */}
          <div className="rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden flex flex-col">
            <div className="p-5 flex justify-between items-center border-b border-gray-100 dark:border-white/5">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-gray-400" />
                Top Assistants by Usage
              </h2>
            </div>
            
            <div className="p-5 w-full" style={{ height: '350px' }}>
              {metrics.top_assistants.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={metrics.top_assistants}
                    layout="vertical"
                    margin={{ top: 10, right: 30, left: 20, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="var(--border-color)" opacity={0.2} />
                    <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#888' }} />
                    <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#888' }} width={100} />
                    <Tooltip 
                      cursor={{fill: 'transparent'}}
                      contentStyle={{ backgroundColor: '#111113', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                    />
                    <Bar dataKey="conversations" name="Conversations" fill="#5B6AF8" radius={[0, 4, 4, 0]} barSize={24}>
                      {metrics.top_assistants.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full w-full flex items-center justify-center text-gray-500">
                  No assistants used yet.
                </div>
              )}
            </div>
          </div>

          {/* Recent Conversations Card */}
          <div className="rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden flex flex-col">
            <div className="p-5 flex justify-between items-center border-b border-gray-100 dark:border-white/5">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-gray-400" />
                Recent Conversations
              </h2>
            </div>
            
            <div className="flex-1 p-0 overflow-y-auto max-h-[300px]">
              <ul className="divide-y divide-gray-100 dark:divide-white/5">
                {metrics.recent_conversations.map((convo) => (
                  <li key={convo.id} className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                    <div className="flex flex-col gap-1 w-full overflow-hidden">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{convo.title}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(convo.created_at).toLocaleString(undefined, {
                          month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
                        })}
                      </p>
                    </div>
                  </li>
                ))}
                {metrics.recent_conversations.length === 0 && (
                  <li className="px-5 py-8 text-center text-gray-500 dark:text-gray-400 text-sm">
                    No recent conversations.
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

function StatCard({ title, value, icon: Icon }: any) {
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
      </div>
    </div>
  );
}
