import React from 'react';
import { Users, Bot, Wrench, MessageSquare, Activity, ShieldCheck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="mb-2">
        <h1 className="text-2xl font-bold text-primary-text m-0 mb-1 tracking-tight">Welcome, admin@company.com</h1>
        <p className="text-secondary-text text-sm m-0">Managing <span className="text-primary-text font-semibold">Acme Corporation</span></p>
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-4">
        <StatCard title="Clients" value="4" trend="+12%" icon={Users} trendUp />
        <StatCard title="Assistants" value="4" trend="+8%" icon={Bot} trendUp />
        <StatCard title="Tools Available" value="4" trend="+15%" icon={Wrench} trendUp />
        <StatCard title="Chat Sessions" value="2,847" trend="+23%" icon={MessageSquare} trendUp />
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-4">
        <Card hoverable className="bg-secondary-bg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity size={18} className="text-accent-primary" />
              <CardTitle>API Usage This Month</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-4 last:mb-0">
              <div className="flex justify-between mb-2 text-sm">
                <span className="text-secondary-text">Requests</span>
                <span className="font-semibold text-primary-text">124,532</span>
              </div>
              <div className="w-full h-2 bg-tertiary-bg rounded-full overflow-hidden">
                <div className="h-full bg-accent-primary rounded-full" style={{ width: '45%' }} />
              </div>
            </div>
            <div className="mb-4 last:mb-0">
              <div className="flex justify-between mb-2 text-sm">
                <span className="text-secondary-text">Tokens Used</span>
                <span className="font-semibold text-primary-text">45.2M / 100M</span>
              </div>
              <div className="w-full h-2 bg-tertiary-bg rounded-full overflow-hidden">
                <div className="h-full bg-accent-primary rounded-full" style={{ width: '45.2%' }} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card hoverable className="bg-secondary-bg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bot size={18} className="text-accent-primary" />
              <CardTitle>Top Assistants</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-3">
              <li className="flex justify-between items-center text-sm">
                <div className="flex gap-2">
                  <span className="text-muted-text">1.</span>
                  <span className="font-medium text-primary-text">General Assistant</span>
                </div>
                <span className="text-secondary-text">2 tools</span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <div className="flex gap-2">
                  <span className="text-muted-text">2.</span>
                  <span className="font-medium text-primary-text">Code Reviewer</span>
                </div>
                <span className="text-secondary-text">1 tool</span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <div className="flex gap-2">
                  <span className="text-muted-text">3.</span>
                  <span className="font-medium text-primary-text">Customer Support Bot</span>
                </div>
                <span className="text-secondary-text">1 tool</span>
              </li>
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
            <ul className="flex flex-col gap-3">
              <li className="flex justify-between items-center text-sm">
                <span className="font-medium text-primary-text">OpenAI API</span>
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium text-accent-success">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-success" /> Operational
                </span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <span className="font-medium text-primary-text">Vector DB</span>
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium text-accent-success">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-success" /> Operational
                </span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <span className="font-medium text-primary-text">API Gateway</span>
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium text-accent-warning">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-warning" /> Degraded
                </span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      <h2 className="text-lg font-semibold text-primary-text mt-4 mb-0 tracking-tight">Recent Clients</h2>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4">
        <ClientCard name="Acme Corporation" status="active" />
        <ClientCard name="TechStart Inc" status="active" />
        <ClientCard name="Global Finance Ltd" status="inactive" />
      </div>
    </div>
  );
}

function StatCard({ title, value, trend, icon: Icon, trendUp }: any) {
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
      <div className="mt-4">
        <span className={`text-xs font-medium ${trendUp ? 'text-accent-success' : 'text-accent-danger'}`}>
          {trend} from last month
        </span>
      </div>
    </Card>
  );
}

function ClientCard({ name, status }: any) {
  return (
    <Card hoverable padding="md" className="flex flex-row items-center gap-4 bg-secondary-bg">
      <div className="w-10 h-10 rounded-md bg-tertiary-bg flex items-center justify-center text-muted-text">
        <Users size={20} />
      </div>
      <div className="flex flex-col gap-0.5">
        <h3 className="m-0 text-sm font-semibold text-primary-text">{name}</h3>
        <span className={`text-xs capitalize ${status === 'active' ? 'text-secondary-text' : 'text-muted-text'}`}>
          {status}
        </span>
      </div>
    </Card>
  );
}
