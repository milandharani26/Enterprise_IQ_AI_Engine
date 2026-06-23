'use client';

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { Send, Bot, User, Sparkles, Trash2, ChevronDown, FileText } from 'lucide-react';
import { useConversationHooks } from '@/hooks/api/useConversation';
import { useAssistantsHooks, Assistant } from '@/hooks/api/useAssistants';
import { useDocumentsHooks } from '@/hooks/api/useDocuments';
import { useAppStore } from '@/store/useAppStore';

const SUGGESTED_QUESTIONS = [
  'What is fine-tuning?',
  'When should I use fine-tuning vs RAG?',
  'Summarize the key points from my uploaded documents.',
];

function renderAssistantContent(content: string, metadata?: { content_blocks?: any[] }) {
  const blocks = metadata?.content_blocks;
  if (blocks?.length) {
    return blocks
      .map((block: any) => {
        if (block.type === 'markdown' && block.data?.content) return block.data.content;
        if (block.type === 'table') {
          const tableData = block.data || block;
          const cols = tableData.columns || [];
          const rows = tableData.rows || [];
          if (cols.length === 0 && rows.length === 0) return '';
          return [
            `| ${cols.join(' | ')} |`,
            `| ${cols.map(() => '---').join(' | ')} |`,
            ...rows.map((r: any[]) => `| ${r.map(val => String(val ?? '').replace(/\|/g, '\\|')).join(' | ')} |`)
          ].join('\n');
        }
        return JSON.stringify(block.data || block);
      })
      .join('\n\n');
  }
  return content;
}

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function MarkdownMessage({ text }: { text: string }) {
  return (
    <div className="text-sm leading-relaxed space-y-2">
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline break-all" />
          ),
          p: ({ node, ...props }) => <p className="m-0" {...props} />,
          ul: ({ node, ...props }) => <ul className="list-disc pl-4 m-0" {...props} />,
          ol: ({ node, ...props }) => <ol className="list-decimal pl-4 m-0" {...props} />,
          li: ({ node, ...props }) => <li className="m-0" {...props} />
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

export default function ChatPage() {
  const { user, activeOrganizationId, hasHydrated } = useAppStore();
  const { useSendChatMessageMutation } = useConversationHooks();
  const { useAssistantsQuery } = useAssistantsHooks();
  const { useDocumentsQuery } = useDocumentsHooks();
  const { data: assistants = [], isLoading: assistantsLoading } = useAssistantsQuery();
  const { data: documentsResponse } = useDocumentsQuery(activeOrganizationId, {
    pollWhileProcessing: false,
  });

  const indexedDocCount = useMemo(
    () => (documentsResponse?.data || []).filter((d) => d.status === 'indexed').length,
    [documentsResponse]
  );

  const enabledAssistants = useMemo(
    () => assistants.filter((a: Assistant) => a.status === 'enabled'),
    [assistants]
  );

  const [activeConversationId, setActiveConversationId] = useState<string>(() => crypto.randomUUID());
  const sendMutation = useSendChatMessageMutation();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [selectedAssistant, setSelectedAssistant] = useState<Assistant | null>(null);
  const [showAssistantPicker, setShowAssistantPicker] = useState(false);

  const [messages, setMessages] = useState<any[]>([]);

  useEffect(() => {
    if (enabledAssistants.length && !selectedAssistant) {
      const withRag = enabledAssistants.find((a: Assistant) =>
        a.tools?.some((t: any) => t.tool_id === 'rag_search')
      );
      setSelectedAssistant(withRag || enabledAssistants[0]);
    }
  }, [enabledAssistants, selectedAssistant]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sendMutation.isPending]);

  const sendMessage = useCallback(
    (messageContent: string) => {
      if (!messageContent.trim()) return;
      if (!activeOrganizationId) return;
      if (!selectedAssistant) return;

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'USER',
          content: messageContent.trim(),
          timestamp: new Date(),
        },
      ]);

      sendMutation.mutate(
        {
          conversation_id: activeConversationId,
          user_id: user?.id || crypto.randomUUID(),
          organization_id: activeOrganizationId,
          agent_id: selectedAssistant.assistant_id,
          content: messageContent.trim(),
        },
        {
          onSuccess: (data) => {
            const displayContent = renderAssistantContent(data.content, data.metadata_json);
            setMessages((prev) => [
              ...prev,
              {
                id: data.id,
                role: data.role,
                content: displayContent,
                timestamp: new Date(data.created_at),
              },
            ]);
          },
          onError: (err: any) => {
            const detail =
              err?.response?.data?.detail?.message ||
              err?.response?.data?.message ||
              err?.response?.data?.detail ||
              err?.message ||
              'Failed to fetch response from the engine.';
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: 'ASSISTANT',
                content: `Error: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`,
                timestamp: new Date(),
                isError: true,
              },
            ]);
          },
        }
      );
    },
    [activeConversationId, activeOrganizationId, selectedAssistant, sendMutation, user?.id]
  );

  const handleSend = () => {
    if (!input.trim()) return;
    const text = input;
    setInput('');
    sendMessage(text);
  };

  const onSuggestedQuestion = (q: string) => {
    setInput('');
    sendMessage(q);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(crypto.randomUUID());
    setMessages([]);
    setInput('');
  };

  const hasRag = selectedAssistant?.tools?.some((t: any) => t.tool_id === 'rag_search');

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] rounded-3xl overflow-hidden bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm relative">

      <div className="w-full max-w-3xl mx-auto px-4 pt-4 shrink-0 z-20">
        <div className="flex items-center justify-between gap-3 bg-black/5 dark:bg-white/5 backdrop-blur-xl border border-black/10 dark:border-white/10 rounded-full px-4 py-2 shadow-sm dark:shadow-2xl relative">

          <div className="flex items-center gap-2 pl-2">
            <Sparkles className="w-4 h-4 text-blue-500" />
            <span className="font-semibold text-sm text-gray-800 dark:text-gray-200 tracking-tight">
              Document Chat
            </span>
            {hasRag && indexedDocCount > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                {indexedDocCount} doc{indexedDocCount !== 1 ? 's' : ''} indexed
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <button
                onClick={() => setShowAssistantPicker(!showAssistantPicker)}
                disabled={assistantsLoading || !enabledAssistants.length}
                className="flex items-center gap-2 rounded-full h-8 px-3 border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-xs text-gray-700 dark:text-gray-300 transition-colors max-w-[180px]"
              >
                <Bot className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">
                  {selectedAssistant?.assistant_name || 'Select assistant'}
                </span>
                <ChevronDown className="w-3 h-3 shrink-0" />
              </button>
              {showAssistantPicker && enabledAssistants.length > 0 && (
                <div className="absolute right-0 top-full mt-1 w-64 rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-[#1a1a1c] shadow-xl z-50 py-1 max-h-60 overflow-y-auto">
                  {enabledAssistants.map((ast: Assistant) => (
                    <button
                      key={ast.assistant_id}
                      onClick={() => {
                        setSelectedAssistant(ast);
                        setShowAssistantPicker(false);
                      }}
                      className={`w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 dark:hover:bg-white/5 ${
                        selectedAssistant?.assistant_id === ast.assistant_id
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      <div className="font-medium">{ast.assistant_name}</div>
                      {ast.tools?.some((t: any) => t.tool_id === 'rag_search') && (
                        <span className="text-[10px] text-emerald-600 dark:text-emerald-400">RAG enabled</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={handleNewChat}
              className="flex items-center justify-center rounded-full h-8 px-4 border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-xs text-gray-700 dark:text-gray-300 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5 mr-2" /> Clear
            </button>
          </div>
        </div>
      </div>

      <div className="px-4 md:px-8 pt-3 space-y-2 max-w-4xl mx-auto w-full">
        {hasHydrated && !activeOrganizationId && (
          <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-lg px-3 py-2">
            Select an organization in Settings → General to scope document search.
          </p>
        )}
        {hasHydrated && activeOrganizationId && indexedDocCount === 0 && (
          <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-lg px-3 py-2">
            No indexed documents yet.{' '}
            <Link href="/documents" className="underline font-medium">
              Upload a file
            </Link>{' '}
            before asking document questions.
          </p>
        )}
        {selectedAssistant && !hasRag && (
          <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-lg px-3 py-2">
            This assistant does not have <code>rag_search</code> — add it in Assistants → Detail → Tools.
          </p>
        )}
        <Link
          href="/documents"
          className="inline-flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 hover:underline"
        >
          <FileText className="w-3.5 h-3.5" />
          Upload documents for RAG
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="min-h-full flex flex-col items-center justify-start pt-4 md:pt-12 pb-20 animate-in fade-in slide-in-from-bottom-8 duration-700">
              <div className="relative w-16 h-16 mb-8">
                <div className="relative w-full h-full rounded-2xl bg-gray-50 dark:bg-white/5 flex items-center justify-center border border-gray-200 dark:border-white/10 shadow-sm">
                  <Bot className="w-6 h-6 text-gray-700 dark:text-gray-300" />
                </div>
              </div>
              <h2 className="text-3xl font-semibold mb-3 text-gray-900 dark:text-white text-center tracking-tight">
                Chat with your documents
              </h2>
              <p className="text-gray-500 dark:text-gray-400 mb-8 max-w-md text-center text-sm">
                Ask questions about your indexed files. The assistant uses <code className="text-xs bg-gray-100 dark:bg-white/10 px-1 rounded">rag_search</code> to find relevant chunks in pgvector, then answers with citations.
              </p>
              {hasRag && indexedDocCount > 0 && (
                <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => onSuggestedQuestion(q)}
                      disabled={sendMutation.isPending || !activeOrganizationId}
                      className="text-xs px-3 py-2 rounded-full border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 hover:bg-blue-50 dark:hover:bg-blue-500/10 hover:border-blue-300 dark:hover:border-blue-500/30 text-gray-700 dark:text-gray-300 transition-colors disabled:opacity-50"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 max-w-[85%] ${message.role === 'USER' ? 'ml-auto flex-row-reverse' : ''} animate-in fade-in slide-in-from-bottom-2`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-md dark:shadow-lg ${
                    message.role === 'USER'
                      ? 'bg-gradient-to-br from-blue-500 to-purple-600'
                      : message.isError
                        ? 'bg-red-500/10 border border-red-500/30'
                        : 'bg-black/5 dark:bg-white/10 backdrop-blur-md border border-black/10 dark:border-white/10'
                  }`}
                >
                  {message.role === 'USER' ? (
                    <User className="w-4 h-4 text-white" />
                  ) : (
                    <Bot className={`w-4 h-4 ${message.isError ? 'text-red-500' : 'text-gray-700 dark:text-gray-300'}`} />
                  )}
                </div>
                <div
                  className={`px-5 py-3.5 text-sm rounded-3xl shadow-sm dark:shadow-lg border max-w-full ${
                    message.role === 'USER'
                      ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-tr-sm border-blue-500/50 shadow-blue-500/20'
                      : message.isError
                        ? 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30 text-red-700 dark:text-red-300 rounded-tl-sm'
                        : 'bg-white/50 dark:bg-white/5 backdrop-blur-xl border-black/10 dark:border-white/10 text-gray-800 dark:text-gray-200 rounded-tl-sm'
                  }`}
                >
                  {message.role === 'USER' ? (
                    <span className="whitespace-pre-wrap">{message.content}</span>
                  ) : (
                    <MarkdownMessage text={message.content} />
                  )}
                </div>
              </div>
            ))
          )}
          {sendMutation.isPending && (
            <div className="flex gap-3 max-w-[85%] animate-in fade-in slide-in-from-bottom-2">
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-md dark:shadow-lg bg-black/5 dark:bg-white/10 backdrop-blur-md border border-black/10 dark:border-white/10">
                <Bot className="w-4 h-4 text-gray-700 dark:text-gray-300" />
              </div>
              <div className="px-5 py-4 text-sm rounded-3xl shadow-sm dark:shadow-lg border bg-white/50 dark:bg-white/5 backdrop-blur-xl border-black/10 dark:border-white/10 text-gray-500 dark:text-gray-400 rounded-tl-sm">
                Searching documents and generating answer…
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="p-4 md:p-6 bg-gradient-to-t from-background via-background to-transparent pt-10">
        <div className="max-w-4xl mx-auto relative group">
          <div className="flex-1 min-w-0 relative flex flex-col items-end">
            <textarea
              placeholder={
                !selectedAssistant
                  ? 'Create an assistant first…'
                  : indexedDocCount === 0
                    ? 'Upload documents first, then ask questions…'
                    : 'Ask about your uploaded documents…'
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sendMutation.isPending || !selectedAssistant || !activeOrganizationId}
              className="min-h-[60px] max-h-[200px] w-full pr-16 pl-6 py-4 resize-none text-sm rounded-3xl border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 backdrop-blur-xl shadow-lg dark:shadow-2xl focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all text-gray-900 dark:text-white placeholder:text-gray-500 outline-none"
              rows={1}
            />
            <div className="absolute right-3 bottom-3 flex items-center gap-1.5">
              <button
                onClick={handleSend}
                disabled={!input.trim() || sendMutation.isPending || !selectedAssistant || !activeOrganizationId}
                className={`w-9 h-9 rounded-full p-0 flex items-center justify-center transition-all ${
                  input.trim() && !sendMutation.isPending && selectedAssistant && activeOrganizationId
                    ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                    : 'bg-black/5 dark:bg-white/5 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                }`}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
