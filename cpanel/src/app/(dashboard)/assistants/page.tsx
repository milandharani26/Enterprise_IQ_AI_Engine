"use client";

import React, { useState } from 'react';
import { Bot, Plus, Search, Filter, MoreVertical, Activity, Settings2, PlayCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Textarea } from '@/components/ui/Textarea';

const MOCK_ASSISTANTS = [
  {
    id: 'ast_101',
    name: 'Customer Support Agent',
    code: 'customer_support',
    description: 'Handles frontline customer inquiries, processes refunds, and answers product FAQs automatically.',
    status: 'enabled',
    lastActive: '2 mins ago',
    tools: 4,
    calls: '12.4k',
    tags: ['support', 'external', 'high-volume']
  },
  {
    id: 'ast_102',
    name: 'Sales Development Rep',
    code: 'sdr_bot',
    description: 'Qualifies inbound leads from the website and automatically schedules meetings in Salesforce.',
    status: 'enabled',
    lastActive: '15 mins ago',
    tools: 3,
    calls: '3.1k',
    tags: ['sales', 'lead-gen']
  },
  {
    id: 'ast_103',
    name: 'Internal Knowledge Bot',
    code: 'hr_wiki_bot',
    description: 'Answers employee questions regarding HR policies, IT troubleshooting, and company benefits.',
    status: 'disabled',
    lastActive: '2 days ago',
    tools: 1,
    calls: '450',
    tags: ['internal', 'hr']
  },
  {
    id: 'ast_104',
    name: 'Code Reviewer',
    code: 'pr_reviewer',
    description: 'Analyzes GitHub pull requests for security vulnerabilities and style guide violations.',
    status: 'enabled',
    lastActive: 'Just now',
    tools: 2,
    calls: '8.9k',
    tags: ['engineering', 'ci/cd']
  }
];

export default function AssistantsPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="flex flex-col gap-8 h-full">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="m-0 text-2xl font-bold text-primary-text tracking-tight">AI Assistants</h1>
          <p className="m-0 mt-1 text-sm text-secondary-text">Deploy and manage your autonomous agents.</p>
        </div>
        <Button variant="primary" className="gap-2" onClick={() => setIsModalOpen(true)}>
          <Plus size={18} />
          New Assistant
        </Button>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row items-center gap-4 bg-secondary-bg p-2 rounded-xl border border-border-color">
        <div className="flex-1 w-full relative">
          <Input
            placeholder="Search assistants by name, code, or tag..."
            icon={<Search size={18} />}
            className="w-full bg-transparent border-none shadow-none focus:ring-0"
          />
        </div>
        <div className="h-8 w-px bg-border-color hidden sm:block" />
        <div className="flex items-center gap-2 pr-2 w-full sm:w-auto">
          <Button variant="ghost" size="sm" className="gap-2">
            <Filter size={16} />
            Filters
          </Button>
          <div className="flex bg-tertiary-bg p-1 rounded-lg">
            <button className="px-3 py-1.5 text-xs font-medium bg-card-bg shadow-sm rounded-md text-primary-text transition-all">All</button>
            <button className="px-3 py-1.5 text-xs font-medium text-secondary-text hover:text-primary-text transition-all">Active</button>
            <button className="px-3 py-1.5 text-xs font-medium text-secondary-text hover:text-primary-text transition-all">Disabled</button>
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-6">
        {MOCK_ASSISTANTS.map((assistant) => (
          <AssistantCard key={assistant.id} assistant={assistant} />
        ))}
      </div>

      {/* Create Assistant Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create New Assistant"
        description="Register a new AI assistant. The code is a unique identifier and cannot be changed after creation."
        maxWidth="max-w-4xl"
      >
        <form className="flex flex-col gap-5">
          <Input
            label="Name *"
            placeholder="e.g., Support Assistant"
            autoFocus
          />
          <Input
            label="Code *"
            placeholder="e.g., support_assistant"
          />
          <p className="-mt-3 text-xs text-muted-text">Unique identifier — letters, numbers, and underscores only. Cannot be changed later.</p>

          <Textarea
            label="Description"
            placeholder="What does this assistant do?"
          />

          <Input
            label="Category"
            placeholder="e.g., support, sales, internal"
          />

          <div className="flex items-center justify-end gap-3 mt-4 pt-4 border-t border-border-color">
            <Button variant="ghost" type="button" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="button" onClick={() => setIsModalOpen(false)}>
              Create Assistant
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

import Link from 'next/link';

function AssistantCard({ assistant }: { assistant: typeof MOCK_ASSISTANTS[0] }) {
  return (
    <Link href={`/assistants/${assistant.id}`} className="group relative flex flex-col bg-card-bg border border-border-color rounded-2xl p-6 transition-all duration-300 hover:border-border-hover hover:shadow-xl hover:shadow-black/5 hover:-translate-y-1 outline-none focus-visible:ring-2 focus-visible:ring-accent-primary">
      {/* Top row: Icon & Status */}
      <div className="flex justify-between items-start mb-4">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-primary/20 to-accent-secondary/20 flex items-center justify-center text-accent-primary border border-accent-primary/10">
          <Bot size={24} />
        </div>
        <div className="flex items-center gap-2">
          {assistant.status === 'enabled' ? (
            <Badge variant="success" size="sm" className="gap-1.5 px-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-success animate-pulse" />
              Active
            </Badge>
          ) : (
            <Badge variant="outline" size="sm">Disabled</Badge>
          )}
          <button 
            className="text-muted-text hover:text-primary-text transition-colors p-1" 
            aria-label="More options"
            onClick={(e) => e.preventDefault()}
          >
            <MoreVertical size={18} />
          </button>
        </div>
      </div>

      {/* Title & Description */}
      <div className="mb-6 flex-1">
        <h3 className="m-0 text-lg font-bold text-primary-text tracking-tight group-hover:text-accent-primary transition-colors">
          {assistant.name}
        </h3>
        <p className="m-0 mt-1 text-xs font-mono text-muted-text uppercase tracking-wider">{assistant.code}</p>
        <p className="m-0 mt-3 text-sm text-secondary-text leading-relaxed line-clamp-2">
          {assistant.description}
        </p>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-2 mb-6">
        {assistant.tags.map(tag => (
          <Badge key={tag} variant="default" size="sm">#{tag}</Badge>
        ))}
      </div>

      {/* Bottom Stats & Actions */}
      <div className="pt-5 border-t border-border-color flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs font-medium text-muted-text">
          <div className="flex items-center gap-1.5" title="API Calls">
            <Activity size={14} />
            {assistant.calls}
          </div>
          <div className="flex items-center gap-1.5" title="Connected Tools">
            <Settings2 size={14} />
            {assistant.tools}
          </div>
        </div>
        <Button 
          variant="secondary" 
          size="sm" 
          className="gap-2 text-xs h-8 px-3 rounded-lg border-transparent bg-tertiary-bg hover:bg-accent-primary hover:text-white transition-all group-hover:bg-accent-primary group-hover:text-white"
          onClick={(e) => {
            e.preventDefault();
            // Optional: navigate to playground directly
          }}
        >
          <PlayCircle size={14} />
          Playground
        </Button>
      </div>
    </Link>
  );
}
