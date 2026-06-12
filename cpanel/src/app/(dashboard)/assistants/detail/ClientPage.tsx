"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { ArrowLeft, Save, Trash2, ShieldOff, PlayCircle, Bot, Blocks, Shield, FileCheck, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Switch } from '@/components/ui/Switch';
import { useAssistantsHooks } from '@/hooks/api/useAssistants';
import toast from 'react-hot-toast';

export default function AssistantDetailsClient() {
  const searchParams = useSearchParams();
  const id = searchParams?.get('id') as string;
  const router = useRouter();

  const { useAssistantQuery, useUpdateAssistantMutation, useDeleteAssistantMutation, useUpdateAssistantStatusMutation } = useAssistantsHooks();
  const { data: assistant, isLoading } = useAssistantQuery(id);
  const updateMutation = useUpdateAssistantMutation();
  const deleteMutation = useDeleteAssistantMutation();
  const statusMutation = useUpdateAssistantStatusMutation();

  const [isToolModalOpen, setIsToolModalOpen] = useState(false);
  const [isGuardrailModalOpen, setIsGuardrailModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const [formData, setFormData] = useState<{
    assistant_name: string;
    description: string;
    system_prompt: string;
    tools: any[];
    guardrails: any[];
  }>({
    assistant_name: '',
    description: '',
    system_prompt: '',
    tools: [],
    guardrails: []
  });

  const [newTool, setNewTool] = useState({ id: 'rag_search', credential: 'none', instructions: '' });
  const [newGuardrail, setNewGuardrail] = useState({ type: '', instructions: '', enforcement: 'block', enabled: true });

  useEffect(() => {
    if (assistant) {
      setFormData({
        assistant_name: assistant.assistant_name || '',
        description: assistant.description || '',
        system_prompt: assistant.system_prompt || '',
        tools: assistant.tools || [],
        guardrails: assistant.guardrails || [],
      });
    }
  }, [assistant]);

  const handleSave = () => {
    if (!assistant) return;
    updateMutation.mutate({
      id,
      data: {
        assistant_name: formData.assistant_name,
        assistant_code: assistant.assistant_code,
        type: assistant.type,
        description: formData.description,
        category: assistant.category,
        system_prompt: formData.system_prompt,
        status: assistant.status,
        guardrails: formData.guardrails,
        tools: formData.tools,
        prompt_library: assistant.prompt_library,
      }
    }, {
      onSuccess: () => toast.success('Assistant updated successfully!'),
      onError: () => toast.error('Failed to update assistant.')
    });
  };

  const handleDelete = () => {
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = () => {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast.success('Assistant deleted.');
        router.push('/assistants');
      },
      onError: () => toast.error('Failed to delete assistant.')
    });
  };

  const handleToggleStatus = () => {
    const newStatus = assistant?.status === 'enabled' ? false : true;
    statusMutation.mutate({ id, status_in: { is_active: newStatus } }, {
      onSuccess: () => toast.success(`Assistant ${newStatus ? 'enabled' : 'disabled'}.`),
      onError: () => toast.error('Failed to update status.')
    });
  };

  if (isLoading) {
    return (
      <div className="flex flex-col h-full items-center justify-center text-secondary-text gap-3">
        <Loader2 className="animate-spin" size={24} />
        <p>Loading Assistant...</p>
      </div>
    );
  }

  if (!assistant) {
    return (
      <div className="flex flex-col h-full items-center justify-center text-secondary-text gap-3">
        <Bot size={48} className="opacity-20" />
        <p>Assistant not found.</p>
        <Link href="/assistants">
          <Button variant="secondary">Go Back</Button>
        </Link>
      </div>
    );
  }

  const isActive = assistant.status === 'enabled';

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
                <h1 className="m-0 text-xl font-bold text-primary-text tracking-tight">{assistant.assistant_name}</h1>
                {isActive ? (
                  <Badge variant="success" size="sm" className="gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-success animate-pulse" />
                    Active
                  </Badge>
                ) : (
                  <Badge variant="outline" size="sm">Disabled</Badge>
                )}
              </div>
              <p className="m-0 mt-0.5 text-xs font-mono text-muted-text uppercase tracking-wider">{assistant.assistant_code} • {assistant.type}</p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Button variant="ghost" className="gap-2 text-secondary-text hover:text-primary-text" onClick={() => toast('Playground coming soon!')}>
            <FileCheck size={16} />
            Check prompt
          </Button>
          <Button variant="ghost" className="text-accent-danger hover:bg-accent-danger/10 hover:text-accent-danger gap-2" onClick={handleDelete} disabled={deleteMutation.isPending}>
            <Trash2 size={16} />
            Delete
          </Button>
          <Button variant="secondary" className="gap-2" onClick={handleToggleStatus} disabled={statusMutation.isPending}>
            <ShieldOff size={16} />
            {isActive ? 'Disable' : 'Enable'}
          </Button>
          <Button variant="primary" className="gap-2" onClick={handleSave} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
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
              <Input 
                label="Assistant Name" 
                value={formData.assistant_name} 
                onChange={e => setFormData({ ...formData, assistant_name: e.target.value })} 
              />
              <Input label="Unique Code" value={assistant.assistant_code} disabled />
              <Textarea 
                label="Description" 
                value={formData.description} 
                onChange={e => setFormData({ ...formData, description: e.target.value })} 
                className="min-h-[80px]" 
              />
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
                <span className="text-sm font-medium text-primary-text">Tools ({formData.tools?.length || 0})</span>
                <span className="text-xs text-muted-text mt-1 text-center">Give the AI skills</span>
              </div>
              
              <div 
                className="flex flex-col items-center justify-center p-6 bg-tertiary-bg border border-dashed border-border-color rounded-2xl hover:border-accent-success hover:bg-accent-success/5 cursor-pointer transition-all group"
                onClick={() => setIsGuardrailModalOpen(true)}
              >
                <div className="w-10 h-10 rounded-full bg-card-bg shadow-sm flex items-center justify-center text-secondary-text group-hover:text-accent-success mb-3 transition-colors">
                  <Shield size={20} />
                </div>
                <span className="text-sm font-medium text-primary-text">Guardrails ({formData.guardrails?.length || 0})</span>
                <span className="text-xs text-muted-text mt-1 text-center">Set safety limits</span>
              </div>
            </div>

            {formData.tools?.length > 0 && (
              <div className="flex flex-col gap-2 mt-2">
                <h3 className="text-xs font-semibold text-secondary-text uppercase tracking-wider mb-1">Configured Tools</h3>
                {formData.tools.map((t, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-card-bg border border-border-color shadow-sm group transition-all hover:border-border-hover">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-accent-primary/10 text-accent-primary rounded-lg">
                        <Blocks size={14} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-primary-text">{t.id}</span>
                        <span className="text-xs text-muted-text">{t.credential === 'none' ? 'No Credential' : 'API Key Required'}</span>
                      </div>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-accent-danger hover:bg-accent-danger/10 hover:text-accent-danger h-8 w-8 p-0" 
                      onClick={() => {
                        const newTools = [...formData.tools];
                        newTools.splice(idx, 1);
                        setFormData({...formData, tools: newTools});
                      }}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {formData.guardrails?.length > 0 && (
              <div className="flex flex-col gap-2 mt-2">
                <h3 className="text-xs font-semibold text-secondary-text uppercase tracking-wider mb-1">Active Guardrails</h3>
                {formData.guardrails.map((g, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-card-bg border border-border-color shadow-sm group transition-all hover:border-border-hover">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-accent-success/10 text-accent-success rounded-lg">
                        <Shield size={14} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-primary-text">{g.type}</span>
                        <span className="text-xs text-muted-text capitalize">{g.enforcement} • {g.enabled ? 'Enabled' : 'Disabled'}</span>
                      </div>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-accent-danger hover:bg-accent-danger/10 hover:text-accent-danger h-8 w-8 p-0" 
                      onClick={() => {
                        const newGuardrails = [...formData.guardrails];
                        newGuardrails.splice(idx, 1);
                        setFormData({...formData, guardrails: newGuardrails});
                      }}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                ))}
              </div>
            )}
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
              <Button variant="ghost" size="sm" className="text-xs bg-tertiary-bg" onClick={() => setFormData({...formData, system_prompt: "You are a helpful, extremely strictly bound assistant. Follow instructions to the letter."})}>Strict Template</Button>
              <Button variant="ghost" size="sm" className="text-xs bg-tertiary-bg" onClick={() => setFormData({...formData, system_prompt: "You are a warm, extremely friendly, and highly empathetic customer support assistant."})}>Friendly Template</Button>
              <div className="w-px h-4 bg-border-color mx-1"></div>
              <Button variant="secondary" size="sm" className="gap-2 text-xs" onClick={() => toast('Playground coming soon!')}>
                <PlayCircle size={14} />
                Test in Playground
              </Button>
            </div>
          </div>
          
          <div className="flex-1 p-0 relative">
            <textarea 
              className="absolute inset-0 w-full h-full p-6 bg-transparent border-none text-primary-text font-mono text-sm leading-relaxed resize-none focus:outline-none custom-scrollbar"
              value={formData.system_prompt}
              onChange={e => setFormData({ ...formData, system_prompt: e.target.value })}
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
            value={newTool.id}
            onChange={(e) => setNewTool({ ...newTool, id: e.target.value })}
          />
          <Select 
            label="Credential" 
            options={[
              { label: 'None', value: 'none' },
              { label: 'API Key', value: 'api_key' },
            ]}
            value={newTool.credential}
            onChange={(e) => setNewTool({ ...newTool, credential: e.target.value })}
          />
          <Textarea 
            label="Usage instructions" 
            placeholder="When and how the model should use this tool"
            className="min-h-[100px]"
            value={newTool.instructions}
            onChange={(e) => setNewTool({ ...newTool, instructions: e.target.value })}
          />
          <div className="p-3 bg-tertiary-bg border border-border-color rounded-lg flex items-center text-xs text-secondary-text">
            Additional config is disabled for <code className="mx-1 px-1.5 py-0.5 bg-secondary-bg rounded text-primary-text">{newTool.id}</code>.
          </div>
          
          <div className="flex items-center justify-end gap-3 mt-2 pt-4 border-t border-border-color">
            <Button variant="ghost" type="button" onClick={() => setIsToolModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="button" onClick={() => {
              setFormData({ ...formData, tools: [...formData.tools, newTool] });
              setNewTool({ id: 'rag_search', credential: 'none', instructions: '' });
              setIsToolModalOpen(false); 
              toast.success('Tool added to assistant draft. Click Save Changes to apply.'); 
            }}>
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
            value={newGuardrail.type}
            onChange={(e) => setNewGuardrail({ ...newGuardrail, type: e.target.value })}
          />
          <Textarea 
            label="Instructions *" 
            placeholder="Describe what this guardrail should do..."
            className="min-h-[100px]"
            value={newGuardrail.instructions}
            onChange={(e) => setNewGuardrail({ ...newGuardrail, instructions: e.target.value })}
          />
          <Select 
            label="Enforcement" 
            options={[
              { label: 'Block', value: 'block' },
              { label: 'Warn', value: 'warn' },
            ]}
            value={newGuardrail.enforcement}
            onChange={(e) => setNewGuardrail({ ...newGuardrail, enforcement: e.target.value })}
          />
          <div className="flex items-center justify-between p-4 border border-border-color rounded-lg bg-card-bg mt-2">
            <div>
              <div className="text-sm font-medium text-primary-text">Enabled</div>
              <div className="text-xs text-muted-text mt-0.5">Guardrail is active when enabled</div>
            </div>
            <Switch 
              checked={newGuardrail.enabled} 
              onChange={(e) => setNewGuardrail({ ...newGuardrail, enabled: e.target.checked })} 
            />
          </div>

          <div className="flex items-center justify-end gap-3 mt-2 pt-4 border-t border-border-color">
            <Button variant="ghost" type="button" onClick={() => setIsGuardrailModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="button" onClick={() => {
              if (!newGuardrail.type || !newGuardrail.instructions) {
                toast.error('Please fill required fields.');
                return;
              }
              setFormData({ ...formData, guardrails: [...formData.guardrails, newGuardrail] });
              setNewGuardrail({ type: '', instructions: '', enforcement: 'block', enabled: true });
              setIsGuardrailModalOpen(false); 
              toast.success('Guardrail added to assistant draft. Click Save Changes to apply.'); 
            }}>
              Add Guardrail
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete Assistant"
        description="Are you sure you want to delete this assistant? This action cannot be undone and any applications depending on this assistant will fail."
        maxWidth="max-w-md"
      >
        <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-border-color">
          <Button variant="ghost" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
          <Button variant="primary" className="bg-accent-danger hover:bg-accent-danger/90 text-white border-transparent" onClick={confirmDelete} disabled={deleteMutation.isPending}>
            {deleteMutation.isPending ? 'Deleting...' : 'Yes, Delete Assistant'}
          </Button>
        </div>
      </Modal>

    </div>
  );
}
