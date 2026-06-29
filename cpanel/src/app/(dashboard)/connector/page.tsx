'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  HardDrive,
  Database,
  ChevronDown,
  X,
  Plus,
  Search,
  Filter,
  Layers
} from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { useConnectorsHooks, Connector } from '@/hooks/api/useConnectors';
import { useCredentialsHooks, Credential } from '@/hooks/api/useCredentials';
import { useAppStore } from '@/store/useAppStore';
import { Skeleton } from '@/components/ui/Skeleton';
import toast from 'react-hot-toast';

interface UIMetaDef {
  name: string;
  provider: string;
  icon: any; // using any for lucide icon
  colorBase: string;
}

const UI_META: Record<string, UIMetaDef> = {
  google_drive: { name: 'Google Drive', provider: 'Google', icon: HardDrive, colorBase: 'blue' },
  postgres: { name: 'PostgreSQL', provider: 'PostgreSQL', icon: Database, colorBase: 'indigo' },
  mysql: { name: 'MySQL', provider: 'MySQL', icon: Database, colorBase: 'indigo' },
};

export default function ConnectorPage() {
  const router = useRouter();
  const { activeOrganizationId } = useAppStore();
  const { useConnectorsQuery, useAddConnectorMutation, useUpdateConnectorMutation, useSyncConnectorMutation } = useConnectorsHooks();
  const { useCredentialsQuery } = useCredentialsHooks();

  const { data: dbConnectors = [], isLoading: isLoadingConnectors } = useConnectorsQuery(activeOrganizationId);
  const { data: credentials = [] } = useCredentialsQuery(activeOrganizationId);

  const addConnectorMutation = useAddConnectorMutation();
  const updateConnectorMutation = useUpdateConnectorMutation();
  const syncConnectorMutation = useSyncConnectorMutation();

  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'connectors' | 'test'>('connectors');
  const [selectedCredentialId, setSelectedCredentialId] = useState<string>('');
  const [localSyncingIds, setLocalSyncingIds] = useState<string[]>([]);

  // Clear local syncing state if the real DB status has caught up and shows 'syncing' or 'synced' or 'failed'
  useEffect(() => {
    if (localSyncingIds.length === 0) return;

    const newIds = localSyncingIds.filter(id => {
      const conn = dbConnectors.find((c: Connector) => c.id === id);
      // Keep in local state only if the DB still hasn't registered it as syncing, synced, or failed
      return conn && conn.sync_status !== 'syncing' && conn.sync_status !== 'synced' && conn.sync_status !== 'failed';
    });

    if (newIds.length !== localSyncingIds.length) {
      setLocalSyncingIds(newIds);
    }
  }, [dbConnectors, localSyncingIds]);

  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  const filteredConnectors = dbConnectors.filter((c: Connector) => {
    const matchesSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          c.connector_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterStatus === 'all' || c.status === filterStatus;
    return matchesSearch && matchesType;
  });

  // Sync static Connectors to DB if they don't exist
  useEffect(() => {
    if (activeOrganizationId && !isLoadingConnectors && dbConnectors) {
      Object.entries(UI_META).forEach(([connector_id, meta]) => {
        if (!dbConnectors.some((c: Connector) => c.connector_id === connector_id)) {
          addConnectorMutation.mutate({
            organization_id: activeOrganizationId,
            connector_id,
            name: meta.name,
            provider: meta.provider,
            status: 'disabled',
            credential_id: null
          });
        }
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrganizationId, isLoadingConnectors, dbConnectors]);


  const handleToggle = async (connector: Connector) => {
    if (connector.status !== 'enabled') {
      // Opening modal to configure before enabling
      setSelectedConnector(connector);
      setSelectedCredentialId(connector.credential_id || '');
      setIsModalOpen(true);
    } else {
      // Disable directly
      updateConnectorMutation.mutate({ id: connector.id, updates: { status: 'disabled', credential_id: null } });
    }
  };

  const handleSaveAndEnable = async () => {
    if (selectedConnector) {
      if (!selectedCredentialId) {
        toast.error("Please select a credential.");
        return;
      }
      try {
        await updateConnectorMutation.mutateAsync({
          id: selectedConnector.id,
          updates: {
            status: 'enabled',
            credential_id: selectedCredentialId || null
          }
        });
        
        // Auto-sync immediately after enabling
        await syncConnectorMutation.mutateAsync(selectedConnector.id);
        toast.success(`${selectedConnector.name} connector enabled and data sync started!`);
      } catch (e: unknown) {
        console.error(e);
        toast.error(`Failed to enable ${selectedConnector.name} connector.`);
      }
      
      setIsModalOpen(false);
      setSelectedConnector(null);
    }
  };

  const availableCredentials = selectedConnector
    ? (selectedConnector.provider.toLowerCase() === 'google'
      ? credentials.filter(c => c.provider.toLowerCase() === 'google')
      : credentials.filter(c => c.provider.toLowerCase() === selectedConnector.provider.toLowerCase()))
    : [];

  const getColorClasses = (colorBase: string) => {
    return { 
      bg: 'bg-accent-primary/10', 
      text: 'text-accent-primary', 
      shadow: 'shadow-[0_0_20px_rgba(91,106,248,0.15)]', 
      border: 'border-accent-primary/20', 
      cardBorder: 'border-accent-primary/20' 
    };
  };

  return (
    <div className="flex flex-col gap-8 h-full">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="m-0 text-2xl font-bold text-primary-text tracking-tight">Connectors</h1>
          <p className="m-0 mt-1 text-sm text-secondary-text">Enable connectors and bind them to credentials.</p>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row items-center gap-4 bg-secondary-bg p-2 rounded-xl border border-border-color">
        <div className="flex-1 w-full relative">
          <Input
            placeholder="Search connectors by name or ID..."
            icon={<Search size={18} />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-transparent border-none shadow-none focus:ring-0"
          />
        </div>
        <div className="h-8 w-px bg-border-color hidden sm:block" />
        <div className="flex items-center gap-2 pr-2 w-full sm:w-auto">
          <div className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-secondary-text">
            <Filter size={16} />
            Filters
          </div>
          <div className="flex bg-tertiary-bg p-1 rounded-lg">
            <button onClick={() => setFilterStatus('all')} className={`cursor-pointer border-none px-3 py-1.5 text-xs font-medium transition-all rounded-md ${filterStatus === 'all' ? 'bg-card-bg shadow-sm text-primary-text' : 'text-secondary-text hover:text-primary-text bg-transparent'}`}>All</button>
            <button onClick={() => setFilterStatus('enabled')} className={`cursor-pointer border-none px-3 py-1.5 text-xs font-medium transition-all rounded-md ${filterStatus === 'enabled' ? 'bg-card-bg shadow-sm text-primary-text' : 'text-secondary-text hover:text-primary-text bg-transparent'}`}>Enabled</button>
            <button onClick={() => setFilterStatus('disabled')} className={`cursor-pointer border-none px-3 py-1.5 text-xs font-medium transition-all rounded-md ${filterStatus === 'disabled' ? 'bg-card-bg shadow-sm text-primary-text' : 'text-secondary-text hover:text-primary-text bg-transparent'}`}>Disabled</button>
          </div>
        </div>
      </div>

      {!activeOrganizationId ? (
        <div className="text-center p-8 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 rounded-xl">
          Please select an Organization first.
        </div>
      ) : isLoadingConnectors ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="flex flex-col bg-card-bg border border-border-color rounded-[16px] p-6">
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-4">
                  <Skeleton className="w-12 h-12 rounded-[12px]" />
                  <div>
                    <Skeleton className="h-5 w-24 mb-1" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                </div>
                <Skeleton className="w-12 h-6 rounded-full" />
              </div>
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-3/4 mb-6" />
              <div className="mt-auto pt-6 border-t border-border-color flex justify-between">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-16" />
              </div>
            </div>
          ))}
        </div>
      ) : activeTab === 'connectors' && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-6">
          {filteredConnectors.map((connector: Connector, idx: number) => {
            const meta = UI_META[connector.connector_id] || UI_META['google_drive'];
            const colors = getColorClasses(meta.colorBase);
            const Icon = meta.icon;
            const isEnabled = connector.status === 'enabled';
            const isMapped = !!connector.credential_id;

            return (
              <div
                key={connector.id}
                className={`group relative flex flex-col bg-card-bg backdrop-blur-2xl backdrop-saturate-[180%] shadow-[0_4px_24px_rgba(0,0,0,0.02)] border border-border-color rounded-[16px] p-6 transition-all duration-300 hover:border-border-hover hover:bg-card-hover hover:shadow-[0_12px_40px_rgba(0,0,0,0.08)] hover:-translate-y-1 animate-cascade-item`}
                style={{ animationDelay: `${idx * 80}ms` }}
              >
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-[12px] bg-accent-primary/10 backdrop-blur-md flex items-center justify-center text-accent-primary border border-accent-primary/20 shadow-[0_0_20px_rgba(91,106,248,0.15)] transition-all duration-300 group-hover:bg-accent-primary/20 group-hover:scale-105 group-hover:shadow-[0_0_25px_rgba(91,106,248,0.25)]`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="m-0 text-[18px] font-bold text-primary-text tracking-tight group-hover:text-accent-primary transition-colors">{connector.name}</h3>
                      <p className="m-0 mt-1 text-[11px] font-mono text-accent-primary/80 uppercase tracking-wider">{connector.connector_id}</p>
                    </div>
                  </div>

                  <button
                    onClick={() => handleToggle(connector)}
                    className={`relative w-12 h-6 rounded-full transition-colors duration-300 shrink-0 ${isEnabled ? 'bg-accent-primary' : 'bg-gray-300 dark:bg-gray-700'
                      }`}
                  >
                    <div className={`absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform duration-300 shadow-sm ${isEnabled ? 'translate-x-6' : 'translate-x-0'
                      }`} />
                  </button>
                </div>

                <div className="flex items-center gap-2 mb-6">
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-black/5 dark:bg-white/10 text-gray-700 dark:text-gray-300 border border-black/5 dark:border-white/5">
                    {connector.provider}
                  </span>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium border ${isEnabled
                    ? 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20'
                    : 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20'
                    }`}>
                    {isEnabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>

                <p className={`text-sm font-medium ${isMapped ? 'text-gray-800 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'}`}>
                  {isMapped ? (
                    <span className="flex items-center gap-1.5">
                      Mapped to: <span className="text-accent-primary bg-accent-primary/10 px-2 py-0.5 rounded-md">{credentials.find(c => c.id === connector.credential_id)?.name || 'Unknown Credential'}</span>
                    </span>
                  ) : 'No credential mapped yet.'}
                </p>

                {connector.status === 'enabled' && (
                  <div className="mt-4 pt-4 border-t border-black/5 dark:border-white/5 flex flex-col gap-3">
                    {/* Sync Status Row */}
                    <div className="flex items-center justify-between">
                      <div className="flex flex-col">
                        <span className="text-xs text-gray-500 dark:text-gray-400">Sync Status</span>
                        <span className={`text-sm font-semibold capitalize ${connector.sync_status === 'synced' ? 'text-emerald-600 dark:text-emerald-400' :
                          connector.sync_status === 'syncing' ? 'text-blue-600 dark:text-blue-400 animate-pulse' :
                            connector.sync_status === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-gray-500'
                          }`}>
                          {connector.sync_status || 'Pending'}
                        </span>
                      </div>
                      <button
                        onClick={() => {
                          setLocalSyncingIds(prev => [...prev, connector.id]);
                          syncConnectorMutation.mutate(connector.id);
                        }}
                        disabled={connector.sync_status === 'syncing' || localSyncingIds.includes(connector.id)}
                        className="cursor-pointer disabled:cursor-not-allowed px-3 py-1.5 rounded-lg text-xs font-medium bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-gray-900 dark:text-white transition-colors disabled:opacity-50"
                      >
                        {connector.sync_status === 'syncing' || localSyncingIds.includes(connector.id) ? 'Syncing...' : 'Sync Data'}
                      </button>
                    </div>

                    {/* Manage Metadata button — only for DB connectors that have been synced */}
                    {connector.connector_id !== 'google_drive' && connector.sync_status === 'synced' && (
                      <button
                        onClick={() => router.push(`/connector/metadata?id=${connector.id}`)}
                        className="cursor-pointer w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold border border-accent-primary/30 bg-accent-primary/5 text-accent-primary hover:bg-accent-primary/15 hover:border-accent-primary/50 transition-all"
                      >
                        <Layers size={13} />
                        Manage Schema Metadata
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {isModalOpen && selectedConnector && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 animate-in fade-in">
          <div
            className="absolute inset-0 bg-black/20 dark:bg-black/60 backdrop-blur-sm"
            onClick={() => setIsModalOpen(false)}
          />
          <div className="relative w-full max-w-lg rounded-3xl bg-white dark:bg-[#0f172a] shadow-2xl border border-black/10 dark:border-white/10 overflow-hidden animate-in zoom-in-95 duration-300 slide-in-from-bottom-8">
            <div className="p-6 md:p-8">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Enable {selectedConnector.name}</h2>
                  <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Select an existing credential, or add a new one.</p>
                </div>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-gray-500 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Display name</label>
                  <input
                    type="text"
                    defaultValue={selectedConnector.name}
                    className="w-full px-4 py-3 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black/20 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
                    readOnly
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Credential</label>
                  <div className="relative">
                    <select
                      value={selectedCredentialId}
                      onChange={(e) => setSelectedCredentialId(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black/20 text-gray-900 dark:text-white appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
                    >
                      <option value="">Select credential...</option>
                      {availableCredentials.map((cred: Credential) => (
                        <option key={cred.id} value={cred.id}>{cred.name} ({cred.status})</option>
                      ))}
                    </select>
                    <ChevronDown className="w-5 h-5 absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                  {availableCredentials.length === 0 && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                      No credentials found for provider `{selectedConnector.provider}`.
                    </p>
                  )}
                </div>

                <a href="/credentials" className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-gray-900 dark:text-white transition-colors text-sm font-medium">
                  <Plus className="w-4 h-4" /> Go to Credentials
                </a>
              </div>
            </div>

            <div className="px-6 py-5 bg-gray-50 dark:bg-black/20 border-t border-black/5 dark:border-white/5 flex items-center justify-end gap-3">
              <button
                onClick={() => setIsModalOpen(false)}
                className="px-6 py-2.5 rounded-xl font-medium text-gray-700 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAndEnable}
                disabled={!selectedCredentialId}
                className="px-6 py-2.5 rounded-xl font-medium bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-0.5 disabled:opacity-50"
              >
                Save and Enable
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
