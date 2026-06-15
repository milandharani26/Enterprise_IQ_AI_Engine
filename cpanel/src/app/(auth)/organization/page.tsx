"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Building2, Plus, Search, LogOut } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useOrganizationHooks } from '@/hooks/api/useOrganization';
import { useAppStore } from '@/store/useAppStore';
import toast from 'react-hot-toast';

export default function OrganizationPage() {
  const router = useRouter();
  const { setOrganization, logout } = useAppStore();
  const { useOrganizationsQuery, useCreateOrganizationMutation } = useOrganizationHooks();
  
  const { data: organizations, isLoading } = useOrganizationsQuery();
  const createMutation = useCreateOrganizationMutation();

  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgEmail, setNewOrgEmail] = useState('');

  const filteredOrgs = Array.isArray(organizations) 
    ? organizations.filter(org => org.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : [];

  const handleSelectOrg = (id: string) => {
    setOrganization(id);
    toast.success('Organization selected');
    router.push('/dashboard');
  };

  const handleCreateOrg = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName) return;

    createMutation.mutate({ name: newOrgName, email: newOrgEmail }, {
      onSuccess: (data) => {
        toast.success('Organization created successfully!');
        setOrganization(data.id);
        setIsModalOpen(false);
        router.push('/dashboard');
      },
      onError: () => {
        toast.error('Failed to create organization');
      }
    });
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <>
      <Card className="w-full max-w-[500px] bg-card-bg border-border-color shadow-xl rounded-2xl overflow-hidden" padding="lg">
        <CardHeader className="text-center mb-6">
          <div className="flex flex-col items-center gap-4">
            <div className="w-14 h-14 bg-accent-primary/10 flex items-center justify-center rounded-2xl text-accent-primary border border-accent-primary/20">
              <Building2 size={28} />
            </div>
            <div>
              <h1 className="m-0 text-2xl font-bold tracking-tight text-primary-text">Select Organization</h1>
              <p className="m-0 mt-1.5 text-sm text-secondary-text">Choose a workspace to continue</p>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          <div className="space-y-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search organizations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-black/20 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
              />
            </div>

            <div className="max-h-[300px] overflow-y-auto space-y-2 pr-2">
              {isLoading ? (
                <div className="text-center py-8 text-sm text-gray-500">Loading organizations...</div>
              ) : filteredOrgs.length > 0 ? (
                filteredOrgs.map((org) => (
                  <button
                    key={org.id}
                    onClick={() => handleSelectOrg(org.id)}
                    className="w-full flex items-center justify-between p-4 rounded-xl border border-gray-100 dark:border-white/5 hover:border-blue-500/30 hover:bg-blue-50/50 dark:hover:bg-blue-500/10 transition-all text-left group"
                  >
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">{org.name}</h3>
                      {org.email && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{org.email}</p>}
                    </div>
                  </button>
                ))
              ) : (
                <div className="text-center py-8 text-sm text-gray-500">
                  {searchQuery ? 'No organizations match your search.' : 'No organizations found.'}
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-gray-100 dark:border-white/5 space-y-3">
              <Button 
                variant="primary" 
                fullWidth 
                className="rounded-xl flex items-center justify-center gap-2"
                onClick={() => setIsModalOpen(true)}
              >
                <Plus className="w-4 h-4" /> Create New Organization
              </Button>
              <Button 
                variant="secondary" 
                fullWidth 
                className="rounded-xl flex items-center justify-center gap-2"
                onClick={handleLogout}
              >
                <LogOut className="w-4 h-4" /> Logout
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 animate-in fade-in duration-200">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setIsModalOpen(false)} />
          <div className="relative w-full max-w-md rounded-2xl bg-white dark:bg-[#0f172a] shadow-2xl border border-gray-200 dark:border-white/10 p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">Create Organization</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Setup a new workspace environment.</p>
            
            <form onSubmit={handleCreateOrg} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Organization Name *</label>
                <input
                  type="text"
                  required
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  placeholder="e.g. Acme Corp"
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-black/20 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Billing Email (Optional)</label>
                <input
                  type="email"
                  value={newOrgEmail}
                  onChange={(e) => setNewOrgEmail(e.target.value)}
                  placeholder="billing@acme.com"
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-black/20 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
                />
              </div>
              
              <div className="flex gap-3 pt-4">
                <Button type="button" variant="secondary" fullWidth onClick={() => setIsModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" fullWidth disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
