'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Search,
  Database,
  Table2,
  ChevronRight,
  Edit3,
  Check,
  X,
  RefreshCw,
  Sparkles,
  User,
  Minus,
  Key,
  AlertCircle,
} from 'lucide-react';
import { useSchemaMetadataHooks, SchemaTableDetail, SchemaColumnDetail } from '@/hooks/api/useSchemaMetadata';
import { useConnectorsHooks } from '@/hooks/api/useConnectors';
import { useAppStore } from '@/store/useAppStore';
import { Skeleton } from '@/components/ui/Skeleton';

type DescSource = 'user' | 'native' | 'empty';

function DescriptionBadge({ source }: { source: DescSource }) {
  if (source === 'user') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-violet-500/15 text-violet-400 border border-violet-500/25">
        <User size={9} /> User Defined
      </span>
    );
  }
  if (source === 'native') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/25">
        <Database size={9} /> DB Native
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/20">
      <Minus size={9} /> No Description
    </span>
  );
}

function getDescSource(desc: string | null, userFlag: boolean): DescSource {
  if (!desc) return 'empty';
  if (userFlag) return 'user';
  return 'native';
}

interface InlineEditorProps {
  value: string | null;
  userFlag: boolean;
  placeholder: string;
  onSave: (value: string | null) => Promise<void>;
  isSaving?: boolean;
}

function InlineEditor({ value, userFlag, placeholder, onSave, isSaving }: InlineEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? '');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const autoResize = useCallback(() => {
    const ta = textareaRef.current;
    if (ta) { ta.style.height = 'auto'; ta.style.height = `${ta.scrollHeight}px`; }
  }, []);

  useEffect(() => {
    if (isEditing) {
      setDraft(value ?? '');
      setTimeout(() => { textareaRef.current?.focus(); autoResize(); }, 50);
    }
  }, [isEditing, value, autoResize]);

  const handleSave = async () => {
    const trimmed = draft.trim();
    await onSave(trimmed === '' ? null : trimmed);
    setIsEditing(false);
  };

  const handleCancel = () => { setDraft(value ?? ''); setIsEditing(false); };

  if (isEditing) {
    return (
      <div className="mt-2 flex flex-col gap-2">
        <textarea
          ref={textareaRef}
          value={draft}
          onChange={(e) => { setDraft(e.target.value); autoResize(); }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') handleCancel();
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSave();
          }}
          placeholder={placeholder}
          rows={3}
          className="w-full px-3 py-2.5 rounded-lg bg-secondary-bg border border-accent-primary/40 text-primary-text text-sm resize-none outline-none focus:border-accent-primary transition-all placeholder:text-muted-text"
          style={{ minHeight: 72 }}
        />
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-accent-primary text-white hover:bg-accent-primary-hover transition-all disabled:opacity-50 shadow-[0_0_12px_rgba(91,106,248,0.4)]"
          >
            {isSaving ? <RefreshCw size={12} className="animate-spin" /> : <Check size={12} />}
            {isSaving ? 'Saving...' : 'Save (Ctrl+Enter)'}
          </button>
          <button
            onClick={handleCancel}
            className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-secondary-text hover:text-primary-text hover:bg-tertiary-bg transition-all"
          >
            <X size={12} /> Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-1.5 group/desc flex items-start gap-2">
      <div className="flex-1 min-w-0">
        {value ? (
          <p className="text-sm text-secondary-text leading-relaxed">{value}</p>
        ) : (
          <p className="text-sm text-muted-text italic">{placeholder}</p>
        )}
      </div>
      <div className="flex items-center gap-1.5 opacity-0 group-hover/desc:opacity-100 transition-opacity shrink-0 mt-0.5">
        <button
          onClick={() => setIsEditing(true)}
          title="Edit description"
          className="cursor-pointer p-1.5 rounded-md text-muted-text hover:text-accent-primary hover:bg-accent-primary/10 transition-all"
        >
          <Edit3 size={13} />
        </button>
        {userFlag && (
          <button
            onClick={() => onSave(null)}
            title="Clear user override - next sync can restore from DB"
            className="cursor-pointer p-1.5 rounded-md text-muted-text hover:text-accent-danger hover:bg-accent-danger/10 transition-all"
          >
            <RefreshCw size={13} />
          </button>
        )}
      </div>
    </div>
  );
}

