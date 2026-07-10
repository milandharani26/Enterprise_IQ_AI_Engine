"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Building2, Plus, Search, LogOut } from 'lucide-react';
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
      <div className="w-full max-w-6xl mx-auto flex flex-col pt-0 md:pt-4 px-4 min-h-[calc(100vh-4rem)]">
        
        {/* Top Actions */}
        <div className="flex items-center justify-end mb-4 md:mb-8">
          <Button variant="ghost" onClick={handleLogout} className="text-secondary-text hover:text-primary-text gap-2">
            <LogOut size={16} /> Logout
          </Button>
        </div>

        {/* Header */}
        <div className="flex flex-col items-center mb-8 text-center animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div className="w-14 h-14 bg-gradient-to-br from-accent-primary/20 to-accent-secondary/20 flex items-center justify-center rounded-2xl text-accent-primary border border-accent-primary/20 mb-6 shadow-inner">
            <Building2 size={28} />
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-primary-text mb-4">
            Select Your Workspace
          </h1>
          <p className="text-secondary-text max-w-md mx-auto text-sm md:text-base">
            Choose an organization to enter the dashboard, or create a new one to get started with Enterprise GPT.
          </p>
        </div>

        {/* Action Bar */}
        <div className="flex flex-col sm:flex-row items-center gap-4 mb-8 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-100 fill-mode-both">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-text" />
            <input
              type="text"
              placeholder="Search organizations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-11 pr-4 py-4 rounded-xl border border-border-color bg-card-bg/80 backdrop-blur-xl text-primary-text focus:outline-none focus:ring-2 focus:ring-accent-primary/50 transition-all shadow-sm hover:border-border-hover"
            />
          </div>
          <Button 
            variant="primary" 
            className="w-full sm:w-auto rounded-xl flex items-center justify-center gap-2 py-4 px-8 shadow-lg shadow-accent-primary/20 hover:shadow-accent-primary/40 transition-all text-base"
            onClick={() => setIsModalOpen(true)}
          >
            <Plus className="w-5 h-5" /> Create Workspace
          </Button>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,340px),1fr))] gap-6 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200 fill-mode-both">
          {isLoading ? (
            [1, 2, 3].map(i => (
              <div key={i} className="h-[160px] bg-card-bg border border-border-color rounded-2xl animate-pulse" />
            ))
          ) : filteredOrgs.length > 0 ? (
            filteredOrgs.map((org) => (
              <div
                key={org.id}
                onClick={() => handleSelectOrg(org.id)}
                className="group relative flex flex-col p-6 bg-card-bg/80 backdrop-blur-sm border border-border-color rounded-2xl cursor-pointer hover:border-accent-primary/50 hover:shadow-2xl hover:shadow-accent-primary/10 transition-all duration-300 overflow-hidden hover:-translate-y-1"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-accent-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative z-10 flex flex-col h-full">
                  <div className="flex items-start justify-between mb-6">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-tertiary-bg to-secondary-bg border border-border-color flex items-center justify-center text-primary-text font-bold text-xl shadow-sm">
                      {org.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="w-8 h-8 flex items-center justify-center bg-secondary-bg rounded-full text-secondary-text group-hover:text-white group-hover:bg-accent-primary transition-all duration-300 shadow-sm group-hover:shadow-md group-hover:scale-110">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                    </div>
                  </div>
                  <div className="mt-auto">
                    <h3 className="text-lg font-bold text-primary-text group-hover:text-accent-primary transition-colors">{org.name}</h3>
                    {org.email && <p className="text-sm text-secondary-text mt-1">{org.email}</p>}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full flex flex-col items-center justify-center py-20 px-4 text-center border-2 border-dashed border-border-color rounded-2xl bg-card-bg/30">
              <div className="w-16 h-16 bg-secondary-bg flex items-center justify-center rounded-full mb-4">
                <Building2 size={32} className="text-muted-text opacity-50" />
              </div>
              <h3 className="text-lg font-semibold text-primary-text mb-2">No workspaces found</h3>
              <p className="text-sm text-secondary-text max-w-sm leading-relaxed">
                {searchQuery ? "We couldn't find any organizations matching your search." : "You haven't joined any organizations yet. Create one to get started."}
              </p>
            </div>
          )}
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 animate-in fade-in duration-200">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-md" onClick={() => setIsModalOpen(false)} />
          <div className="relative w-full max-w-md rounded-2xl bg-card-bg shadow-2xl border border-border-color p-8">
            <h2 className="text-2xl font-bold text-primary-text mb-1">Create Organization</h2>
            <p className="text-sm text-secondary-text mb-6">Setup a new workspace environment.</p>
            
            <form onSubmit={handleCreateOrg} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-primary-text mb-2">Organization Name *</label>
                <input
                  type="text"
                  required
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  placeholder="e.g. Acme Corp"
                  className="w-full px-4 py-3 rounded-xl border border-border-color bg-secondary-bg text-sm text-primary-text focus:outline-none focus:ring-2 focus:ring-accent-primary/50 transition-shadow"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-primary-text mb-2">Billing Email (Optional)</label>
                <input
                  type="email"
                  value={newOrgEmail}
                  onChange={(e) => setNewOrgEmail(e.target.value)}
                  placeholder="billing@acme.com"
                  className="w-full px-4 py-3 rounded-xl border border-border-color bg-secondary-bg text-sm text-primary-text focus:outline-none focus:ring-2 focus:ring-accent-primary/50 transition-shadow"
                />
              </div>
              
              <div className="flex gap-3 pt-6">
                <Button type="button" variant="secondary" fullWidth onClick={() => setIsModalOpen(false)} className="py-2.5">
                  Cancel
                </Button>
                <Button type="submit" variant="primary" fullWidth disabled={createMutation.isPending} className="py-2.5">
                  {createMutation.isPending ? 'Creating...' : 'Create Workspace'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
