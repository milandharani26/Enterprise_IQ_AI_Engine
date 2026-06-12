"use client";

import React, { useState } from 'react';
import { KeyRound, Copy, Plus, ShieldCheck, MoreVertical, CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';

interface Token {
  id: string;
  name: string;
  prefix: string;
  created: string;
  expires: string;
  status: 'active' | 'revoked';
}

const INITIAL_TOKENS: Token[] = [
  {
    id: 'tok_1',
    name: 'Production Worker',
    prefix: 'sk_live_...j9k8',
    created: 'Jun 12, 2026',
    expires: 'Never',
    status: 'active',
  },
  {
    id: 'tok_2',
    name: 'Staging Environment',
    prefix: 'sk_test_...m2n1',
    created: 'May 01, 2026',
    expires: 'Nov 12, 2026',
    status: 'active',
  }
];

export default function ServiceTokenPage() {
  const [tokens, setTokens] = useState<Token[]>(INITIAL_TOKENS);
  const [filter, setFilter] = useState<'all' | 'active' | 'revoked'>('all');
  
  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newTokenName, setNewTokenName] = useState('');
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  const filteredTokens = tokens.filter(t => filter === 'all' || t.status === filter);

  const handleGenerate = () => {
    if (!newTokenName.trim()) return;
    const fullToken = `sk_live_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`;
    const prefix = `sk_live_...${fullToken.slice(-4)}`;
    
    const newToken: Token = {
      id: `tok_${Date.now()}`,
      name: newTokenName,
      prefix,
      created: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      expires: 'Never',
      status: 'active'
    };

    setTokens([newToken, ...tokens]);
    setGeneratedToken(fullToken);
  };

  const handleCopy = () => {
    if (generatedToken) {
      navigator.clipboard.writeText(generatedToken);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  const handleCloseModal = () => {
    setIsCreateModalOpen(false);
    setTimeout(() => {
      setNewTokenName('');
      setGeneratedToken(null);
      setIsCopied(false);
    }, 300);
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto h-full">
      {/* Premium Light-Theme Header with Inline Stats */}
      <div className="relative overflow-hidden bg-card-bg border border-border-color rounded-3xl p-8 shadow-sm">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-bl from-accent-primary/10 via-accent-primary/5 to-transparent rounded-full blur-3xl -mr-48 -mt-48 pointer-events-none" />
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex flex-col">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-accent-primary/10 text-accent-primary text-xs font-bold tracking-widest uppercase mb-4 w-fit">
              <ShieldCheck size={14} /> Secure Access
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-primary-text m-0 mb-2">Service Tokens</h1>
            <p className="text-secondary-text text-sm max-w-xl m-0 leading-relaxed">
              Manage app-to-app authentication tokens. For your protection, tokens are only displayed once upon creation. Revoke and rotate keys regularly to maintain security.
            </p>
          </div>
          
          <div className="flex items-center gap-6 shrink-0 mt-4 md:mt-0 bg-secondary-bg/50 p-2 pl-6 rounded-2xl border border-border-color">
            <div className="flex items-center gap-6 pr-6 border-r border-border-color">
              <div className="flex flex-col items-center">
                <span className="text-2xl font-bold text-primary-text leading-none">{tokens.filter(t => t.status === 'active').length}</span>
                <span className="text-[10px] font-bold text-secondary-text mt-1.5 uppercase tracking-wider">Active</span>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-2xl font-bold text-accent-danger leading-none">{tokens.filter(t => t.status === 'revoked').length}</span>
                <span className="text-[10px] font-bold text-secondary-text mt-1.5 uppercase tracking-wider">Revoked</span>
              </div>
            </div>
            <Button variant="primary" size="lg" className="gap-2 shadow-lg shadow-accent-primary/20 rounded-xl" onClick={() => setIsCreateModalOpen(true)}>
              <Plus size={18} strokeWidth={2.5} />
              Create Token
            </Button>
          </div>
        </div>
      </div>

      {/* Sleek List Container */}
      <div className="flex flex-col flex-1 mt-4">
        {/* Modern Tabs */}
        <div className="flex items-center gap-2 mb-6 border-b border-border-color pb-px">
          {['all', 'active', 'revoked'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f as any)}
              className={`pb-3 px-4 text-sm font-semibold capitalize transition-all relative ${
                filter === f 
                  ? 'text-accent-primary' 
                  : 'text-secondary-text hover:text-primary-text'
              }`}
            >
              {f} Tokens
              {filter === f && (
                <div className="absolute bottom-0 left-0 w-full h-[2px] bg-accent-primary rounded-t-full shadow-[0_-2px_10px_rgba(59,130,246,0.5)]" />
              )}
            </button>
          ))}
        </div>

        {/* Minimalist Edge-to-Edge Table List */}
        <div className="bg-card-bg border border-border-color rounded-2xl overflow-hidden shadow-sm flex-1">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-secondary-bg/30 border-b border-border-color">
                <th className="py-4 px-6 text-xs font-bold text-muted-text uppercase tracking-widest w-[30%]">Application</th>
                <th className="py-4 px-6 text-xs font-bold text-muted-text uppercase tracking-widest w-[30%]">Masked Secret</th>
                <th className="py-4 px-6 text-xs font-bold text-muted-text uppercase tracking-widest w-[20%]">Timeline</th>
                <th className="py-4 px-6 text-xs font-bold text-muted-text uppercase tracking-widest w-[15%]">Status</th>
                <th className="py-4 px-6 w-[5%]"></th>
              </tr>
            </thead>
            <tbody>
              {filteredTokens.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-16 px-6 text-center">
                    <div className="flex flex-col items-center justify-center text-muted-text">
                      <ShieldAlert size={48} strokeWidth={1} className="mb-4 opacity-50" />
                      <p className="text-primary-text font-medium text-lg mb-1">No tokens found</p>
                      <p className="text-sm">There are no {filter !== 'all' ? filter : ''} tokens matching your criteria.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredTokens.map((token) => (
                  <tr key={token.id} className="border-b border-border-color last:border-0 hover:bg-secondary-bg/40 transition-colors group">
                    <td className="py-5 px-6">
                      <div className="flex flex-col">
                        <span className="font-bold text-primary-text text-[15px] group-hover:text-accent-primary transition-colors">{token.name}</span>
                        <span className="text-xs text-muted-text font-mono mt-1">{token.id}</span>
                      </div>
                    </td>
                    <td className="py-5 px-6">
                      <div className="inline-flex items-center gap-2 bg-[#0f111a] border border-[#262936] px-3 py-1.5 rounded-lg shadow-inner">
                        <KeyRound size={14} className="text-[#60a5fa]" />
                        <code className="text-sm text-gray-300 font-mono tracking-wider">
                          {token.prefix}
                        </code>
                      </div>
                    </td>
                    <td className="py-5 px-6">
                      <div className="flex flex-col gap-1">
                        <span className="text-[13px] text-secondary-text"><strong className="text-muted-text font-medium">Created:</strong> {token.created}</span>
                        <span className="text-[13px] text-secondary-text"><strong className="text-muted-text font-medium">Expires:</strong> {token.expires}</span>
                      </div>
                    </td>
                    <td className="py-5 px-6">
                      {token.status === 'active' ? (
                        <div className="inline-flex items-center gap-1.5 text-accent-success bg-accent-success/10 px-2.5 py-1 rounded-md text-xs font-bold tracking-wide uppercase border border-accent-success/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-accent-success animate-pulse" />
                          Active
                        </div>
                      ) : (
                        <div className="inline-flex items-center gap-1.5 text-muted-text bg-tertiary-bg px-2.5 py-1 rounded-md text-xs font-bold tracking-wide uppercase border border-border-color">
                          <div className="w-1.5 h-1.5 rounded-full bg-muted-text" />
                          Revoked
                        </div>
                      )}
                    </td>
                    <td className="py-5 px-6 text-right">
                      <button className="p-2 text-muted-text hover:text-primary-text rounded-lg hover:bg-tertiary-bg opacity-0 group-hover:opacity-100 transition-all focus:opacity-100 outline-none">
                        <MoreVertical size={20} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Security Modal - Exactly as requested for the strict copy flow */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={handleCloseModal}
        title={generatedToken ? "Token Generated" : "Generate New Secret"}
        description={generatedToken 
          ? "This is the only time your secret will be visible. Please copy it now."
          : "Create a new API token. You will only be able to see the secret once."
        }
        maxWidth="max-w-md"
      >
        {!generatedToken ? (
          <form className="flex flex-col gap-5 mt-2">
            <div>
              <label className="block text-sm font-semibold text-primary-text mb-2">App Name <span className="text-accent-danger">*</span></label>
              <Input 
                placeholder="e.g. Enterprise GPT Production"
                value={newTokenName}
                onChange={(e) => setNewTokenName(e.target.value)}
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-primary-text mb-2">Expiry Time <span className="text-secondary-text font-normal">(optional)</span></label>
              <Input 
                type="datetime-local"
                placeholder="dd-mm-yyyy --:--"
              />
              <p className="text-xs text-secondary-text mt-2 m-0">Leave empty for a non-expiring token (active until revoked).</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-primary-text mb-2">Message Note <span className="text-secondary-text font-normal">(optional)</span></label>
              <Textarea 
                placeholder="e.g. Used by the analytics pipeline for GPT access."
                rows={3}
              />
            </div>
            <div className="flex justify-end gap-3 mt-4 pt-5 border-t border-border-color">
              <Button variant="ghost" type="button" onClick={handleCloseModal}>Cancel</Button>
              <Button variant="primary" type="button" onClick={handleGenerate} disabled={!newTokenName.trim()}>
                Create Token
              </Button>
            </div>
          </form>
        ) : (
          <div className="flex flex-col gap-6 mt-4">
            <div className="bg-[#0f111a] p-5 rounded-2xl border border-[#262936] relative shadow-inner group">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-3 block">Your Secret Key</label>
              <div className="font-mono text-[15px] text-white break-all pr-12 leading-relaxed">
                {generatedToken}
              </div>
              <button 
                onClick={handleCopy}
                className="absolute top-1/2 -translate-y-1/2 right-4 p-2.5 bg-[#1a1f36] hover:bg-[#2563eb] border border-[#262936] hover:border-transparent rounded-xl text-[#60a5fa] hover:text-white transition-all shadow-lg"
                title="Copy token"
              >
                {isCopied ? <CheckCircle2 size={18} /> : <Copy size={18} />}
              </button>
            </div>
            
            <div className="flex items-center justify-between mt-2 pt-5 border-t border-border-color">
              <div className="text-sm font-medium">
                {isCopied ? (
                  <span className="text-accent-success flex items-center gap-2">
                    <CheckCircle2 size={16} /> Copied to clipboard
                  </span>
                ) : (
                  <span className="text-secondary-text">Ready to copy</span>
                )}
              </div>
              <Button variant="primary" type="button" onClick={handleCloseModal}>
                I've stored it safely
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
