"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, Save, Trash2, ShieldOff, PlayCircle, Bot, Blocks, Shield, FileCheck } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Switch } from '@/components/ui/Switch';

export default function AssistantDetailsClient() {
  const params = useParams();
  const id = params?.id as string;

  const [isToolModalOpen, setIsToolModalOpen] = useState(false);
  const [isGuardrailModalOpen, setIsGuardrailModalOpen] = useState(false);

  return (
    <div className="flex flex-col h-full">
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-6 border-b border-border-color shrink-0">
        <div className="flex items-center gap-4">
          <Link href="/assistants">
            <Button variant="ghost" size="sm" className="p-2 -ml-2 rounded-full text-muted-text hover:text-primary-text hover:bg-secondary-bg">
              <ArrowLeft size={20} />
            </Button>
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-primary/20 to-accent-secondary/20 flex items-center justify-center text-accent-primary border border-accent-primary/10">
              <Bot size={20} />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="m-0 text-xl font-bold text-primary-text tracking-tight">Customer Support Agent</h1>
                <Badge variant="success" size="sm" className="gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-success animate-pulse" />
                  Active
                </Badge>
              </div>
              <p className="m-0 mt-0.5 text-xs font-mono text-muted-text uppercase tracking-wider">customer_support • {id}</p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Button variant="ghost" className="gap-2 text-secondary-text hover:text-primary-text">
            <FileCheck size={16} />
            Check prompt
          </Button>
          <Button variant="ghost" className="text-accent-danger hover:bg-accent-danger/10 hover:text-accent-danger gap-2">
            <Trash2 size={16} />
            Delete
          </Button>
          <Button variant="secondary" className="gap-2">
            <ShieldOff size={16} />
            Disable
          </Button>
          <Button variant="primary" className="gap-2">
            <Save size={16} />
            Save Changes
          </Button>
        </div>
      </div>

      {/* Main Unified Layout */}
      <div className="flex flex-col lg:flex-row flex-1 overflow-hidden min-h-0 pt-6 gap-8">
        
        {/* Left Column: Configuration (Scrollable) */}
        <div className="w-full lg:w-[450px] xl:w-[500px] flex flex-col gap-10 overflow-y-auto pr-2 pb-10 custom-scrollbar shrink-0">
          
          {/* Section: Basic Identity */}
          <section className="flex flex-col gap-5">
            <div>
              <h2 className="text-sm font-semibold text-primary-text uppercase tracking-wider mb-1">Basic Identity</h2>
              <p className="text-xs text-secondary-text">Core details defining this assistant.</p>
            </div>
            
            <div className="flex flex-col gap-4">
              <Input label="Assistant Name" defaultValue="Customer Support Agent" />
              <Input label="Unique Code" defaultValue="customer_support" disabled />
              <Textarea label="Description" defaultValue="Handles frontline customer inquiries, processes refunds, and answers product FAQs automatically." className="min-h-[80px]" />
            </div>
          </section>

          <hr className="border-border-color" />

          {/* Section: Extensions (Tools & Guardrails) */}
          <section className="flex flex-col gap-5">
             <div>
              <h2 className="text-sm font-semibold text-primary-text uppercase tracking-wider mb-1">Capabilities & Security</h2>
              <p className="text-xs text-secondary-text">Extend actions and enforce rules.</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div 
                className="flex flex-col items-center justify-center p-6 bg-tertiary-bg border border-dashed border-border-color rounded-2xl hover:border-accent-primary hover:bg-accent-primary/5 cursor-pointer transition-all group"
                onClick={() => setIsToolModalOpen(true)}
              >
                <div className="w-10 h-10 rounded-full bg-card-bg shadow-sm flex items-center justify-center text-secondary-text group-hover:text-accent-primary mb-3 transition-colors">
                  <Blocks size={20} />
                </div>
                <span className="text-sm font-medium text-primary-text">Tools (0)</span>
                <span className="text-xs text-muted-text mt-1 text-center">Give the AI skills</span>
              </div>
              
              <div 
                className="flex flex-col items-center justify-center p-6 bg-tertiary-bg border border-dashed border-border-color rounded-2xl hover:border-accent-success hover:bg-accent-success/5 cursor-pointer transition-all group"
                onClick={() => setIsGuardrailModalOpen(true)}
              >
                <div className="w-10 h-10 rounded-full bg-card-bg shadow-sm flex items-center justify-center text-secondary-text group-hover:text-accent-success mb-3 transition-colors">
                  <Shield size={20} />
                </div>
                <span className="text-sm font-medium text-primary-text">Guardrails (0)</span>
                <span className="text-xs text-muted-text mt-1 text-center">Set safety limits</span>
              </div>
            </div>
          </section>

        </div>

        {/* Right Column: System Instructions (Prompt) */}
        <div className="flex-1 flex flex-col bg-secondary-bg border border-border-color rounded-2xl overflow-hidden shadow-sm">
          <div className="flex items-center justify-between p-4 border-b border-border-color bg-card-bg shrink-0">
            <div>
              <h2 className="text-sm font-semibold text-primary-text tracking-wide flex items-center gap-2">
                System Instructions
              </h2>
              <p className="text-xs text-secondary-text mt-0.5">Define the core personality and behavior.</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="text-xs bg-tertiary-bg">Strict Template</Button>
              <Button variant="ghost" size="sm" className="text-xs bg-tertiary-bg">Friendly Template</Button>
              <div className="w-px h-4 bg-border-color mx-1"></div>
              <Button variant="secondary" size="sm" className="gap-2 text-xs">
                <PlayCircle size={14} />
                Test in Playground
              </Button>
            </div>
          </div>
          
          <div className="flex-1 p-0 relative">
            <textarea 
              className="absolute inset-0 w-full h-full p-6 bg-transparent border-none text-primary-text font-mono text-sm leading-relaxed resize-none focus:outline-none custom-scrollbar"
              defaultValue={`You are a helpful customer support assistant for Acme Corporation.

Your primary goals are:
1. Answer customer questions politely and accurately.
2. If you don't know the answer, escalate to a human agent.
3. Maintain a professional, empathetic tone.

Rules:
- Never promise refunds without checking the policy tool.
- Always ask for the user's order number if the query is about shipping.`}
              placeholder="Write the system prompt here..."
            />
          </div>
        </div>

      </div>

      {/* Add Tool Modal */}
      <Modal
        isOpen={isToolModalOpen}
        onClose={() => setIsToolModalOpen(false)}
        title="Add Tool"
        maxWidth="max-w-xl"
      >
        <form className="flex flex-col gap-5">
          <Select 
            label="Tool ID" 
            options={[
              { label: 'rag_search', value: 'rag_search' },
              { label: 'fetch_weather', value: 'fetch_weather' },
            ]}
            defaultValue="rag_search"
          />
          <Select 
            label="Credential" 
            options={[
              { label: 'None', value: 'none' },
              { label: 'API Key', value: 'api_key' },
            ]}
            defaultValue="none"
          />
          <Textarea 
            label="Usage instructions" 
            placeholder="When and how the model should use this tool"
            className="min-h-[100px]"
          />
          <div className="p-3 bg-tertiary-bg border border-border-color rounded-lg flex items-center text-xs text-secondary-text">
            Additional config is disabled for <code className="mx-1 px-1.5 py-0.5 bg-secondary-bg rounded text-primary-text">rag_search</code>.
          </div>
          
          <div className="flex items-center justify-end gap-3 mt-2 pt-4 border-t border-border-color">
            <Button variant="ghost" type="button" onClick={() => setIsToolModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="button" onClick={() => setIsToolModalOpen(false)}>
              Add Tool
            </Button>
          </div>
        </form>
      </Modal>

      {/* Add Guardrail Modal */}
      <Modal
        isOpen={isGuardrailModalOpen}
        onClose={() => setIsGuardrailModalOpen(false)}
        title="Add Guardrail"
        maxWidth="max-w-xl"
      >
        <form className="flex flex-col gap-5">
          <Input 
            label="Type *" 
            placeholder="e.g. Financial accuracy" 
            autoFocus
          />
          <Textarea 
            label="Instructions *" 
            placeholder="Describe what this guardrail should do..."
            className="min-h-[100px]"
          />
          <Select 
            label="Enforcement" 
            options={[
              { label: 'Block', value: 'block' },
              { label: 'Warn', value: 'warn' },
            ]}
            defaultValue="block"
          />
          <div className="flex items-center justify-between p-4 border border-border-color rounded-lg bg-card-bg mt-2">
            <div>
              <div className="text-sm font-medium text-primary-text">Enabled</div>
              <div className="text-xs text-muted-text mt-0.5">Guardrail is active when enabled</div>
            </div>
            <Switch defaultChecked />
          </div>

          <div className="flex items-center justify-end gap-3 mt-2 pt-4 border-t border-border-color">
            <Button variant="ghost" type="button" onClick={() => setIsGuardrailModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="button" onClick={() => setIsGuardrailModalOpen(false)}>
              Add Guardrail
            </Button>
          </div>
        </form>
      </Modal>

    </div>
  );
}
