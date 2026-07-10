'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { usePathname, useRouter } from 'next/navigation';
import { useTourStore } from '@/store/useTourStore';
import { useAssistantsHooks } from '@/hooks/api/useAssistants';

// Dynamically import react-joyride to ensure it doesn't trigger SSR hydration errors
const Joyride = dynamic(() => import('react-joyride').then((mod) => mod.Joyride), { ssr: false });

// High-performance canvas confetti system with left and right side bursts
function triggerConfetti() {
  if (typeof window === 'undefined') return;

  const canvas = document.createElement('canvas');
  canvas.style.position = 'fixed';
  canvas.style.top = '0';
  canvas.style.left = '0';
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  canvas.style.pointerEvents = 'none';
  canvas.style.zIndex = '99999';
  document.body.appendChild(canvas);

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const colors = ['#5B6AF8', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#3B82F6'];
  const particles: any[] = [];

  // Create particles from left side burst
  for (let i = 0; i < 70; i++) {
    particles.push({
      x: 0,
      y: canvas.height * 0.75,
      vx: Math.random() * 16 + 12,
      vy: -(Math.random() * 22 + 16),
      size: Math.random() * 9 + 6,
      color: colors[Math.floor(Math.random() * colors.length)],
      rotation: Math.random() * 360,
      rotationSpeed: Math.random() * 12 - 6,
      opacity: 1,
    });
  }

  // Create particles from right side burst
  for (let i = 0; i < 70; i++) {
    particles.push({
      x: canvas.width,
      y: canvas.height * 0.75,
      vx: -(Math.random() * 16 + 12),
      vy: -(Math.random() * 22 + 16),
      size: Math.random() * 9 + 6,
      color: colors[Math.floor(Math.random() * colors.length)],
      rotation: Math.random() * 360,
      rotationSpeed: Math.random() * 12 - 6,
      opacity: 1,
    });
  }

  let animationFrameId: number;

  function update() {
    ctx!.clearRect(0, 0, canvas.width, canvas.height);

    let active = false;

    particles.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.55; // gravity
      p.vx *= 0.975; // friction
      p.rotation += p.rotationSpeed;

      // Start fading out when falling down past middle screen
      if (p.y > canvas.height * 0.45) {
        p.opacity -= 0.012;
      }

      if (p.opacity > 0) {
        active = true;
        ctx!.save();
        ctx!.translate(p.x, p.y);
        ctx!.rotate((p.rotation * Math.PI) / 180);
        ctx!.globalAlpha = p.opacity;
        ctx!.fillStyle = p.color;
        ctx!.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
        ctx!.restore();
      }
    });

    if (active) {
      animationFrameId = requestAnimationFrame(update);
    } else {
      document.body.removeChild(canvas);
    }
  }

  update();
}

