import { create } from 'zustand';
import { Calendar, Fingerprint, HardDrive, Sparkles, Database, Bot, Mail } from 'lucide-react';

export interface Connector {
  id: string;
  name: string;
  provider: string;
  icon: any; // Using any here to avoid complex React.ElementType imports in store, though normally we'd map string -> icon component in UI layer
  colorBase: string;
  enabled: boolean;
  credentialMapped: boolean;
  credentialId?: string;
}

export interface Credential {
  id: string;
  name: string;
  provider: string;
  status: 'Active' | 'Inactive';
  lastUsed: Date | null;
}

interface IntegrationState {
  connectors: Connector[];
  credentials: Credential[];
  
  // Actions
  addCredential: (cred: Omit<Credential, 'id' | 'status' | 'lastUsed'>) => void;
  deleteCredential: (id: string) => void;
  updateConnector: (id: string, updates: Partial<Connector>) => void;
}

const INITIAL_CONNECTORS: Connector[] = [
  { id: 'google_drive', name: 'Google Drive', provider: 'Google', icon: HardDrive, colorBase: 'blue', enabled: false, credentialMapped: false },
  { id: 'postgres', name: 'PostgreSQL', provider: 'PostgreSQL', icon: Database, colorBase: 'indigo', enabled: false, credentialMapped: false },
];

export const useIntegrationStore = create<IntegrationState>((set) => ({
  connectors: INITIAL_CONNECTORS,
  credentials: [],

  addCredential: (cred) => set((state) => ({
    credentials: [
      ...state.credentials,
      {
        ...cred,
        id: Math.random().toString(36).substring(7),
        status: 'Active',
        lastUsed: new Date(),
      }
    ]
  })),

  deleteCredential: (id) => set((state) => ({
    credentials: state.credentials.filter(c => c.id !== id),
    // Also unmap any connectors using this credential
    connectors: state.connectors.map(conn => 
      conn.credentialId === id 
        ? { ...conn, credentialMapped: false, credentialId: undefined, enabled: false }
        : conn
    )
  })),

  updateConnector: (id, updates) => set((state) => ({
    connectors: state.connectors.map(c => 
      c.id === id ? { ...c, ...updates } : c
    )
  })),
}));