interface ColumnRowProps {
  column: SchemaColumnDetail;
  tableId: string;
  onUpdateColumn: (tableId: string, columnId: string, desc: string | null) => Promise<void>;
  isSaving: boolean;
}

function ColumnRow({ column, tableId, onUpdateColumn, isSaving }: ColumnRowProps) {
  const source = getDescSource(column.column_description, column.user_column_description);
  return (
    <div className="px-4 py-3 border-b border-border-color last:border-b-0 hover:bg-tertiary-bg/50 transition-colors">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0 w-6 h-6 rounded-md bg-accent-primary/10 flex items-center justify-center">
          {column.is_primary_key ? (
            <Key size={11} className="text-amber-400" />
          ) : (
            <span className="text-[9px] font-bold text-accent-primary/60">{column.data_type.slice(0, 2).toUpperCase()}</span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-semibold text-primary-text">{column.column_name}</span>
            <span className="text-[11px] font-mono text-muted-text bg-tertiary-bg px-1.5 py-0.5 rounded">{column.data_type}</span>
            {column.is_primary_key && (
              <span className="text-[10px] font-semibold text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">PK</span>
            )}
            {!column.is_nullable && (
              <span className="text-[10px] font-semibold text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">NOT NULL</span>
            )}
            <DescriptionBadge source={source} />
          </div>
          <InlineEditor
            value={column.column_description}
            userFlag={column.user_column_description}
            placeholder="Add a description for this column..."
            isSaving={isSaving}
            onSave={(desc) => onUpdateColumn(tableId, column.id, desc)}
          />
        </div>
      </div>
    </div>
  );
}

interface TableCardProps {
  table: SchemaTableDetail;
  connectorId: string;
  onUpdateTable: (tableId: string, desc: string | null) => Promise<void>;
  onUpdateColumn: (tableId: string, columnId: string, desc: string | null) => Promise<void>;
  savingTableId: string | null;
  savingColumnId: string | null;
  defaultExpanded?: boolean;
}

function TableCard({ table, connectorId, onUpdateTable, onUpdateColumn, savingTableId, savingColumnId, defaultExpanded = false }: TableCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const source = getDescSource(table.table_description, table.user_table_description);
  const userColCount = table.columns.filter((c) => c.user_column_description).length;
  const emptyDescCount = table.columns.filter((c) => !c.column_description).length;

  return (
    <div className={`bg-card-bg border rounded-xl overflow-hidden transition-all duration-200 ${expanded ? 'border-accent-primary/30 shadow-[0_0_20px_rgba(91,106,248,0.08)]' : 'border-border-color hover:border-border-hover'}`}>
      <button
        id={`table-card-${table.id}`}
        onClick={() => setExpanded((e) => !e)}
        className="cursor-pointer w-full text-left px-5 py-4 flex items-center gap-3 hover:bg-tertiary-bg/40 transition-colors"
      >
        <div className={`transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}>
          <ChevronRight size={16} className="text-muted-text" />
        </div>
        <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center shrink-0">
          <Table2 size={15} className="text-accent-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[15px] font-bold text-primary-text">
              {table.schema_name ? `${table.schema_name}.` : ''}{table.table_name}
            </span>
            <DescriptionBadge source={source} />
            {userColCount > 0 && (
              <span className="text-[10px] font-semibold text-violet-400 bg-violet-500/10 px-1.5 py-0.5 rounded-full border border-violet-500/20">
                {userColCount} custom col{userColCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
          {table.table_description && (
            <p className="mt-0.5 text-xs text-secondary-text truncate max-w-[500px]">{table.table_description}</p>
          )}
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <div className="text-right hidden sm:block">
            <div className="text-xs text-muted-text">{table.columns.length} cols</div>
            {emptyDescCount > 0 && <div className="text-[10px] text-amber-500 mt-0.5">{emptyDescCount} missing</div>}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border-color animate-page-enter">
          <div className="px-5 py-4 border-b border-border-color bg-tertiary-bg/30">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[11px] font-bold text-secondary-text uppercase tracking-wider">Table Description</span>
              <DescriptionBadge source={source} />
            </div>
            <InlineEditor
              value={table.table_description}
              userFlag={table.user_table_description}
              placeholder="Add a description to help the AI understand this table..."
              isSaving={savingTableId === table.id}
              onSave={(desc) => onUpdateTable(table.id, desc)}
            />
          </div>
          <div>
            <div className="px-5 py-2.5 bg-secondary-bg/40">
              <span className="text-[11px] font-bold text-secondary-text uppercase tracking-wider">Columns ({table.columns.length})</span>
            </div>
            {table.columns.length === 0 ? (
              <div className="px-5 py-6 text-center text-sm text-muted-text">No columns found.</div>
            ) : (
              table.columns.map((col) => (
                <ColumnRow
                  key={col.id}
                  column={col}
                  tableId={table.id}
                  isSaving={savingColumnId === col.id}
                  onUpdateColumn={onUpdateColumn}
                />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatsBar({ tables }: { tables: SchemaTableDetail[] }) {
  const totalCols = tables.reduce((s, t) => s + t.columns.length, 0);
  const tablesWithDesc = tables.filter((t) => !!t.table_description).length;
  const userDefinedTables = tables.filter((t) => t.user_table_description).length;
  const colsWithDesc = tables.flatMap((t) => t.columns).filter((c) => !!c.column_description).length;
  const coverage = totalCols > 0 ? Math.round((colsWithDesc / totalCols) * 100) : 0;
  const stats = [
    { label: 'Tables', value: String(tables.length), icon: Table2, color: 'text-accent-primary' },
    { label: 'Table Desc Coverage', value: `${tablesWithDesc}/${tables.length}`, icon: Database, color: 'text-accent-success' },
    { label: 'Column Coverage', value: `${coverage}%`, icon: Sparkles, color: 'text-amber-400' },
    { label: 'User Overrides', value: String(userDefinedTables), icon: User, color: 'text-violet-400' },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {stats.map(({ label, value, icon: Icon, color }) => (
        <div key={label} className="bg-card-bg border border-border-color rounded-xl px-4 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
            <Icon size={15} className={color} />
          </div>
          <div>
            <div className="text-[18px] font-bold text-primary-text leading-none">{value}</div>
            <div className="text-[11px] text-muted-text mt-0.5">{label}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function MetadataPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const connectorId = searchParams.get('id') as string;
  const { activeOrganizationId } = useAppStore();

  const { useSchemaTablesDetailedQuery, useUpdateTableDescriptionMutation, useUpdateColumnDescriptionMutation } = useSchemaMetadataHooks();
  const { useConnectorsQuery } = useConnectorsHooks();
  const { data: connectors = [] } = useConnectorsQuery(activeOrganizationId);
  const connector = (connectors as any[]).find((c: any) => c.id === connectorId);

  const { data: tables = [], isLoading, isError, refetch } = useSchemaTablesDetailedQuery(connectorId);
  const updateTableDesc = useUpdateTableDescriptionMutation(connectorId);
  const updateColumnDesc = useUpdateColumnDescriptionMutation(connectorId);

  const [savingTableId, setSavingTableId] = useState<string | null>(null);
  const [savingColumnId, setSavingColumnId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'missing' | 'user' | 'native'>('all');

  const allTables = tables as SchemaTableDetail[];

  const filteredTables = allTables.filter((t) => {
    const q = search.toLowerCase();
    const matchesSearch = !q ||
      t.table_name.toLowerCase().includes(q) ||
      (t.schema_name ?? '').toLowerCase().includes(q) ||
      (t.table_description ?? '').toLowerCase().includes(q) ||
      t.columns.some((c) => c.column_name.toLowerCase().includes(q) || (c.column_description ?? '').toLowerCase().includes(q));
    if (!matchesSearch) return false;
    if (filter === 'missing') return !t.table_description || t.columns.some((c) => !c.column_description);
    if (filter === 'user') return t.user_table_description || t.columns.some((c) => c.user_column_description);
    if (filter === 'native') return !t.user_table_description && !!t.table_description;
    return true;
  });

  const handleUpdateTable = async (tableId: string, desc: string | null) => {
    setSavingTableId(tableId);
    try { await updateTableDesc.mutateAsync({ tableId, description: desc }); }
    finally { setSavingTableId(null); }
  };

  const handleUpdateColumn = async (tableId: string, columnId: string, desc: string | null) => {
    setSavingColumnId(columnId);
    try { await updateColumnDesc.mutateAsync({ tableId, columnId, description: desc }); }
    finally { setSavingColumnId(null); }
  };

  if (!connectorId) {
    return (
      <div className="p-8 text-center">
        <AlertCircle className="w-8 h-8 text-accent-danger mx-auto mb-3" />
        <p className="text-secondary-text">No connector ID provided.</p>
        <button onClick={() => router.push('/connector')} className="mt-4 text-accent-primary hover:underline">Go back</button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 animate-page-enter">
      <div className="mb-6">
        <button
          onClick={() => router.push('/connector')}
          className="cursor-pointer inline-flex items-center gap-1.5 text-xs font-medium text-muted-text hover:text-primary-text transition-colors mb-3"
        >
          <ArrowLeft size={14} /> Back to Connectors
        </button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-primary-text tracking-tight flex items-center gap-2">
              Schema Metadata
            </h1>
            <p className="mt-1 text-sm text-secondary-text">
              Enrich table and column descriptions for <strong className="text-primary-text font-semibold">{connector?.name || 'this database'}</strong> to improve AI query accuracy.
            </p>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-secondary-bg hover:bg-tertiary-bg text-secondary-text hover:text-primary-text border border-border-color transition-all disabled:opacity-50"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-6">
          <Skeleton className="h-[72px] w-full rounded-xl" />
          <div className="space-y-4">
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
          </div>
        </div>
      ) : isError ? (
        <div className="rounded-xl border border-accent-danger/20 bg-accent-danger/5 p-6 text-center">
          <AlertCircle size={24} className="mx-auto text-accent-danger mb-2" />
          <p className="text-sm text-accent-danger font-medium">Failed to load schema metadata.</p>
        </div>
      ) : allTables.length === 0 ? (
        <div className="rounded-xl border border-border-color bg-card-bg p-12 text-center">
          <Database size={32} className="mx-auto text-muted-text mb-3" />
          <h3 className="text-sm font-semibold text-primary-text">No tables found</h3>
          <p className="text-sm text-secondary-text mt-1 max-w-sm mx-auto">
            This database connector doesn't have any tables yet. Try syncing the connector first.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <StatsBar tables={allTables} />

          <div className="bg-card-bg border border-border-color rounded-xl p-3 flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1 relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-text" />
              <input
                type="text"
                placeholder="Search tables or columns..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-lg bg-secondary-bg border border-transparent focus:border-accent-primary/40 focus:bg-card-bg text-sm text-primary-text outline-none transition-all placeholder:text-muted-text"
              />
            </div>
            <div className="h-8 w-px bg-border-color hidden sm:block" />
            <div className="flex bg-secondary-bg p-1 rounded-lg shrink-0">
              <button
                onClick={() => setFilter('all')}
                className={`cursor-pointer px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${filter === 'all' ? 'bg-card-bg text-primary-text shadow-sm border border-border-color' : 'text-secondary-text hover:text-primary-text border border-transparent'}`}
              >All</button>
              <button
                onClick={() => setFilter('missing')}
                className={`cursor-pointer px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${filter === 'missing' ? 'bg-card-bg text-primary-text shadow-sm border border-border-color' : 'text-secondary-text hover:text-primary-text border border-transparent'}`}
              >Missing</button>
              <button
                onClick={() => setFilter('user')}
                className={`cursor-pointer px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${filter === 'user' ? 'bg-card-bg text-primary-text shadow-sm border border-border-color' : 'text-secondary-text hover:text-primary-text border border-transparent'}`}
              >User Overrides</button>
            </div>
          </div>

          <div className="space-y-3">
            {filteredTables.map((table) => (
              <TableCard
                key={table.id}
                connectorId={connectorId}
                table={table}
                onUpdateTable={handleUpdateTable}
                onUpdateColumn={handleUpdateColumn}
                savingTableId={savingTableId}
                savingColumnId={savingColumnId}
                defaultExpanded={search.length > 0}
              />
            ))}
            {filteredTables.length === 0 && (
              <div className="text-center py-8 text-sm text-muted-text">
                No tables match your search or filter.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
