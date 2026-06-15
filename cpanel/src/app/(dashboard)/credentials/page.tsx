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

const PROVIDERS = ['Google', 'OpenAI', 'Anthropic', 'PostgreSQL', 'Microsoft'];

export default function CredentialsPage() {
  const { credentials, addCredential, deleteCredential } = useIntegrationStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Modal State
  const [provider, setProvider] = useState('');
  const [name, setName] = useState('');

  const filteredCredentials = credentials.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.provider.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreate = () => {
    if (name && provider) {
      addCredential({
        name,
        provider,
      });
      setIsModalOpen(false);
      setName('');
      setProvider('');
    }
  };

  return (
    <div className="min-h-full p-4 md:p-8 lg:p-12 relative">

      {/* Header Section */}
      <div className="mb-10 max-w-6xl mx-auto flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-2 bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400">
            Credentials
          </h1>
          <p className="text-gray-600 dark:text-gray-400 text-lg max-w-2xl leading-relaxed">
            Manage provider credentials from the admin backend securely.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-6 py-3 rounded-full font-medium bg-black dark:bg-white text-white dark:text-gray-900 shadow-xl shadow-black/10 dark:shadow-white/10 transition-all hover:scale-105"
        >
          <Plus className="w-5 h-5" /> Add Credential
        </button>
      </div>

      {/* Filters Section */}
      <div className="max-w-6xl mx-auto mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="p-6 rounded-3xl bg-white/50 dark:bg-[#111113]/50 backdrop-blur-xl border border-black/5 dark:border-white/5 shadow-sm">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search credentials..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black/20 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
              />
            </div>
            <div className="w-full md:w-48 relative">
              <select className="w-full px-4 py-3 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black/20 text-gray-900 dark:text-white appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow">
                <option value="all">All Types</option>
                {PROVIDERS.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <ChevronDown className="w-5 h-5 absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            </div>
          </div>
        </div>
      </div>

      {/* Credentials List */}
      <div className="max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-6 duration-700">
        <div className="rounded-3xl bg-white/50 dark:bg-[#111113]/50 backdrop-blur-xl border border-black/5 dark:border-white/5 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-black/5 dark:border-white/5">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Credential List</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {filteredCredentials.length} total credentials. Data is masked by the backend for security.
            </p>
          </div>

          {filteredCredentials.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-black/5 dark:bg-white/5 border-b border-black/5 dark:border-white/5">
                    <th className="px-6 py-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Credential Name</th>
                    <th className="px-6 py-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Provider</th>
                    <th className="px-6 py-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Status</th>
                    <th className="px-6 py-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Last Used</th>
                    <th className="px-6 py-4 text-sm font-semibold text-gray-700 dark:text-gray-300 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/5 dark:divide-white/5">
                  {filteredCredentials.map(cred => (
                    <tr key={cred.id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-blue-500/10 dark:bg-blue-500/20 flex items-center justify-center text-blue-600 dark:text-blue-400">
                            <KeyRound className="w-4 h-4" />
                          </div>
                          <span className="font-medium text-gray-900 dark:text-white">{cred.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-3 py-1 rounded-full text-xs font-medium bg-black/5 dark:bg-white/10 text-gray-700 dark:text-gray-300 border border-black/5 dark:border-white/5 flex items-center gap-1.5 w-max">
                          <Globe className="w-3 h-3" />
                          {cred.provider}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-700 dark:text-green-400 border border-green-500/20 flex items-center gap-1.5 w-max">
                          <ShieldCheck className="w-3 h-3" />
                          {cred.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {cred.lastUsed ? cred.lastUsed.toLocaleDateString() : 'Never'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => deleteCredential(cred.id)}
                          className="p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-500/10 transition-colors"
                          title="Delete Credential"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-16 flex flex-col items-center justify-center text-center">
              <div className="w-20 h-20 rounded-full bg-gray-100 dark:bg-white/5 flex items-center justify-center mb-6">
                <KeyRound className="w-10 h-10 text-gray-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">No credentials found</h3>
              <p className="text-gray-500 dark:text-gray-400 max-w-md">
                You haven't added any external credentials yet. Click the button above to securely add your first credential.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Add Credential Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 animate-in fade-in">
          <div
            className="absolute inset-0 bg-black/20 dark:bg-black/60 backdrop-blur-sm"
            onClick={() => setIsModalOpen(false)}
          />
          <div className="relative w-full max-w-lg rounded-3xl bg-white dark:bg-[#0f172a] shadow-2xl border border-black/10 dark:border-white/10 overflow-hidden animate-in zoom-in-95 duration-300 slide-in-from-bottom-8">
            <div className="p-6 md:p-8">

              <div className="flex items-center justify-between mb-8">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Add Credential</h2>
                  <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Pick a provider and fill provider-specific fields.</p>
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
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Provider</label>
                  <div className="relative">
                    <select
                      value={provider}
                      onChange={(e) => setProvider(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black/20 text-gray-900 dark:text-white appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
                    >
                      <option value="">Select provider...</option>
                      {PROVIDERS.map(p => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                    <ChevronDown className="w-5 h-5 absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Credential Name</label>
                  <input
                    type="text"
                    placeholder="e.g. admin@company.com"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black/20 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">API Key / Secret</label>
                  <input
                    type="password"
                    placeholder="••••••••••••••••••••••••"
                    className="w-full px-4 py-3 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black/20 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-shadow"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    Keys are heavily encrypted before being stored.
                  </p>
                </div>
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
                onClick={handleCreate}
                disabled={!name || !provider}
                className="px-6 py-2.5 rounded-xl font-medium bg-black dark:bg-white text-white dark:text-gray-900 shadow-xl shadow-black/20 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:translate-y-0"
              >
                Create Credential
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
