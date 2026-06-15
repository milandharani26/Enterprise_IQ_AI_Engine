'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Paperclip, Mic, Sparkles, History, ChevronDown, X, MessageSquare, Check, FileText, StopCircle, Plus } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const STATIC_ASSISTANTS = [
  { id: 'general', name: 'General Assistant', icon: <Bot className="w-4 h-4 text-blue-500 dark:text-blue-400" /> },
  { id: 'code', name: 'Code Expert', icon: <Bot className="w-4 h-4 text-purple-500 dark:text-purple-400" /> },
  { id: 'data', name: 'Data Analyst', icon: <Bot className="w-4 h-4 text-emerald-500 dark:text-emerald-400" /> },
  { id: 'creative', name: 'Creative Writer', icon: <Bot className="w-4 h-4 text-pink-500 dark:text-pink-400" /> },
];

const STATIC_HISTORY = [
  { id: '1', title: 'Previous chat about AI', date: '2 hours ago' },
  { id: '2', title: 'Debugging React component', date: 'Yesterday' },
  { id: '3', title: 'Database schema design', date: '3 days ago' },
  { id: '4', title: 'Marketing copy generation', date: 'Last week' },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // New State for Assistant Selection and History
  const [selectedAssistant, setSelectedAssistant] = useState(STATIC_ASSISTANTS[0]);
  const [isAssistantDropdownOpen, setIsAssistantDropdownOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // New State for File and Audio
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isThinking, setIsThinking] = useState(false);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } else {
      setRecordingTime(0);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() && !selectedFile) return;
    
    let messageContent = input.trim();
    if (selectedFile) {
      messageContent = `[Attachment: ${selectedFile.name}]\n${messageContent}`;
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageContent,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSelectedFile(null);
    setIsThinking(true);
    
    // Mock response
    setTimeout(() => {
      setIsThinking(false);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I'm a placeholder response from ${selectedAssistant.name}! The backend is not yet connected.`,
        timestamp: new Date()
      }]);
    }, 1000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.assistant-dropdown-container')) {
        setIsAssistantDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] rounded-3xl overflow-hidden bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm relative">
      
      {/* Floating Header */}
      <div className="w-full max-w-3xl mx-auto px-4 pt-4 shrink-0 z-20">
        <div className="flex items-center justify-between gap-3 bg-black/5 dark:bg-white/5 backdrop-blur-xl border border-black/10 dark:border-white/10 rounded-full px-4 py-2 shadow-sm dark:shadow-2xl relative">
          
          {/* Assistant Selector */}
          <div className="relative assistant-dropdown-container">
            <button 
              onClick={() => setIsAssistantDropdownOpen(!isAssistantDropdownOpen)}
              className="flex items-center gap-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-full pr-3 pl-1 py-1 transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-blue-500/10 dark:bg-blue-500/20 flex items-center justify-center">
                {selectedAssistant.icon}
              </div>
              <span className="font-medium text-sm text-gray-800 dark:text-gray-200">{selectedAssistant.name}</span>
              <ChevronDown className={`w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform ${isAssistantDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {isAssistantDropdownOpen && (
              <div className="absolute top-full left-0 mt-2 w-56 rounded-2xl bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-xl border border-black/10 dark:border-white/10 shadow-xl dark:shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-2">
                <div className="p-2 space-y-1">
                  {STATIC_ASSISTANTS.map(assistant => (
                    <button
                      key={assistant.id}
                      onClick={() => {
                        setSelectedAssistant(assistant);
                        setIsAssistantDropdownOpen(false);
                      }}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${
                        selectedAssistant.id === assistant.id 
                          ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' 
                          : 'text-gray-700 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white'
                      }`}
                    >
                      <div className="w-6 h-6 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
                        {assistant.icon}
                      </div>
                      <span className="flex-1 text-left">{assistant.name}</span>
                      {selectedAssistant.id === assistant.id && <Check className="w-4 h-4 shrink-0" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button 
              onClick={() => setMessages([])}
              className="flex items-center justify-center rounded-full h-8 px-4 border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-xs text-gray-700 dark:text-gray-300 transition-colors"
            >
              <Plus className="w-3 h-3 mr-2" /> New Chat
            </button>
            <button 
              onClick={() => setIsHistoryOpen(true)}
              className="flex items-center justify-center rounded-full h-8 px-4 border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-xs text-gray-700 dark:text-gray-300 transition-colors"
            >
              <History className="w-3 h-3 mr-2" /> History
            </button>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="min-h-full flex flex-col items-center justify-start pt-4 md:pt-16 pb-20 animate-in fade-in slide-in-from-bottom-8 duration-700">
              <div className="relative w-16 h-16 mb-8">
                <div className="relative w-full h-full rounded-2xl bg-gray-50 dark:bg-white/5 flex items-center justify-center border border-gray-200 dark:border-white/10 shadow-sm">
                  <Sparkles className="w-6 h-6 text-gray-700 dark:text-gray-300" />
                </div>
              </div>
              <h2 className="text-3xl font-semibold mb-3 text-gray-900 dark:text-white text-center tracking-tight">
                How can I help you today?
              </h2>
              <p className="text-gray-500 dark:text-gray-400 mb-12 max-w-md text-center text-sm">
                I'm your AI assistant. I can help you analyze data, generate code, or answer any questions you might have.
              </p>
            </div>
          ) : (
            messages.map(message => (
              <div
                key={message.id}
                className={`flex gap-3 max-w-[85%] ${message.role === 'user' ? 'ml-auto flex-row-reverse' : ''} animate-in fade-in slide-in-from-bottom-2`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-md dark:shadow-lg ${
                  message.role === 'user' 
                    ? 'bg-gradient-to-br from-blue-500 to-purple-600' 
                    : 'bg-black/5 dark:bg-white/10 backdrop-blur-md border border-black/10 dark:border-white/10'
                }`}>
                  {message.role === 'user' ? <User className="w-4 h-4 text-white" /> : selectedAssistant.icon}
                </div>
                <div className={`px-5 py-3.5 text-sm rounded-3xl shadow-sm dark:shadow-lg border ${
                  message.role === 'user'
                    ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-tr-sm border-blue-500/50 shadow-blue-500/20'
                    : 'bg-white/50 dark:bg-white/5 backdrop-blur-xl border-black/10 dark:border-white/10 text-gray-800 dark:text-gray-200 rounded-tl-sm'
                }`}>
                  {message.content}
                </div>
              </div>
            ))
          )}
          {isThinking && (
            <div className="flex gap-3 max-w-[85%] animate-in fade-in slide-in-from-bottom-2">
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-md dark:shadow-lg bg-black/5 dark:bg-white/10 backdrop-blur-md border border-black/10 dark:border-white/10">
                {selectedAssistant.icon}
              </div>
              <div className="px-5 py-4 text-sm rounded-3xl shadow-sm dark:shadow-lg border bg-white/50 dark:bg-white/5 backdrop-blur-xl border-black/10 dark:border-white/10 text-gray-800 dark:text-gray-200 rounded-tl-sm flex items-center gap-1.5 h-[46px]">
                <span className="w-1.5 h-1.5 bg-gray-500 dark:bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-gray-500 dark:bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-gray-500 dark:bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Floating Input Area */}
      <div className="p-4 md:p-6 bg-gradient-to-t from-background via-background to-transparent pt-10">
        <div className="max-w-4xl mx-auto relative group">
          <div className="flex-1 min-w-0 relative flex flex-col items-end">
            {selectedFile && (
              <div className="w-full flex justify-start mb-2 animate-in fade-in slide-in-from-bottom-1">
                <div className="flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 px-3 py-1.5 rounded-full text-blue-600 dark:text-blue-400 text-xs">
                  <FileText className="w-3.5 h-3.5" />
                  <span className="truncate max-w-[200px]">{selectedFile.name}</span>
                  <button onClick={() => setSelectedFile(null)} className="hover:text-blue-800 dark:hover:text-blue-200 transition-colors ml-1">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
            
            {isRecording && (
              <div className="absolute left-6 top-[28px] -translate-y-1/2 flex items-center gap-2 text-red-500 dark:text-red-400 animate-pulse text-sm z-10">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                Recording Audio... 0:{recordingTime.toString().padStart(2, '0')}
              </div>
            )}

            <textarea
              placeholder={isRecording ? "" : "Type your message..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isRecording}
              className={`min-h-[60px] max-h-[200px] w-full pr-32 pl-6 py-4 resize-none text-sm rounded-3xl border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 backdrop-blur-xl shadow-lg dark:shadow-2xl focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all text-gray-900 dark:text-white placeholder:text-gray-500 outline-none ${isRecording ? 'opacity-50' : ''}`}
              rows={1}
            />
            <div className="absolute right-3 bottom-3 flex items-center gap-1.5">
              <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) setSelectedFile(file);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
              />
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center justify-center w-9 h-9 rounded-full hover:bg-black/10 dark:hover:bg-white/10 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                <Paperclip className="w-4 h-4" />
              </button>
              <button 
                onClick={() => {
                  if (isRecording) {
                     setIsRecording(false);
                     setInput(prev => prev + (prev ? ' ' : '') + "This is a transcribed audio message.");
                  } else {
                     setIsRecording(true);
                  }
                }}
                className={`flex items-center justify-center w-9 h-9 rounded-full transition-colors ${
                  isRecording 
                    ? 'bg-red-500/20 text-red-600 dark:text-red-400 hover:bg-red-500/30' 
                    : 'hover:bg-black/10 dark:hover:bg-white/10 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {isRecording ? <StopCircle className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
              <button 
                onClick={handleSend}
                disabled={(!input.trim() && !selectedFile) || isRecording}
                className={`w-9 h-9 rounded-full p-0 flex items-center justify-center transition-all ${
                  (input.trim() || selectedFile) && !isRecording
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

      {/* History Drawer Overlay */}
      {isHistoryOpen && (
        <div 
          className="absolute inset-0 bg-black/10 dark:bg-black/40 backdrop-blur-sm z-40 animate-in fade-in"
          onClick={() => setIsHistoryOpen(false)}
        />
      )}

      {/* History Drawer */}
      <div className={`absolute top-0 right-0 h-full w-80 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-xl border-l border-black/10 dark:border-white/10 z-50 transform transition-transform duration-300 ease-in-out flex flex-col shadow-2xl ${
        isHistoryOpen ? 'translate-x-0' : 'translate-x-full'
      }`}>
        <div className="flex items-center justify-between p-6 border-b border-black/10 dark:border-white/10">
          <h3 className="font-semibold text-lg text-gray-900 dark:text-white">Chat History</h3>
          <button 
            onClick={() => setIsHistoryOpen(false)}
            className="w-8 h-8 rounded-full hover:bg-black/10 dark:hover:bg-white/10 flex items-center justify-center text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            {STATIC_HISTORY.map((item) => (
              <button
                key={item.id}
                className="w-full flex flex-col items-start p-3 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 transition-colors text-left group"
              >
                <div className="flex items-center gap-2 mb-1 w-full">
                  <MessageSquare className="w-4 h-4 text-gray-400 dark:text-gray-500 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors" />
                  <span className="font-medium text-sm text-gray-800 dark:text-gray-200 group-hover:text-gray-900 dark:group-hover:text-white truncate flex-1">{item.title}</span>
                </div>
                <span className="text-xs text-gray-500 dark:text-gray-500 pl-6">{item.date}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