export function Tour() {
  const { run, stepIndex, setStepIndex, stopTour, completedTours, completeTour, initializeCompletedTours } = useTourStore();
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const { useAssistantsQuery } = useAssistantsHooks();
  const { data: accountsList } = useAssistantsQuery();
  const assistants = Array.isArray(accountsList) ? accountsList : [];

  useEffect(() => {
    setMounted(true);
    initializeCompletedTours();
  }, [initializeCompletedTours]);

  // Determine tour type based on pathname
  const isDashboard = pathname === '/dashboard' || pathname === '/dashboard/';
  const isChat = pathname === '/chat' || pathname === '/chat/';
  const isDocuments = pathname === '/documents' || pathname === '/documents/';
  const isAssistants = pathname === '/assistants' || pathname === '/assistants/';
  const isAssistantDetail = pathname === '/assistants/detail' || pathname === '/assistants/detail/';
  const isConnector = pathname === '/connector' || pathname === '/connector/';
  const isCredentials = pathname === '/credentials' || pathname === '/credentials/';
  const isServiceToken = pathname === '/settings/service-token' || pathname === '/settings/service-token/';
  const isSettings = pathname?.startsWith('/settings') && !isServiceToken;

  let tourId = '';
  let steps: any[] = [];

  if (isDashboard) {
    tourId = 'dashboard';
    steps = [
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Welcome to EnterpriseIQ AI!',
        content: (
          <div className="flex flex-col gap-3">
            <p className="m-0 text-sm">
              EnterpriseIQ AI is a secure control center for orchestrating enterprise intelligence. The platform consists of four main capabilities:
            </p>
            <ul className="m-0 pl-5 text-xs flex flex-col gap-1 list-disc text-secondary-text">
              <li>
                <strong className="text-primary-text">AI Assistants:</strong> Deploy autonomous agents with custom system prompt rules and tool access.
              </li>
              <li>
                <strong className="text-primary-text">Knowledge Base:</strong> Ingest local files, databases, or Google Drive folders into semantic search indexes (RAG).
              </li>
              <li>
                <strong className="text-primary-text">Integrations & Credentials:</strong> Set up automated sync connectors and bind API secrets securely.
              </li>
              <li>
                <strong className="text-primary-text">Service Tokens:</strong> Generate secure API keys for authenticating developer scripts and external applications.
              </li>
            </ul>
            <p className="m-0 text-sm">
              Let\'s take a quick walk through these core features!
            </p>
          </div>
        ),
        disableBeacon: true,
      },
      {
        target: '[data-tour="stats-grid"]',
        placement: 'bottom' as const,
        title: 'System Analytics Overview',
        content: 'Monitor stats including active assistants, synced documents count, integration volume, and daily user conversations.',
      },
      {
        target: '[data-tour="dashboard-charts"]',
        placement: 'top' as const,
        title: 'Engagement & Knowledge Charts',
        content: 'Track real-time conversation engagement graphs over the last 7 days and view a breakdown of your synced documents base in the donut chart.',
      },
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Dashboard Tour Complete!',
        content: 'You have explored the dashboard overview. Would you like to proceed to the Chat console tour next?',
        locale: {
          back: 'No',
          next: 'Yes',
          last: 'Yes',
        },
      },
    ];
  } else if (isChat) {
    tourId = 'chat';
    steps = [
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Chat Console',
        content: 'Welcome to the interactive chat console. Here you can run live test conversations with your AI assistants.',
        disableBeacon: true,
      },
      {
        target: '[data-tour="chat-assistant-picker"]',
        placement: 'bottom' as const,
        title: 'Assistant Selector',
        content: 'Select which assistant you want to converse with. Each assistant utilizes its own tools and knowledge bases.',
      },
      {
        target: '[data-tour="chat-clear-button"]',
        placement: 'bottom' as const,
        title: 'Clear Chat',
        content: 'Click here to clear the current chat thread and start a fresh session.',
      },
      {
        target: '[data-tour="chat-input-textarea"]',
        placement: 'top' as const,
        title: 'Chat Input',
        content: 'Type your message or prompt here. If the assistant has document search tools, it will query your knowledge base to answer.',
      },
      {
        target: '[data-tour="chat-send-button"]',
        placement: 'left' as const,
        title: 'Send Message',
        content: 'Submit your prompt to query the assistant and get a real-time response.',
      },
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Chat Tour Complete!',
        content: 'You now know how to chat with assistants. Would you like to proceed to the Documents library tour next?',
        locale: {
          back: 'No',
          next: 'Yes',
          last: 'Yes',
        },
      },
    ];
  } else if (isDocuments) {
    tourId = 'documents';
    steps = [
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Documents Library',
        content: 'Welcome to the Documents library. This is where you upload files and verify external sources to build your organization knowledge base.',
        disableBeacon: true,
      },
      {
        target: '[data-tour="documents-tabs"]',
        placement: 'bottom' as const,
        title: 'Data Sources',
        content: 'Switch between local uploaded files, synced Google Drive folders, and database schema metadata.',
      },
      {
        target: '[data-tour="documents-upload-zone"]',
        placement: 'bottom' as const,
        title: 'Upload Zone',
        content: 'Drag and drop or click here to upload local files (PDFs, Word docs, Markdown, Excel, CSV) directly into your vector store.',
      },
      {
        target: '[data-tour="documents-search-input"]',
        placement: 'bottom' as const,
        title: 'Search & Filters',
        content: 'Search files by title or reference ID, and filter them by vector indexing status.',
      },
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Documents Tour Complete!',
        content: 'You have learned how to manage your knowledge base files. Would you like to proceed to the AI Assistants hub tour next?',
        locale: {
          back: 'No',
          next: 'Yes',
          last: 'Yes',
        },
      },
    ];
  } else if (isAssistants) {
    tourId = 'assistants';
    steps = [
      {
        target: 'body',
        placement: 'center' as const,
        title: 'AI Assistants Hub',
        content: 'Create and configure your autonomous AI agents. Define their system prompt instructions and bind tools/knowledge here.',
        disableBeacon: true,
      },
      {
        target: '[data-tour="assistants-create-button"]',
        placement: 'left' as const,
        title: 'Create Assistant',
        content: 'Click here to register a new assistant, select its foundational LLM, and describe its purpose.',
      },
      {
        target: '[data-tour="assistants-filters"]',
        placement: 'bottom' as const,
        title: 'Search Agents',
        content: 'Quickly find assistants by name or filter them based on their enabled/disabled status.',
      },
      {
        target: '[data-tour="assistants-grid"]',
        placement: 'top' as const,
        title: 'Deployed Assistants',
        content: 'Review active agents, check call usage counters, check mapped tools, and click to configure system prompts/parameters.',
      },
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Assistants Tour Complete!',
        content: assistants.length > 0 
          ? 'You have explored the AI assistants overview. Would you like to proceed to configure the assistant details next?'
          : 'You have explored the AI assistants overview. Currently, no assistant is available in this workspace. You need to create an assistant first to tour the configuration details page. Would you like to proceed to the Connectors integration tour instead?',
        locale: {
          back: 'No',
          next: 'Yes',
          last: 'Yes',
        },
      },
    ];
  } else if (isAssistantDetail) {
    tourId = 'assistant-detail';
    steps = [
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Assistant Configuration',
        content: 'Welcome to the Assistant Configuration panel. Here you can edit prompt rules, bind external tools, and apply guardrails for your AI agent.',
        disableBeacon: true,
      },
      {
        target: '[data-tour="assistant-details-identity"]',
        placement: 'right' as const,
        title: 'Basic Identity',
        content: 'Edit the display name and description of your assistant to keep track of its role.',
      },
      {
        target: '[data-tour="assistant-details-capabilities"]',
        placement: 'right' as const,
        title: 'Capabilities & Security',
        content: 'Add powerful tools (like RAG database search or drive search) and enable security guardrails to enforce safety rules.',
      },
      {
        target: '[data-tour="assistant-details-instructions"]',
        placement: 'left' as const,
        title: 'System Instructions',
        content: 'Define the system prompt here. This dictates the core personality, style, and instructions that the LLM will follow.',
      },
      {
        target: '[data-tour="assistant-details-actions"]',
        placement: 'bottom' as const,
        title: 'Save & Manage',
        content: 'Save your settings, perform a prompt token compilation check, toggle status, or delete the agent.',
      },
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Configuration Tour Complete!',
        content: 'You have explored assistant configuration. Would you like to proceed to the Connectors integration tour next?',
        locale: {
          back: 'No',
          next: 'Yes',
          last: 'Yes',
        },
      },
    ];
  } else if (isConnector) {
    tourId = 'connector';
    steps = [
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Data Connectors',
        content: 'Integrate external platforms (Google Drive, PostgreSQL, MySQL) to automate periodic data synchronization.',
        disableBeacon: true,
      },
      {
        target: '[data-tour="connectors-filters"]',
        placement: 'bottom' as const,
        title: 'Search Connectors',
        content: 'Search available third-party platforms and filter them by configuration status.',
      },
      {
        target: '[data-tour="connectors-list"]',
        placement: 'top' as const,
        title: 'Connector Settings',
        content: 'Configure connections, link them to api keys/credentials, trigger manual database syncs, and toggle integrations on/off.',
      },
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Connectors Tour Complete!',
        content: 'You have explored integration sources. Would you like to proceed to the Credentials store tour next?',
        locale: {
          back: 'No',
          next: 'Yes',
          last: 'Yes',
        },
      },
    ];
  } else if (isCredentials) {
    tourId = 'credentials';
    steps = [
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Credentials Store',
        content: 'Manage API keys, OAuth client credentials, and database server host logins securely.',
        disableBeacon: true,
      },
      {
        target: '[data-tour="credentials-create-button"]',
        placement: 'left' as const,
        title: 'Register Secrets',
        content: 'Securely save database logins, Google OAuth client details, or API tokens to be mapped to data connectors.',
      },
      {
        target: '[data-tour="credentials-list"]',
        placement: 'top' as const,
        title: 'Stored Credentials',
        content: 'Check credential connectivity status, run test connections to PostgreSQL or Google Drive, or remove old secrets.',
      },
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Credentials Tour Complete!',
        content: 'You have completed the credentials vault tour. Would you like to proceed to the Service Tokens settings tour next?',
        locale: {
          back: 'No',
          next: 'Yes',
          last: 'Yes',
        },
      },
    ];
  } else if (isServiceToken) {
    tourId = 'service-token';
    steps = [
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Service Tokens',
        content: 'Welcome to the Service Tokens page. Here you can generate API keys to securely communicate with the platform via scripts or backend servers.',
        disableBeacon: true,
      },
      {
        target: '[data-tour="service-tokens-create-button"]',
        placement: 'left' as const,
        title: 'Create Token',
        content: 'Generate a new API key. You can specify a name, optional note/description, and an expiration date.',
      },
      {
        target: '[data-tour="service-tokens-filters"]',
        placement: 'bottom' as const,
        title: 'Filter Keys',
        content: 'Filter tokens based on their state to view Active or Revoked keys.',
      },
      {
        target: '[data-tour="service-tokens-list"]',
        placement: 'top' as const,
        title: 'Token Registry',
        content: 'View details of generated keys including prefixes, timelines, and status. Remember: the actual secret token value is only displayed once upon creation.',
      },
      {
        target: 'body',
        placement: 'center' as const,
        title: 'Service Tokens Tour Complete!',
        content: 'You have completed the Service Tokens walkthrough. Would you like to proceed to the General settings tour next?',
        locale: {
          back: 'No',
          next: 'Yes',
          last: 'Yes',
        },
      },
    ];
  } else if (isSettings) {
    tourId = 'settings';
    steps = [
      {
        target: 'body',
        placement: 'center' as const,
        title: 'General Settings',
        content: 'Configure profile data and organization wide workspace parameters.',
        disableBeacon: true,
      },
      {
        target: '[data-tour="settings-profile-card"]',
        placement: 'top' as const,
        title: 'Profile Information',
        content: 'Update your display name, view your login email, and apply changes.',
      },
      {
        target: 'body',
        placement: 'center' as const,
        title: 'All Tours Completed!',
        content: 'Congratulations! You have completed the entire onboarding guide for EnterpriseIQ AI. Click Finish to exit.',
      },
    ];
  }

  useEffect(() => {
    if (!mounted || !tourId) return;

    // Check if the current page tour has already been completed
    const alreadyCompleted = completedTours[tourId];

    if (!alreadyCompleted && !run) {
      // Auto-start page tour after short delay to let layout mount and page query finish
      const timer = setTimeout(() => {
        useTourStore.getState().startTour();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [mounted, pathname, tourId, completedTours, run]);

  if (!mounted || !tourId || !run || steps.length === 0) return null;

  const handleJoyrideCallback = (data: any) => {
    const { action, index, status, type } = data;
    
    if (type === 'step:after' || type === 'target:not_found') {
      const isTransitionStep = index === steps.length - 1;
      if (isTransitionStep && action === 'prev') {
        stopTour();
      } else {
        setStepIndex(index + (action === 'prev' ? -1 : 1));
      }
    } else if (['finished', 'skipped'].includes(status)) {
      completeTour(tourId);

      if (status === 'finished') {
        // Redirection chain logic to link every page's tour
        let nextPath = '';
        if (tourId === 'dashboard') nextPath = '/chat';
        else if (tourId === 'chat') nextPath = '/documents';
        else if (tourId === 'documents') nextPath = '/assistants';
        else if (tourId === 'assistants') {
          if (assistants.length > 0) {
            const firstId = assistants[0].assistant_id;
            nextPath = `/assistants/detail?id=${firstId}`;
          } else {
            nextPath = '/connector';
          }
        }
        else if (tourId === 'assistant-detail') nextPath = '/connector';
        else if (tourId === 'connector') nextPath = '/credentials';
        else if (tourId === 'credentials') nextPath = '/settings/service-token';
        else if (tourId === 'service-token') nextPath = '/settings/general';
        else if (tourId === 'settings') {
          // Final settings tour finished -> Redirect back to Dashboard
          nextPath = '/dashboard';
        }

        if (nextPath) {
          router.push(nextPath);
          
          if (tourId === 'settings') {
            // Trigger beautiful left & right confetti celebration on landing
            setTimeout(() => {
              triggerConfetti();
            }, 1000);
          } else {
            // Wait briefly for new page rendering before starting next tour
            setTimeout(() => {
              useTourStore.getState().startTour();
            }, 1000);
          }
        }
      }
    }
  };

  return (
    <Joyride
      steps={steps}
      run={run}
      stepIndex={stepIndex}
      continuous={true}
      onEvent={handleJoyrideCallback}
      options={{
        arrowColor: 'var(--color-tour-bg)',
        backgroundColor: 'var(--color-tour-bg)',
        overlayColor: 'rgba(0, 0, 0, 0.45)',
        primaryColor: 'var(--color-accent-primary)',
        textColor: 'var(--color-primary-text)',
        zIndex: 1000,
        showProgress: true,
        buttons: ['back', 'close', 'primary', 'skip'],
        width: 480,
      }}
      styles={{
        tooltip: {
          borderRadius: '16px',
          padding: '20px',
          border: '1px solid var(--color-border-color)',
          boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
          backdropFilter: 'blur(12px)',
          background: 'var(--color-tour-bg)',
        },
        tooltipContainer: {
          textAlign: 'left' as const,
        },
        tooltipTitle: {
          fontSize: '16px',
          fontWeight: 700,
          marginBottom: '8px',
          color: 'var(--color-primary-text)',
        },
        tooltipContent: {
          fontSize: '13px',
          lineHeight: '1.5',
          color: 'var(--color-secondary-text)',
        },
        buttonPrimary: {
          backgroundColor: 'var(--color-accent-primary)',
          color: '#ffffff',
          borderRadius: '8px',
          fontSize: '13px',
          fontWeight: 600,
          padding: '8px 16px',
          outline: 'none',
          cursor: 'pointer',
        },
        buttonBack: {
          color: 'var(--color-secondary-text)',
          fontSize: '13px',
          fontWeight: 600,
          marginRight: '12px',
          cursor: 'pointer',
        },
        buttonSkip: {
          color: 'var(--color-muted-text)',
          fontSize: '13px',
          fontWeight: 500,
          cursor: 'pointer',
        },
      }}
    />
  );
}
