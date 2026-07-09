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
  Globe,
  RefreshCw,
  Loader2
} from 'lucide-react';
import { Skeleton } from '@/components/ui/Skeleton';
import { useCredentialsHooks, Credential } from '@/hooks/api/useCredentials';
import { useAppStore } from '@/store/useAppStore';
const PROVIDERS = ['Google', 'PostgreSQL', 'MySQL'];

export default function CredentialsPage() {
  const { activeOrganizationId } = useAppStore();
  const { useCredentialsQuery, useAddCredentialMutation, useDeleteCredentialMutation, useTestCredentialMutation, useGenerateGoogleOAuthUrlMutation, useRegenerateGoogleOAuthUrlMutation } = useCredentialsHooks();
  const { data: credentials = [], isLoading } = useCredentialsQuery(activeOrganizationId);

  const addCredentialMutation = useAddCredentialMutation();
  const deleteCredentialMutation = useDeleteCredentialMutation();
  const testCredentialMutation = useTestCredentialMutation();
  const generateGoogleOAuthUrlMutation = useGenerateGoogleOAuthUrlMutation();
  const regenerateGoogleOAuthUrlMutation = useRegenerateGoogleOAuthUrlMutation();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Delete Modal State
  const [credentialToDelete, setCredentialToDelete] = useState<string | null>(null);

  // Modal State
  const [provider, setProvider] = useState('');
  const [name, setName] = useState('');

  // Auth Data State
  const [authData, setAuthData] = useState<Record<string, any>>({});
  
  // Google OAuth State
  const [googleClientId, setGoogleClientId] = useState('');
  const [googleClientSecret, setGoogleClientSecret] = useState('');
  const [googleRedirectUri, setGoogleRedirectUri] = useState(
    typeof window !== 'undefined' ? `${window.location.origin}/google` : ''
  );

  // Database State
  const [dbHost, setDbHost] = useState('');
  const [dbPort, setDbPort] = useState('5432');
  const [dbUser, setDbUser] = useState('');
  const [dbPass, setDbPass] = useState('');
  const [dbName, setDbName] = useState('');
  const [dbSchema, setDbSchema] = useState('');

  const [filterType, setFilterType] = useState('all');

  const ITEMS_PER_PAGE = 10;
  const [currentPage, setCurrentPage] = useState(1);

  React.useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filterType]);

  const filteredCredentials = (credentials || []).filter((c: Credential) => {
    const matchesSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          c.provider.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'all' ? true : c.provider === filterType;
    return matchesSearch && matchesType;
  });

  const paginatedCredentials = filteredCredentials.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);
  const totalPages = Math.max(1, Math.ceil(filteredCredentials.length / ITEMS_PER_PAGE));

  const handleCreate = async () => {
    if (name && provider && activeOrganizationId) {
      if (provider === 'Google') {
        generateGoogleOAuthUrlMutation.mutate({
          name,
          organization_id: activeOrganizationId,
          client_id: googleClientId,
          client_secret: googleClientSecret,
          redirect_uri: googleRedirectUri
        }, {
          onSuccess: (data) => {
            window.location.href = data.auth_url;
          }
        });
        return; // Don't reset state or close modal, we're redirecting
      } else if (provider === 'PostgreSQL' || provider === 'MySQL') {
        addCredentialMutation.mutate({
          organization_id: activeOrganizationId,
          name,
          provider,
          auth_data: {
            host: dbHost,
            port: parseInt(dbPort),
            username: dbUser,
            password: dbPass,
            database: dbName,
            schema: dbSchema || null
          },
        });
      } else {
        addCredentialMutation.mutate({
          organization_id: activeOrganizationId,
          name,
          provider,
          auth_data: authData,
        });
      }
      setIsModalOpen(false);
      setName('');
      setProvider('');
      setAuthData({});
      setDbHost('');
      setDbPort('5432');
      setDbUser('');
      setDbPass('');
      setDbName('');
      setDbSchema('');
    }
  };

  const updateAuthData = (key: string, value: any) => {
    setAuthData(prev => ({ ...prev, [key]: value }));
  };

  const handleTestConnection = () => {
    let payloadAuthData = authData;
    if (provider === 'PostgreSQL' || provider === 'MySQL') {
      payloadAuthData = {
        host: dbHost,
        port: parseInt(dbPort),
        username: dbUser,
        password: dbPass,
        database: dbName,
        schema: dbSchema || null
      };
    }

    if (provider && Object.keys(payloadAuthData).length > 0) {
      testCredentialMutation.mutate({ provider, auth_data: payloadAuthData });
    }
  };

  return (
    <div className="flex flex-col gap-8 h-full">

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
            disabled={!activeOrganizationId}
            data-tour="credentials-create-button"
            className="flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors shadow-sm disabled:opacity-50"
          >
            <Plus className="w-4 h-4" /> Add Credential
          </button>
        </div>

        {!activeOrganizationId ? (
          <div className="text-center p-8 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 rounded-xl">
            Please select an Organization first.
          </div>
        ) : (
          <>
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
                <select 
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white appearance-none focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow">
                  <option value="all">All Types</option>
                  {PROVIDERS.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
            </div>

            {/* Credentials List */}
            <div data-tour="credentials-list" className="rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden flex flex-col">
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
                {isLoading ? (
                  <div className="flex flex-col p-4 gap-4">
                    {[1, 2, 3, 4, 5].map(i => (
                      <div key={i} className="flex items-center gap-4">
                        <Skeleton className="h-6 w-1/4" />
                        <Skeleton className="h-6 w-1/6" />
                        <Skeleton className="h-6 w-1/6" />
                        <Skeleton className="h-6 w-1/6" />
                        <Skeleton className="h-6 w-1/4" />
                      </div>
                    ))}
                  </div>
                ) : filteredCredentials.length > 0 ? (
                  <>
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
                      {paginatedCredentials.map((cred: Credential) => (
                        <tr key={cred.id} className="hover:bg-gray-50 dark:hover:bg-white/5 transition-colors group">
                          <td className="px-5 py-3.5">
                            <div className="flex flex-col">
                              <span className="font-medium text-gray-900 dark:text-white">{cred.name}</span>
                              {cred.display_info?.email ? (
                                <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{cred.display_info.email}</span>
                              ) : cred.display_info?.host ? (
                                <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{cred.display_info.username}@{cred.display_info.host}</span>
                              ) : null}
                            </div>
                          </td>
                          <td className="px-5 py-3.5">
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-300 border border-gray-200 dark:border-white/5">
                              <Globe className="w-3 h-3" />
                              {cred.provider}
                            </span>
                          </td>
                          <td className="px-5 py-3.5">
                            <div className="flex items-center gap-2">
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
                                <ShieldCheck className="w-3 h-3" />
                                {cred.status}
                              </span>
                              {cred.sync_status && (
                                <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border ${
                                  cred.sync_status === 'syncing'
                                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400 border-blue-200 dark:border-blue-500/20'
                                    : cred.sync_status === 'synced'
                                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20'
                                      : 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400 border-rose-200 dark:border-rose-500/20'
                                }`}>
                                  {cred.sync_status === 'syncing' ? (
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                  ) : (
                                    <RefreshCw className="w-3 h-3" />
                                  )}
                                  {cred.sync_status.charAt(0).toUpperCase() + cred.sync_status.slice(1)}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-5 py-3.5 text-gray-500 dark:text-gray-400">
                            {cred.last_used_at ? new Date(cred.last_used_at).toLocaleDateString() : 'Never'}
                          </td>
                          <td className="px-5 py-3.5 text-right space-x-2">
                            {cred.status === 'pending' && cred.provider === 'Google' && (
                              <button
                                onClick={() => {
                                  regenerateGoogleOAuthUrlMutation.mutate(cred.id, {
                                    onSuccess: (data) => {
                                      window.location.href = data.auth_url;
                                    }
                                  });
                                }}
                                disabled={regenerateGoogleOAuthUrlMutation.isPending}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-500/10 dark:text-blue-400 dark:hover:bg-blue-500/20 transition-colors disabled:opacity-50 border border-blue-200 dark:border-blue-500/20 mr-2"
                                title="Complete Setup"
                              >
                                <RefreshCw className={`w-3.5 h-3.5 ${regenerateGoogleOAuthUrlMutation.isPending ? 'animate-spin' : ''}`} />
                                {regenerateGoogleOAuthUrlMutation.isPending ? 'Redirecting...' : 'Complete Setup'}
                              </button>
                            )}
                            <button
                              onClick={() => setCredentialToDelete(cred.id)}
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
                  {totalPages > 1 && (
                    <div className="p-4 border-t border-gray-100 dark:border-white/5 flex items-center justify-between bg-gray-50/50 dark:bg-white/[0.02]">
                      <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1.5 text-sm rounded-lg font-medium bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:bg-gray-50 dark:hover:bg-white/10 disabled:opacity-50 transition-colors"
                      >
                        Previous
                      </button>
                      <span className="text-xs text-gray-500">Page {currentPage} of {totalPages}</span>
                      <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1.5 text-sm rounded-lg font-medium bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:bg-gray-50 dark:hover:bg-white/10 disabled:opacity-50 transition-colors"
                      >
                        Next
                      </button>
                    </div>
                  )}
                  </>
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
          </>
        )}

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
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Client ID *</label>
                        <input
                          type="text"
                          placeholder="Google OAuth client ID."
                          value={googleClientId}
                          onChange={(e) => setGoogleClientId(e.target.value)}
                          className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Client Secret *</label>
                        <input
                          type="password"
                          placeholder="Google OAuth client secret."
                          value={googleClientSecret}
                          onChange={(e) => setGoogleClientSecret(e.target.value)}
                          className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-[#111113] text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-white/20 transition-shadow"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Redirect URI *</label>
                        <input
                          type="text"
                          value={googleRedirectUri}
                          disabled
                          className="w-full px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-[#1a1a1c] text-sm text-gray-500 dark:text-gray-400 cursor-not-allowed focus:outline-none transition-shadow"
                        />
                        <p className="text-xs text-gray-500 mt-1">Configured redirect URI for OAuth callback.</p>
                      </div>
                    </div>
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

              <div className={`px-6 py-4 bg-gray-50/80 dark:bg-white/5 border-t border-gray-200 dark:border-white/10 flex items-center ${provider !== 'Google' ? 'justify-between' : 'justify-end'}`}>
                {provider !== 'Google' && (
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={!provider || testCredentialMutation.isPending}
                    className="px-4 py-2 text-sm rounded-lg font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10 hover:bg-blue-100 dark:hover:bg-blue-500/20 transition-colors disabled:opacity-50"
                  >
                    {testCredentialMutation.isPending ? 'Testing...' : 'Test Connection'}
                  </button>
                )}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 text-sm rounded-lg font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreate}
                    disabled={!name || !provider || (provider === 'Google' && generateGoogleOAuthUrlMutation.isPending)}
                    className="px-4 py-2 text-sm rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors shadow-sm disabled:opacity-50"
                  >
                    {provider === 'Google' && generateGoogleOAuthUrlMutation.isPending ? 'Redirecting...' : 'Create Credential'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      {/* Delete Credential Modal */}
      {credentialToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 animate-in fade-in">
          <div
            className="absolute inset-0 bg-black/20 dark:bg-black/60 backdrop-blur-sm"
            onClick={() => setCredentialToDelete(null)}
          />
          <div className="relative w-full max-w-md rounded-2xl bg-white dark:bg-[#0f172a] shadow-xl border border-black/10 dark:border-white/10 overflow-hidden animate-in zoom-in-95 duration-300 slide-in-from-bottom-8">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">Delete Credential</h2>
                <button
                  onClick={() => setCredentialToDelete(null)}
                  className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-gray-500 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Are you sure you want to delete this credential? This action cannot be undone, and any connectors currently using it will be disabled.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setCredentialToDelete(null)}
                  className="px-4 py-2 rounded-lg font-medium text-gray-700 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    deleteCredentialMutation.mutate(credentialToDelete, {
                      onSuccess: () => setCredentialToDelete(null)
                    });
                  }}
                  disabled={deleteCredentialMutation.isPending}
                  className="px-4 py-2 rounded-lg font-medium bg-red-600 hover:bg-red-700 text-white transition-colors disabled:opacity-50"
                >
                  {deleteCredentialMutation.isPending ? 'Deleting...' : 'Yes, Delete'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
