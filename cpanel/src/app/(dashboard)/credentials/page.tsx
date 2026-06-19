'use client';

import React, { useState } from 'react';
import {
  Plus,
  KeyRound,
  Search,
  Trash2,
  X,
  ChevronDown,
  ShieldCheck,
  Globe
} from 'lucide-react';
import { useIntegrationStore } from '@/store/useIntegrationStore';
import { useDatabaseConnections, useCreateDatabaseConnection } from '@/hooks/api/useDatabaseConnections';

const PROVIDERS = ['Google', 'PostgreSQL', 'MySQL'];

export default function CredentialsPage() {
  const { credentials, addCredential, deleteCredential } = useIntegrationStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Modal State
  const [provider, setProvider] = useState('');
  const [name, setName] = useState('');
  
  // Database State
  const [dbHost, setDbHost] = useState('');
  const [dbPort, setDbPort] = useState('5432');
  const [dbUser, setDbUser] = useState('');
  const [dbPass, setDbPass] = useState('');
  const [dbName, setDbName] = useState('');
  const [dbSchema, setDbSchema] = useState('');

  // API Hooks
  const { data: dbConnections, isLoading } = useDatabaseConnections();
  const createDbConn = useCreateDatabaseConnection();

  // Merge local credentials and db connections for display
  const allCredentials = [
    ...credentials,
    ...(dbConnections || []).map(db => ({
      id: db.id,
      name: db.name,
      provider: db.database_type === 'postgresql' ? 'PostgreSQL' : 'MySQL',
      status: db.sync_status === 'synced' ? 'Active' : db.sync_status || 'Pending',
      lastUsed: new Date(db.last_synced_at || db.created_at)
    }))
  ];

  const filteredCredentials = allCredentials.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.provider.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreate = async () => {
    if (name && provider) {
      if (provider === 'PostgreSQL' || provider === 'MySQL') {
        try {
          await createDbConn.mutateAsync({
            name,
            database_type: provider.toLowerCase(),
            host: dbHost,
            port: parseInt(dbPort),
            username: dbUser,
            password: dbPass,
            database_name: dbName,
            schema_name: dbSchema || null
          });
        } catch (e) {
          console.error("Failed to create database connection", e);
          return;
        }
      } else {
        addCredential({
          name,
          provider,
        });
      }
      setIsModalOpen(false);
      setName('');
      setProvider('');
      setDbHost('');
      setDbPort('5432');
      setDbUser('');
      setDbPass('');
      setDbName('');
      setDbSchema('');
    }
  };

  return (
    <div className="min-h-full p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-gray-200 dark:border-white/10 pb-6">
          <div>
            <h1 className="text-3xl font-semibold text-gray-900 dark:text-white tracking-tight">
              Credentials
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">
              Manage provider credentials from the admin backend securely.
            </p>
          </div>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" /> Add Credential
          </button>
        </div>

        {/* Filters Section */}
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search credentials..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow"
            />
          </div>
          <div className="w-full md:w-48 relative">
            <select className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white appearance-none focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow">
              <option value="all">All Types</option>
              {PROVIDERS.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <ChevronDown className="w-4 h-4 absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Credentials List */}
        <div className="rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden flex flex-col">
          <div className="p-5 flex justify-between items-center border-b border-gray-100 dark:border-white/5">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-gray-400" />
              Credential List
            </h2>
            <span className="text-xs font-medium text-gray-500 bg-gray-100 dark:bg-white/10 px-2.5 py-1 rounded-full">
              {filteredCredentials.length} total
            </span>
          </div>

          <div className="flex-1 p-0 overflow-x-auto">
            {filteredCredentials.length > 0 ? (
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead>
                  <tr className="bg-gray-50/50 dark:bg-white/5 border-b border-gray-100 dark:border-white/5">
                    <th className="px-5 py-3 font-medium text-gray-500 dark:text-gray-400">Credential Name</th>
                    <th className="px-5 py-3 font-medium text-gray-500 dark:text-gray-400">Provider</th>
                    <th className="px-5 py-3 font-medium text-gray-500 dark:text-gray-400">Status</th>
                    <th className="px-5 py-3 font-medium text-gray-500 dark:text-gray-400">Last Used</th>
                    <th className="px-5 py-3 font-medium text-gray-500 dark:text-gray-400 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-white/5">
                  {filteredCredentials.map(cred => (
                    <tr key={cred.id} className="hover:bg-gray-50 dark:hover:bg-white/5 transition-colors group">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-3">
                          <span className="font-medium text-gray-900 dark:text-white">{cred.name}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-300 border border-gray-200 dark:border-white/5">
                          <Globe className="w-3 h-3" />
                          {cred.provider}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
                          <ShieldCheck className="w-3 h-3" />
                          {cred.status}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-gray-500 dark:text-gray-400">
                        {cred.lastUsed ? cred.lastUsed.toLocaleDateString() : 'Never'}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => deleteCredential(cred.id)}
                          className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                          title="Delete Credential"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="px-5 py-12 flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 rounded-xl bg-gray-50 dark:bg-white/5 flex items-center justify-center mb-4 border border-gray-100 dark:border-white/5">
                  <KeyRound className="w-6 h-6 text-gray-400" />
                </div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">No credentials found</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm">
                  You haven't added any external credentials yet. Click the button above to securely add your first credential.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Add Credential Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center px-4 animate-in fade-in duration-200">
            <div
              className="absolute inset-0 bg-black/20 dark:bg-black/60 backdrop-blur-sm"
              onClick={() => setIsModalOpen(false)}
            />
            <div className="relative w-full max-w-lg rounded-xl bg-white dark:bg-[#111113] shadow-xl border border-gray-200 dark:border-white/10 overflow-hidden animate-in zoom-in-95 duration-200">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Add Credential</h2>
                    <p className="text-gray-500 dark:text-gray-400 text-sm mt-0.5">Pick a provider and fill provider-specific fields.</p>
                  </div>
                  <button
                    onClick={() => setIsModalOpen(false)}
                    className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-gray-100 dark:hover:bg-white/10 text-gray-500 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Provider</label>
                    <div className="relative">
                      <select
                        value={provider}
                        onChange={(e) => setProvider(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white appearance-none focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow"
                      >
                        <option value="">Select provider...</option>
                        {PROVIDERS.map(p => (
                          <option key={p} value={p}>{p}</option>
                        ))}
                      </select>
                      <ChevronDown className="w-4 h-4 absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Credential Name</label>
                    <input
                      type="text"
                      placeholder="e.g. admin@company.com"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow"
                    />
                  </div>

                  {provider === 'Google' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Client ID *</label>
                        <input type="text" placeholder="Google OAuth client ID." className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Client Secret *</label>
                        <input type="password" placeholder="Google OAuth client secret." className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Redirect URI *</label>
                        <input type="text" defaultValue="{{CRD_CALLBACK_URL}}/google" readOnly className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 text-gray-500 dark:text-gray-400 focus:outline-none text-sm cursor-not-allowed" />
                      </div>
                    </>
                  )}

                  {(provider === 'PostgreSQL' || provider === 'MySQL') && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="col-span-2 md:col-span-1">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Host *</label>
                        <input value={dbHost} onChange={(e) => setDbHost(e.target.value)} type="text" placeholder="localhost" className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow" />
                      </div>
                      <div className="col-span-2 md:col-span-1">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Port *</label>
                        <input value={dbPort} onChange={(e) => setDbPort(e.target.value)} type="text" placeholder="5432" className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow" />
                      </div>
                      <div className="col-span-2 md:col-span-1">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Username *</label>
                        <input value={dbUser} onChange={(e) => setDbUser(e.target.value)} type="text" className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow" />
                      </div>
                      <div className="col-span-2 md:col-span-1">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Password *</label>
                        <input value={dbPass} onChange={(e) => setDbPass(e.target.value)} type="password" className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow" />
                      </div>
                      <div className="col-span-2 md:col-span-1">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Database *</label>
                        <input value={dbName} onChange={(e) => setDbName(e.target.value)} type="text" className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow" />
                      </div>
                      <div className="col-span-2 md:col-span-1">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Schema</label>
                        <input value={dbSchema} onChange={(e) => setDbSchema(e.target.value)} type="text" placeholder="public" className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow" />
                      </div>
                    </div>
                  )}

                  {provider !== 'Google' && provider !== 'PostgreSQL' && provider !== 'MySQL' && provider !== '' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">API Key / Secret</label>
                      <input
                        type="password"
                        placeholder="••••••••••••••••••••••••"
                        className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow"
                      />
                    </div>
                  )}
                </div>
              </div>

              <div className="px-6 py-4 bg-gray-50/80 dark:bg-white/5 border-t border-gray-200 dark:border-white/10 flex items-center justify-between">
                <button
                  type="button"
                  className="px-4 py-2 text-sm rounded-lg font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10 hover:bg-blue-100 dark:hover:bg-blue-500/20 transition-colors"
                >
                  Test Connection
                </button>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 text-sm rounded-lg font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreate}
                    disabled={!name || !provider}
                    className="px-4 py-2 text-sm rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors shadow-sm disabled:opacity-50"
                  >
                    Create Credential
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
