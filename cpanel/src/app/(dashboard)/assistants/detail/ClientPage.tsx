"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { ArrowLeft, Save, Trash2, ShieldOff, PlayCircle, Bot, Blocks, Shield, FileCheck, Loader2, Pencil } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Switch } from '@/components/ui/Switch';
import { useAssistantsHooks } from '@/hooks/api/useAssistants';
import { useConnectorsHooks } from '@/hooks/api/useConnectors';
import { useCredentialsHooks } from '@/hooks/api/useCredentials';
import { useAppStore } from '@/store/useAppStore';
import toast from 'react-hot-toast';

function AssistantDetailsClientContent() {
  const searchParams = useSearchParams();
  const id = searchParams?.get('id') as string;
  const router = useRouter();

  const { activeOrganizationId } = useAppStore();
  const { useConnectorsQuery } = useConnectorsHooks();
  const { data: dbConnectors = [] } = useConnectorsQuery(activeOrganizationId);
  const { useCredentialsQuery } = useCredentialsHooks();
  const { data: credentials = [] } = useCredentialsQuery(activeOrganizationId);

  const {
    useAssistantQuery,
    useUpdateAssistantMutation,
    useDeleteAssistantMutation,
    useUpdateAssistantStatusMutation,
    useToolsQuery,
    usePreviewPromptMutation,
    useAvailableLLMsQuery
  } = useAssistantsHooks();
  const { data: assistant, isLoading } = useAssistantQuery(id);
  const { data: availableTools } = useToolsQuery();
  const { data: llmData = { providers: [] } } = useAvailableLLMsQuery();
  const providers = llmData?.providers || [];
  const updateMutation = useUpdateAssistantMutation();
  const deleteMutation = useDeleteAssistantMutation();
  const statusMutation = useUpdateAssistantStatusMutation();
  const previewMutation = usePreviewPromptMutation();

  const [isToolModalOpen, setIsToolModalOpen] = useState(false);
  const [isGuardrailModalOpen, setIsGuardrailModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDisableModalOpen, setIsDisableModalOpen] = useState(false);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [previewResult, setPreviewResult] = useState<{ compiled_prompt: string; estimated_tokens: number; status: string; warnings: string[] } | null>(null);
  const [editingToolIdx, setEditingToolIdx] = useState<number | null>(null);
  const [editingGuardrailIdx, setEditingGuardrailIdx] = useState<number | null>(null);
  const [viewingTool, setViewingTool] = useState<any | null>(null);
  const [viewingToolIdx, setViewingToolIdx] = useState<number | null>(null);
  const [viewingGuardrail, setViewingGuardrail] = useState<any | null>(null);
  const [viewingGuardrailIdx, setViewingGuardrailIdx] = useState<number | null>(null);

  const handleEditTool = (tool: any, index: number) => {
    setNewTool({
      tool_id: tool.tool_id || tool.id,
      credential_id: tool.credential_id || tool.credential || 'none',
      usage_instructions: tool.usage_instructions || tool.instructions || ''
    });
    setEditingToolIdx(index);
    setIsToolModalOpen(true);
  };

  const handleEditGuardrail = (guardrail: any, index: number) => {
    setNewGuardrail({
      type: guardrail.type || '',
      instructions: guardrail.instructions || '',
      enforcement: guardrail.enforcement || 'block',
      enabled: guardrail.enabled !== undefined ? guardrail.enabled : true
    });
    setEditingGuardrailIdx(index);
    setIsGuardrailModalOpen(true);
  };

  const [formData, setFormData] = useState<{
    assistant_name: string;
    description: string;
    system_prompt: string;
    tools: any[];
    guardrails: any[];
    llmProvider: string;
    llmModel: string;
  }>({
    assistant_name: '',
    description: '',
    system_prompt: '',
    tools: [],
    guardrails: [],
    llmProvider: 'google',
    llmModel: 'gemini-3.1-flash-lite',
  });

  const [newTool, setNewTool] = useState({ tool_id: 'rag_search', credential_id: 'none', usage_instructions: '' });
  const [newGuardrail, setNewGuardrail] = useState({ type: '', instructions: '', enforcement: 'block', enabled: true });

  useEffect(() => {
    if (assistant) {
      setFormData({
        assistant_name: assistant.assistant_name || '',
        description: assistant.description || '',
        system_prompt: assistant.system_prompt || '',
        tools: assistant.tools || [],
        guardrails: assistant.guardrails || [],
        llmProvider: assistant.llm_config?.provider || (providers[0]?.id || 'google'),
        llmModel: assistant.llm_config?.model || (providers[0]?.models[0] || 'gemini-3.1-flash-lite'),
      });
    }
  }, [assistant?.assistant_id, providers.length]);

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
        llm_config: {
          provider: formData.llmProvider,
          model: formData.llmModel,
        }
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
    setIsDisableModalOpen(true);
  };

  const confirmToggleStatus = () => {
    const newStatus = assistant?.status === 'enabled' ? false : true;
    statusMutation.mutate({ id, status_in: { status: newStatus ? 'enabled' : 'disabled' } }, {
      onSuccess: () => {
        toast.success(`Assistant ${newStatus ? 'enabled' : 'disabled'}.`);
        setIsDisableModalOpen(false);
      },
      onError: () => {
        toast.error('Failed to update status.');
        setIsDisableModalOpen(false);
      }
    });
  };

  const handlePreviewPrompt = () => {
    if (!assistant) return;
    previewMutation.mutate(
      {
        ...assistant,
        type: assistant.type || 'simple_reactive',
      },
      {
        onSuccess: (data) => {
          setPreviewResult(data);
          setIsPreviewModalOpen(true);
        },
        onError: () => toast.error('Failed to generate prompt preview.')
      }
    );
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


  const providerOptions = providers.map(p => ({
    label: p.name,
    value: p.id
  }));

  const selectedProviderData = providers.find(p => p.id === formData.llmProvider);
  const modelOptions = selectedProviderData 
    ? selectedProviderData.models.map(m => ({ label: m, value: m }))
    : [];

  const isActive = assistant.status === 'enabled';

  return (
    <div className="flex flex-col h-full">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 gap-4 border-b border-border-color shrink-0">
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
              <div className="flex flex-wrap items-center gap-3">
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

        <div data-tour="assistant-details-actions" className="flex flex-wrap items-center gap-3">
          <Button variant="ghost" className="gap-2 text-secondary-text hover:text-primary-text" onClick={handlePreviewPrompt} disabled={previewMutation.isPending}>
            {previewMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <FileCheck size={16} />}
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
      <div className="flex flex-col lg:flex-row flex-1 overflow-y-auto lg:overflow-hidden lg:min-h-0 pt-6 gap-8 pb-6">

        {/* Left Column: Configuration (Scrollable) */}
        <div className="w-full lg:w-[450px] xl:w-[500px] flex flex-col gap-10 lg:overflow-y-auto pr-2 lg:pb-10 custom-scrollbar shrink-0">

          {/* Section: Basic Identity */}
          <section data-tour="assistant-details-identity" className="flex flex-col gap-5">
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
              {providers.length === 0 ? (
                <div className="p-3 bg-amber-50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-200 rounded-lg text-xs leading-relaxed border border-amber-200 dark:border-amber-900/30">
                  ⚠️ No active API key credentials found for your organization, and no system fallback key is set. Please add a <strong>Google API Key</strong> or <strong>OpenAI API Key</strong> in the Credentials section first.
                </div>
              ) : (
                <>
                  <Select
                    label="LLM Provider"
                    options={providerOptions}
                    value={formData.llmProvider}
                    onChange={(e) => {
                      const nextProvider = e.target.value;
                      const provData = providers.find(p => p.id === nextProvider);
                      const nextModel = provData?.models[0] || '';
                      setFormData({ ...formData, llmProvider: nextProvider, llmModel: nextModel });
                    }}
                  />
                  <Select
                    label="LLM Model"
                    options={modelOptions}
                    value={formData.llmModel}
                    onChange={(e) => setFormData({ ...formData, llmModel: e.target.value })}
                  />
                </>
              )}
            </div>
          </section>

          <hr className="border-border-color" />

          {/* Section: Extensions (Tools & Guardrails) */}
          <section data-tour="assistant-details-capabilities" className="flex flex-col gap-5">
            <div>
              <h2 className="text-sm font-semibold text-primary-text uppercase tracking-wider mb-1">Capabilities & Security</h2>
              <p className="text-xs text-secondary-text">Extend actions and enforce rules.</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div
                className="flex flex-col items-center justify-center p-6 bg-tertiary-bg border border-dashed border-border-color rounded-2xl hover:border-accent-primary hover:bg-accent-primary/5 cursor-pointer transition-all group"
                onClick={() => {
                  setNewTool({ tool_id: 'rag_search', credential_id: 'none', usage_instructions: '' });
                  setEditingToolIdx(null);
                  setIsToolModalOpen(true);
                }}
              >
                <div className="w-10 h-10 rounded-full bg-card-bg shadow-sm flex items-center justify-center text-secondary-text group-hover:text-accent-primary mb-3 transition-colors">
                  <Blocks size={20} />
                </div>
                <span className="text-sm font-medium text-primary-text">Tools ({formData.tools?.length || 0})</span>
                <span className="text-xs text-muted-text mt-1 text-center">Give the AI skills</span>
              </div>

              <div
                className="flex flex-col items-center justify-center p-6 bg-tertiary-bg border border-dashed border-border-color rounded-2xl hover:border-accent-success hover:bg-accent-success/5 cursor-pointer transition-all group"
                onClick={() => {
                  setNewGuardrail({ type: '', instructions: '', enforcement: 'block', enabled: true });
                  setEditingGuardrailIdx(null);
                  setIsGuardrailModalOpen(true);
                }}
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
                  <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-card-bg border border-border-color shadow-sm group transition-all hover:border-border-hover cursor-pointer" onClick={() => { setViewingTool(t); setViewingToolIdx(idx); }}>
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-accent-primary/10 text-accent-primary rounded-lg">
                        <Blocks size={14} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-primary-text">{t.tool_id || t.id}</span>
                        <span className="text-xs text-muted-text">
                          {(t.credential_id || t.credential) === 'none' 
                            ? 'No Credential' 
                            : credentials.find((c: any) => c.id === (t.credential_id || t.credential))?.name || 'API Key Required'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-secondary-text hover:bg-secondary-bg h-8 w-8 p-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditTool(t, idx);
                        }}
                      >
                        <Pencil size={14} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-accent-danger hover:bg-accent-danger/10 hover:text-accent-danger h-8 w-8 p-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          const newTools = [...formData.tools];
                          newTools.splice(idx, 1);
                          setFormData({ ...formData, tools: newTools });
                        }}
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {formData.guardrails?.length > 0 && (
              <div className="flex flex-col gap-2 mt-2">
                <h3 className="text-xs font-semibold text-secondary-text uppercase tracking-wider mb-1">Active Guardrails</h3>
                {formData.guardrails.map((g, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-card-bg border border-border-color shadow-sm group transition-all hover:border-border-hover cursor-pointer" onClick={() => { setViewingGuardrail(g); setViewingGuardrailIdx(idx); }}>
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-accent-success/10 text-accent-success rounded-lg">
                        <Shield size={14} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-primary-text">{g.type}</span>
                        <span className="text-xs text-muted-text capitalize">{g.enforcement} • {g.enabled ? 'Enabled' : 'Disabled'}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-secondary-text hover:bg-secondary-bg h-8 w-8 p-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditGuardrail(g, idx);
                        }}
                      >
                        <Pencil size={14} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-accent-danger hover:bg-accent-danger/10 hover:text-accent-danger h-8 w-8 p-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          const newGuardrails = [...formData.guardrails];
                          newGuardrails.splice(idx, 1);
                          setFormData({ ...formData, guardrails: newGuardrails });
                        }}
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

        </div>

        {/* Right Column: System Instructions (Prompt) */}
        <div data-tour="assistant-details-instructions" className="flex-1 flex flex-col bg-secondary-bg border border-border-color rounded-2xl overflow-hidden shadow-sm min-h-[400px] lg:min-h-0">
          <div className="flex flex-col xl:flex-row xl:items-center justify-between p-4 border-b border-border-color bg-card-bg shrink-0 gap-4">
            <div>
              <h2 className="text-sm font-semibold text-primary-text tracking-wide flex items-center gap-2">
                System Instructions
              </h2>
              <p className="text-xs text-secondary-text mt-0.5">Define the core personality and behavior.</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="ghost" size="sm" className="text-xs bg-tertiary-bg" onClick={() => setFormData({ ...formData, system_prompt: "You are a helpful, extremely strictly bound assistant. Follow instructions to the letter." })}>Strict Template</Button>
              <Button variant="ghost" size="sm" className="text-xs bg-tertiary-bg" onClick={() => setFormData({ ...formData, system_prompt: "You are a warm, extremely friendly, and highly empathetic customer support assistant." })}>Friendly Template</Button>
              <div className="w-px h-4 bg-border-color mx-1"></div>
              <Button variant="secondary" size="sm" className="gap-2 text-xs" onClick={() => router.push(`/chat?assistantId=${assistant.assistant_id}`)}>
                <PlayCircle size={14} />
                Test in Playground
              </Button>
            </div>
          </div>

          <div className="flex-1 p-0 relative min-h-[300px] lg:min-h-0">
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
        onClose={() => {
          setIsToolModalOpen(false);
          setEditingToolIdx(null);
        }}
        title={editingToolIdx !== null ? "Edit Tool" : "Add Tool"}
        maxWidth="max-w-xl"
      >
        <form className="flex flex-col gap-5">
          <Select
            label="Tool ID"
            options={availableTools?.map((t: any) => ({ label: t.tool_id, value: t.tool_id })) || []}
            value={newTool.tool_id}
            onChange={(e) => {
              const selectedTool = e.target.value;
              let defaultCred = 'none';
              
              // Find if there is a connector configured for this tool and use its credential_id as default
              let matchedConnector = null;
              if (selectedTool === 'drive_search') {
                matchedConnector = dbConnectors.find((c: any) => c.connector_id === 'google_drive');
              } else if (selectedTool === 'sql_query') {
                matchedConnector = dbConnectors.find((c: any) => c.connector_id === 'postgresql' || c.connector_id === 'mysql');
              }

              if (matchedConnector && matchedConnector.credential_id) {
                defaultCred = matchedConnector.credential_id;
              } else {
                // Fallback to the first available credential
                const applicable = credentials.filter((c: any) => {
                  const provider = c.provider?.toLowerCase() || '';
                  const status = c.status?.toLowerCase() || '';
                  if (selectedTool === 'drive_search') return provider === 'google' && status === 'active';
                  if (selectedTool === 'sql_query') return (provider === 'postgresql' || provider === 'mysql') && status === 'active';
                  return false;
                });
                if (applicable.length > 0) {
                  defaultCred = applicable[0].id;
                }
              }
              setNewTool({ ...newTool, tool_id: selectedTool, credential_id: defaultCred });
            }}
          />
          
          <Select
            label={`Credential${(newTool.tool_id !== 'rag_search' && newTool.tool_id !== 'emit_ui_blocks' && newTool.tool_id !== 'emi_ui_blocks') ? ' *' : ''}`}
            options={[
              ...((newTool.tool_id === 'rag_search' || newTool.tool_id === 'emit_ui_blocks' || newTool.tool_id === 'emi_ui_blocks')
                ? [{ label: 'None', value: 'none' }]
                : []),
              ...credentials
                .filter((c: any) => {
                  const provider = c.provider?.toLowerCase() || '';
                  const status = c.status?.toLowerCase() || '';
                  if (newTool.tool_id === 'drive_search') return provider === 'google' && status === 'active';
                  if (newTool.tool_id === 'sql_query') return (provider === 'postgresql' || provider === 'mysql') && status === 'active';
                  return false;
                })
                .map((c: any) => ({ label: `${c.name} (${c.provider})`, value: c.id }))
            ]}
            value={newTool.credential_id}
            onChange={(e) => setNewTool({ ...newTool, credential_id: e.target.value })}
          />
          {(newTool.tool_id !== 'rag_search' && newTool.tool_id !== 'emit_ui_blocks' && newTool.tool_id !== 'emi_ui_blocks' && (!newTool.credential_id || newTool.credential_id === 'none')) && (
            <p className="text-xs text-accent-danger -mt-3">
              This tool requires a configured credential. If none are listed, please create one in the Credentials tab.
            </p>
          )}
          <Textarea
            label="Usage instructions"
            placeholder="When and how the model should use this tool"
            className="min-h-[100px]"
            value={newTool.usage_instructions}
            onChange={(e) => setNewTool({ ...newTool, usage_instructions: e.target.value })}
          />
          <div className="p-3 bg-tertiary-bg border border-border-color rounded-lg flex items-center text-xs text-secondary-text">
            Additional config is disabled for <code className="mx-1 px-1.5 py-0.5 bg-secondary-bg rounded text-primary-text">{newTool.tool_id}</code>.
          </div>

          <div className="flex items-center justify-end gap-3 mt-2 pt-4 border-t border-border-color">
            <Button variant="ghost" type="button" onClick={() => {
              setIsToolModalOpen(false);
              setEditingToolIdx(null);
            }}>
              Cancel
            </Button>
            <Button variant="primary" type="button" onClick={() => {
              const isCredentialRequired = newTool.tool_id !== 'rag_search' && newTool.tool_id !== 'emit_ui_blocks' && newTool.tool_id !== 'emi_ui_blocks';
              if (isCredentialRequired && (!newTool.credential_id || newTool.credential_id === 'none')) {
                toast.error(`A valid credential is required for the tool '${newTool.tool_id}'.`);
                return;
              }
              if (formData.tools.some((t: any, idx: number) => 
                idx !== editingToolIdx &&
                (t.tool_id === newTool.tool_id || t.id === newTool.tool_id) && 
                ((t.credential_id || 'none') === (newTool.credential_id || 'none') || (t.credential || 'none') === (newTool.credential_id || 'none'))
              )) {
                toast.error(`The tool '${newTool.tool_id}' is already configured with this credential.`);
                return;
              }
              if (editingToolIdx !== null) {
                const newTools = [...formData.tools];
                newTools[editingToolIdx] = newTool;
                setFormData({ ...formData, tools: newTools });
                toast.success('Tool updated in assistant draft. Click Save Changes to apply.');
              } else {
                setFormData({ ...formData, tools: [...formData.tools, newTool] });
                toast.success('Tool added to assistant draft. Click Save Changes to apply.');
              }
              setNewTool({ tool_id: 'rag_search', credential_id: 'none', usage_instructions: '' });
              setEditingToolIdx(null);
              setIsToolModalOpen(false);
            }}>
              {editingToolIdx !== null ? 'Save Changes' : 'Add Tool'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Add Guardrail Modal */}
      <Modal
        isOpen={isGuardrailModalOpen}
        onClose={() => {
          setIsGuardrailModalOpen(false);
          setEditingGuardrailIdx(null);
        }}
        title={editingGuardrailIdx !== null ? "Edit Guardrail" : "Add Guardrail"}
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
            <Button variant="ghost" type="button" onClick={() => {
              setIsGuardrailModalOpen(false);
              setEditingGuardrailIdx(null);
            }}>
              Cancel
            </Button>
            <Button variant="primary" type="button" onClick={() => {
              if (!newGuardrail.type || !newGuardrail.instructions) {
                toast.error('Please fill required fields.');
                return;
              }
              if (editingGuardrailIdx !== null) {
                const newGuardrails = [...formData.guardrails];
                newGuardrails[editingGuardrailIdx] = newGuardrail;
                setFormData({ ...formData, guardrails: newGuardrails });
                toast.success('Guardrail updated in assistant draft. Click Save Changes to apply.');
              } else {
                setFormData({ ...formData, guardrails: [...formData.guardrails, newGuardrail] });
                toast.success('Guardrail added to assistant draft. Click Save Changes to apply.');
              }
              setNewGuardrail({ type: '', instructions: '', enforcement: 'block', enabled: true });
              setEditingGuardrailIdx(null);
              setIsGuardrailModalOpen(false);
            }}>
              {editingGuardrailIdx !== null ? 'Save Changes' : 'Add Guardrail'}
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

      {/* View Guardrail Modal */}
      <Modal
        isOpen={!!viewingGuardrail}
        onClose={() => {
          setViewingGuardrail(null);
          setViewingGuardrailIdx(null);
        }}
        title="Guardrail Details"
        maxWidth="max-w-xl"
      >
        {viewingGuardrail && (
          <div className="flex flex-col gap-5">
            <div>
              <h3 className="text-sm font-semibold text-primary-text mb-1">Type</h3>
              <p className="text-sm text-secondary-text">{viewingGuardrail.type}</p>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-primary-text mb-1">Instructions</h3>
              <div className="p-4 bg-secondary-bg border border-border-color rounded-lg text-sm text-secondary-text whitespace-pre-wrap font-mono">
                {viewingGuardrail.instructions}
              </div>
            </div>
            <div className="flex gap-6">
              <div>
                <h3 className="text-sm font-semibold text-primary-text mb-1">Enforcement</h3>
                <Badge variant="outline" className="capitalize mt-1">{viewingGuardrail.enforcement}</Badge>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-primary-text mb-1">Status</h3>
                <div className="mt-1">
                  <Badge variant={viewingGuardrail.enabled ? "success" : "outline"}>
                    {viewingGuardrail.enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end mt-2 pt-4 border-t border-border-color">
              <Button variant="secondary" onClick={() => {
                setViewingGuardrail(null);
                setViewingGuardrailIdx(null);
              }}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* View Tool Modal */}
      <Modal
        isOpen={!!viewingTool}
        onClose={() => {
          setViewingTool(null);
          setViewingToolIdx(null);
        }}
        title="Tool Details"
        maxWidth="max-w-xl"
      >
        {viewingTool && (
          <div className="flex flex-col gap-5">
            <div>
              <h3 className="text-sm font-semibold text-primary-text mb-1">Tool ID</h3>
              <p className="text-sm text-secondary-text">{viewingTool.tool_id || viewingTool.id}</p>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-primary-text mb-1">Usage Instructions</h3>
              <div className="p-4 bg-secondary-bg border border-border-color rounded-lg text-sm text-secondary-text whitespace-pre-wrap font-mono">
                {viewingTool.usage_instructions || <span className="italic opacity-50">No usage instructions provided.</span>}
              </div>
            </div>
            <div className="flex gap-6">
              <div>
                <h3 className="text-sm font-semibold text-primary-text mb-1">Credential Requirement</h3>
                <Badge variant="outline" className="capitalize mt-1">
                  {(viewingTool.credential_id || viewingTool.credential) === 'none' 
                    ? 'No Credential' 
                    : credentials.find((c: any) => c.id === (viewingTool.credential_id || viewingTool.credential))?.name || 'API Key / Token Required'}
                </Badge>
              </div>
            </div>
            <div className="flex items-center justify-end mt-2 pt-4 border-t border-border-color">
              <Button variant="secondary" onClick={() => {
                setViewingTool(null);
                setViewingToolIdx(null);
              }}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>


      {/* Disable/Enable Confirmation Modal */}
      <Modal
        isOpen={isDisableModalOpen}
        onClose={() => setIsDisableModalOpen(false)}
        title={assistant?.status === 'enabled' ? "Disable Assistant" : "Enable Assistant"}
        description={assistant?.status === 'enabled' ? "Are you sure you want to disable this assistant? Applications depending on it will not be able to use it until you re-enable it." : "Are you sure you want to enable this assistant?"}
        maxWidth="max-w-md"
      >
        <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-border-color">
          <Button variant="ghost" onClick={() => setIsDisableModalOpen(false)}>Cancel</Button>
          <Button variant="primary" onClick={confirmToggleStatus} disabled={statusMutation.isPending}>
            {statusMutation.isPending ? 'Updating...' : (assistant?.status === 'enabled' ? 'Yes, Disable Assistant' : 'Yes, Enable Assistant')}
          </Button>
        </div>
      </Modal>

      {/* Preview Prompt Modal */}
      <Modal
        isOpen={isPreviewModalOpen}
        onClose={() => setIsPreviewModalOpen(false)}
        title="Compiled Prompt Preview"
        description="This is the exact string sent to the LLM. It includes your system prompt, tool instructions, and context."
        maxWidth="max-w-5xl"
      >
        {previewResult && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-6 p-4 bg-tertiary-bg border border-border-color rounded-xl">
              <div className="flex flex-col">
                <span className="text-xs text-secondary-text uppercase tracking-wider font-semibold mb-1">Estimated Tokens</span>
                <span className="text-xl font-bold text-primary-text">{previewResult.estimated_tokens.toLocaleString()}</span>
              </div>

              {previewResult.warnings && previewResult.warnings.length > 0 && (
                <>
                  <div className="w-px h-10 bg-border-color"></div>
                  <div className="flex flex-col">
                    <span className="text-xs text-accent-danger uppercase tracking-wider font-semibold mb-1">Warnings</span>
                    <span className="text-sm font-medium text-accent-danger">{previewResult.warnings[0]}</span>
                  </div>
                </>
              )}
            </div>

            <div className="relative bg-card-bg border border-border-color rounded-lg overflow-y-auto max-h-[500px] custom-scrollbar">
              <pre className="p-4 font-mono text-xs leading-relaxed text-secondary-text whitespace-pre-wrap break-words">
                {previewResult.compiled_prompt}
              </pre>
            </div>

            <div className="flex justify-end gap-3 mt-2 pt-4 border-t border-border-color">
              <Button variant="secondary" onClick={() => setIsPreviewModalOpen(false)}>Close</Button>
            </div>
          </div>
        )}
      </Modal>

    </div>
  );
}

import { Suspense } from 'react';

export default function AssistantDetailsClient() {
  return (
    <Suspense fallback={<div className="flex h-full items-center justify-center">Loading assistant details...</div>}>
      <AssistantDetailsClientContent />
    </Suspense>
  );
}
