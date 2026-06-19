'use client';

import React, { useState } from 'react';
import { 
  Calendar, 
  Fingerprint, 
  HardDrive, 
  Sparkles, 
  Database, 
  Bot, 
  Mail,
  ChevronDown,
  X,
  Plus
} from 'lucide-react';
import { useIntegrationStore, Connector } from '@/store/useIntegrationStore';
import { 
  useDatabaseConnections, 
  useUpdateDatabaseConnection, 
  useSyncDatabaseConnection 
} from '@/hooks/api/useDatabaseConnections';
import toast from 'react-hot-toast';

export default function ConnectorPage() {
  const { connectors, credentials, updateConnector } = useIntegrationStore();
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'connectors' | 'test'>('connectors');
  const [selectedCredentialId, setSelectedCredentialId] = useState<string>('');

  // API Hooks
  const { data: dbConnections, isLoading: isDbLoading } = useDatabaseConnections();
  const updateDbConn = useUpdateDatabaseConnection();
  const syncDbConn = useSyncDatabaseConnection();

  // Find active / mapped database connections
  const activePgConn = dbConnections?.find(c => c.database_type === 'postgresql' && c.is_active);
  const activeMySqlConn = dbConnections?.find(c => c.database_type === 'mysql' && c.is_active);

  // Map PostgreSQL and MySQL connectors based on real backend data
  const derivedConnectors = connectors.map(conn => {
    if (conn.id === 'postgres') {
      return {
        ...conn,
        enabled: !!activePgConn,
        credentialMapped: !!activePgConn,
        credentialId: activePgConn?.id,
        syncStatus: activePgConn?.sync_status,
        lastSyncedAt: activePgConn?.last_synced_at
      };
    }
    if (conn.id === 'mysql') {
      return {
        ...conn,
        enabled: !!activeMySqlConn,
        credentialMapped: !!activeMySqlConn,
        credentialId: activeMySqlConn?.id,
        syncStatus: activeMySqlConn?.sync_status,
        lastSyncedAt: activeMySqlConn?.last_synced_at
      };
    }
    return conn;
  });

  const handleToggle = async (connector: Connector) => {
    if (!connector.enabled) {
      // Opening modal to configure before enabling
      setSelectedConnector(connector);
      setSelectedCredentialId('');
      setIsModalOpen(true);
    } else {
      // Disable directly
      if (connector.id === 'postgres' || connector.id === 'mysql') {
        const activeConnId = connector.credentialId;
        if (activeConnId) {
          try {
            await updateDbConn.mutateAsync({ id: activeConnId, data: { is_active: false } });
            toast.success(`${connector.name} connector disabled.`);
          } catch (e) {
            console.error(e);
            toast.error(`Failed to disable ${connector.name} connector.`);
          }
        }
      } else {
        updateConnector(connector.id, { enabled: false, credentialMapped: false, credentialId: undefined });
      }
    }
  };

  const handleSaveAndEnable = async () => {
    if (selectedConnector) {
      if (selectedConnector.id === 'postgres' || selectedConnector.id === 'mysql') {
        if (!selectedCredentialId) {
          toast.error("Please select a credential.");
          return;
        }
        try {
          await updateDbConn.mutateAsync({ id: selectedCredentialId, data: { is_active: true } });
          // Start the schema sync immediately
          await syncDbConn.mutateAsync(selectedCredentialId);
          toast.success(`${selectedConnector.name} connector enabled and schema sync started!`);
        } catch (e) {
          console.error(e);
          toast.error(`Failed to enable ${selectedConnector.name} connector.`);
        }
      } else {
        updateConnector(selectedConnector.id, { 
          enabled: true, 
          credentialMapped: !!selectedCredentialId,
          credentialId: selectedCredentialId || undefined
        });
      }
      setIsModalOpen(false);
      setSelectedConnector(null);
    }
  };

  // Filter credentials matching the selected connector's provider
  const availableCredentials = selectedConnector 
    ? (selectedConnector.provider.toLowerCase() === 'google'
        ? credentials.filter(c => c.provider.toLowerCase() === 'google')
        : (dbConnections || []).map(db => ({
            id: db.id,
            name: `${db.name} (${db.host})`,
            provider: db.database_type === 'postgresql' ? 'PostgreSQL' : 'MySQL',
            status: db.sync_status || 'pending',
            database_type: db.database_type
          })).filter(c => {
            if (selectedConnector.id === 'postgres') return c.database_type === 'postgresql';
            if (selectedConnector.id === 'mysql') return c.database_type === 'mysql';
            return false;
          }))
    : [];

  const getColorClasses = (colorBase: string) => {
    const map: Record<string, { bg: string, text: string, shadow: string, border: string }> = {
      blue: { bg: 'bg-blue-500/10 dark:bg-blue-500/20', text: 'text-blue-600 dark:text-blue-400', shadow: 'shadow-blue-500/20', border: 'border-blue-500/20' },
      purple: { bg: 'bg-purple-500/10 dark:bg-purple-500/20', text: 'text-purple-600 dark:text-purple-400', shadow: 'shadow-purple-500/20', border: 'border-purple-500/20' },
      orange: { bg: 'bg-orange-500/10 dark:bg-orange-500/20', text: 'text-orange-600 dark:text-orange-400', shadow: 'shadow-orange-500/20', border: 'border-orange-500/20' },
      indigo: { bg: 'bg-indigo-500/10 dark:bg-indigo-500/20', text: 'text-indigo-600 dark:text-indigo-400', shadow: 'shadow-indigo-500/20', border: 'border-indigo-500/20' },
      cyan: { bg: 'bg-cyan-500/10 dark:bg-cyan-500/20', text: 'text-cyan-600 dark:text-cyan-400', shadow: 'shadow-cyan-500/20', border: 'border-cyan-500/20' },
    };
    return map[colorBase] || map.blue;
  };

  return (
    <div className="min-h-full p-4 md:p-8 lg:p-12 relative">
      
      {/* Header Section */}
      <div className="mb-10 max-w-6xl mx-auto">
        <h1 className="text-4xl font-extrabold tracking-tight mb-2 bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400">
          Connectors
        </h1>
        <p className="text-gray-600 dark:text-gray-400 text-lg max-w-2xl leading-relaxed">
          Enable connectors and bind them to credentials. Turning on always requires selecting a credential.
        </p>

        {/* Tabs */}
        <div className="flex items-center gap-2 mt-8">
          <button 
            onClick={() => setActiveTab('connectors')}
            className={`px-6 py-2.5 rounded-full font-medium text-sm transition-all duration-300 ${
              activeTab === 'connectors' 
                ? 'bg-black dark:bg-white text-white dark:text-gray-900 shadow-xl shadow-black/10 dark:shadow-white/10 scale-105' 
                : 'bg-black/5 dark:bg-white/5 text-gray-600 dark:text-gray-400 hover:bg-black/10 dark:hover:bg-white/10'
            }`}
          >
            Connectors
          </button>
          <button 
            onClick={() => setActiveTab('test')}
            className={`px-6 py-2.5 rounded-full font-medium text-sm transition-all duration-300 ${
              activeTab === 'test' 
                ? 'bg-black dark:bg-white text-white dark:text-gray-900 shadow-xl shadow-black/10 dark:shadow-white/10 scale-105' 
                : 'bg-black/5 dark:bg-white/5 text-gray-600 dark:text-gray-400 hover:bg-black/10 dark:hover:bg-white/10'
            }`}
          >
            Test OAuth
          </button>
        </div>
      </div>

      {/* Grid Section */}
      {activeTab === 'connectors' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
          {derivedConnectors.map(connector => {
            const colors = getColorClasses(connector.colorBase);
            const Icon = connector.icon;
            
            return (
              <div 
                key={connector.id} 
                className={`group relative p-6 rounded-3xl bg-white/50 dark:bg-[#111113]/50 backdrop-blur-xl border transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl ${
                  connector.enabled 
                    ? `border-${connector.colorBase}-500/30 dark:border-${connector.colorBase}-500/20 shadow-lg ${colors.shadow}` 
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
                      <p className="text-gray-500 dark:text-gray-400 text-sm font-mono">{connector.id}</p>
                    </div>
                  </div>
                  
                  {/* Custom Toggle Switch */}
                  <button
                    onClick={() => handleToggle(connector)}
                    className={`relative w-12 h-6 rounded-full transition-colors duration-300 shrink-0 ${
                      connector.enabled ? 'bg-blue-600 dark:bg-blue-500' : 'bg-gray-300 dark:bg-gray-700'
                    }`}
                  >
                    <div className={`absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform duration-300 shadow-sm ${
                      connector.enabled ? 'translate-x-6' : 'translate-x-0'
                    }`} />
                  </button>
                </div>

                <div className="flex items-center gap-2 mb-6">
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-black/5 dark:bg-white/10 text-gray-700 dark:text-gray-300 border border-black/5 dark:border-white/5">
                    {connector.provider}
                  </span>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium border ${
                    connector.enabled 
                      ? 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20' 
                      : 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20'
                  }`}>
                    {connector.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>

                <p className={`text-sm ${connector.credentialMapped ? 'text-gray-800 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'}`}>
                  {connector.credentialMapped ? 'Credentials successfully mapped.' : 'No credential mapped yet.'}
                </p>

                {connector.enabled && (connector.id === 'postgres' || connector.id === 'mysql') && (
                  <div className="mt-4 pt-4 border-t border-black/5 dark:border-white/5 flex items-center justify-between">
                    <div className="flex flex-col">
                      <span className="text-xs text-gray-500 dark:text-gray-400">Sync Status</span>
                      <span className={`text-sm font-semibold capitalize ${
                        connector.syncStatus === 'synced' ? 'text-emerald-600 dark:text-emerald-400' :
                        connector.syncStatus === 'syncing' ? 'text-blue-600 dark:text-blue-400 animate-pulse' :
                        connector.syncStatus === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-gray-500'
                      }`}>
                        {connector.syncStatus || 'Pending'}
                      </span>
                    </div>
                    <button
                      onClick={() => connector.credentialId && syncDbConn.mutate(connector.credentialId)}
                      disabled={connector.syncStatus === 'syncing'}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-gray-900 dark:text-white transition-colors disabled:opacity-50"
                    >
                      {connector.syncStatus === 'syncing' ? 'Syncing...' : 'Sync Schema'}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Configuration Modal */}
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
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Description</label>
                  <textarea 
                    placeholder="Optional details for admins"
                    rows={3}
                    className="w-full px-4 py-3 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black/20 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow resize-none placeholder:text-gray-400 dark:placeholder:text-gray-600"
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
                      {availableCredentials.map(cred => (
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

                <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-gray-900 dark:text-white transition-colors text-sm font-medium">
                  <Plus className="w-4 h-4" /> Add New Credential
                </button>
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
                className="px-6 py-2.5 rounded-xl font-medium bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-0.5"
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
