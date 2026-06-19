'use client';

import React, { useState, useEffect } from 'react';
import {
  HardDrive,
  Database,
  ChevronDown,
  X,
  Plus
} from 'lucide-react';
import { useConnectorsHooks, Connector } from '@/hooks/api/useConnectors';
import { useCredentialsHooks, Credential } from '@/hooks/api/useCredentials';
import { useAppStore } from '@/store/useAppStore';
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
        
        // If it's a database, auto-sync
        if (selectedConnector.connector_id === 'postgres' || selectedConnector.connector_id === 'mysql') {
          await syncConnectorMutation.mutateAsync(selectedConnector.id);
          toast.success(`${selectedConnector.name} connector enabled and schema sync started!`);
        } else {
          toast.success(`${selectedConnector.name} connector enabled!`);
        }
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
    const map: Record<string, any> = {
      blue: { bg: 'bg-blue-500/10 dark:bg-blue-500/20', text: 'text-blue-600 dark:text-blue-400', shadow: 'shadow-blue-500/20', border: 'border-blue-500/20' },
      indigo: { bg: 'bg-indigo-500/10 dark:bg-indigo-500/20', text: 'text-indigo-600 dark:text-indigo-400', shadow: 'shadow-indigo-500/20', border: 'border-indigo-500/20' },
    };
    return map[colorBase] || map.blue;
  };

  return (
    <div className="min-h-full p-4 md:p-8 lg:p-12 relative">
      <div className="mb-10 max-w-6xl mx-auto">
        <h1 className="text-4xl font-extrabold tracking-tight mb-2 bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400">
          Connectors
        </h1>
        <p className="text-gray-600 dark:text-gray-400 text-lg max-w-2xl leading-relaxed">
          Enable connectors and bind them to credentials.
        </p>

        <div className="flex items-center gap-2 mt-8">
          <button
            onClick={() => setActiveTab('connectors')}
            className={`px-6 py-2.5 rounded-full font-medium text-sm transition-all duration-300 ${activeTab === 'connectors'
              ? 'bg-black dark:bg-white text-white dark:text-gray-900 shadow-xl shadow-black/10 dark:shadow-white/10 scale-105'
              : 'bg-black/5 dark:bg-white/5 text-gray-600 dark:text-gray-400 hover:bg-black/10 dark:hover:bg-white/10'
              }`}
          >
            Connectors
          </button>
        </div>
      </div>

      {!activeOrganizationId ? (
        <div className="text-center p-8 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 rounded-xl">
          Please select an Organization first.
        </div>
      ) : activeTab === 'connectors' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
          {dbConnectors.map((connector: Connector) => {
            const meta = UI_META[connector.connector_id] || UI_META['google_drive'];
            const colors = getColorClasses(meta.colorBase);
            const Icon = meta.icon;
            const isEnabled = connector.status === 'enabled';
            const isMapped = !!connector.credential_id;

            return (
              <div
                key={connector.id}
                className={`group relative p-6 rounded-3xl bg-white/50 dark:bg-[#111113]/50 backdrop-blur-xl border transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl ${isEnabled
                  ? `border-${meta.colorBase}-500/30 dark:border-${meta.colorBase}-500/20 shadow-lg ${colors.shadow}`
                  : 'border-black/10 dark:border-white/10 hover:border-black/20 dark:hover:border-white/20'
                  }`}
              >
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border ${colors.bg} ${colors.text} ${colors.border}`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white text-lg">{connector.name}</h3>
                      <p className="text-gray-500 dark:text-gray-400 text-sm font-mono">{connector.connector_id}</p>
                    </div>
                  </div>

                  <button
                    onClick={() => handleToggle(connector)}
                    className={`relative w-12 h-6 rounded-full transition-colors duration-300 shrink-0 ${isEnabled ? 'bg-blue-600 dark:bg-blue-500' : 'bg-gray-300 dark:bg-gray-700'
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

                <p className={`text-sm ${isMapped ? 'text-gray-800 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'}`}>
                  {isMapped ? 'Credentials successfully mapped.' : 'No credential mapped yet.'}
                </p>

                {connector.status === 'enabled' && (connector.connector_id === 'postgres' || connector.connector_id === 'mysql') && (
                  <div className="mt-4 pt-4 border-t border-black/5 dark:border-white/5 flex items-center justify-between">
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
                      onClick={() => syncConnectorMutation.mutate(connector.id)}
                      disabled={connector.sync_status === 'syncing'}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-gray-900 dark:text-white transition-colors disabled:opacity-50"
                    >
                      {connector.sync_status === 'syncing' ? 'Syncing...' : 'Sync Schema'}
                    </button>
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
