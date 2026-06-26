'use client';

import React, { useCallback, useRef, useState } from 'react';
import Link from 'next/link';
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  MessageSquare,
  CloudUpload,
  Search,
  Filter
} from 'lucide-react';
import { Input } from '@/components/ui/Input';
import toast from 'react-hot-toast';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useAppStore } from '@/store/useAppStore';
import { useDocumentsHooks, DocumentRecord } from '@/hooks/api/useDocuments';
import { useDriveDocumentsHooks, DriveDocumentRecord } from '@/hooks/api/useDriveDocuments';
import { HardDrive } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Skeleton } from '@/components/ui/Skeleton';

const ACCEPTED_TYPES = '.pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls,.pptx,.ppt,.html,.json';

function statusBadge(status: DocumentRecord['status'] | DriveDocumentRecord['status']) {
  switch (status) {
    case 'indexed':
      return <Badge variant="success">Indexed</Badge>;
    case 'processing':
      return <Badge variant="warning">Processing</Badge>;
    case 'failed':
      return <Badge variant="danger">Failed</Badge>;
    default:
      return <Badge variant="default">Draft</Badge>;
  }
}

export default function DocumentsPage() {
  const { activeOrganizationId, hasHydrated } = useAppStore();
  const { useDocumentsQuery, useUploadDocumentMutation, useDeleteDocumentMutation } = useDocumentsHooks();
  const { data: listResponse, isLoading, refetch } = useDocumentsQuery(activeOrganizationId, {
    pollWhileProcessing: true,
  });
  const uploadMutation = useUploadDocumentMutation();
  const deleteMutation = useDeleteDocumentMutation();

  const { useDriveDocumentsQuery, useDeleteDriveDocumentMutation } = useDriveDocumentsHooks();
  const { data: driveListResponse, isLoading: isLoadingDrive } = useDriveDocumentsQuery(activeOrganizationId, { pollWhileProcessing: true });
  const deleteDriveMutation = useDeleteDriveDocumentMutation();

  const [activeTab, setActiveTab] = useState<'local' | 'drive'>('local');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadingFile, setUploadingFile] = useState<string | null>(null);

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<DocumentRecord | null>(null);

  const [isDeleteDriveModalOpen, setIsDeleteDriveModalOpen] = useState(false);
  const [docToDeleteDrive, setDocToDeleteDrive] = useState<DriveDocumentRecord | null>(null);

  const ITEMS_PER_PAGE = 10;
  const [localPage, setLocalPage] = useState(1);
  const [drivePage, setDrivePage] = useState(1);

  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  // Reset page when search or filter changes
  React.useEffect(() => {
    setLocalPage(1);
    setDrivePage(1);
  }, [searchQuery, filterStatus]);

  const documents = (listResponse?.data || []).filter((d: any) => {
    const search = searchQuery.toLowerCase();
    const matchesSearch = d.title?.toLowerCase().includes(search) || d.reference_id?.toLowerCase().includes(search);
    const matchesType = filterStatus === 'all' || d.status === filterStatus;
    return matchesSearch && matchesType;
  });

  const driveDocuments = (driveListResponse?.data || []).filter((d: any) => {
    const search = searchQuery.toLowerCase();
    const matchesSearch = d.title?.toLowerCase().includes(search) || d.file_id?.toLowerCase().includes(search);
    const matchesType = filterStatus === 'all' || d.status === filterStatus;
    return matchesSearch && matchesType;
  });

  const paginatedDocuments = documents.slice((localPage - 1) * ITEMS_PER_PAGE, localPage * ITEMS_PER_PAGE);
  const totalLocalPages = Math.max(1, Math.ceil(documents.length / ITEMS_PER_PAGE));

  const paginatedDriveDocuments = driveDocuments.slice((drivePage - 1) * ITEMS_PER_PAGE, drivePage * ITEMS_PER_PAGE);
  const totalDrivePages = Math.max(1, Math.ceil(driveDocuments.length / ITEMS_PER_PAGE));

  const handleUpload = useCallback(
    async (file: File) => {
      if (!activeOrganizationId) {
        toast.error('Select an organization first (Settings → General).');
        return;
      }

      setUploadingFile(file.name);
      try {
        const result = await uploadMutation.mutateAsync({
          file,
          organizationId: activeOrganizationId,
          title: file.name,
        });

        if (result.data.status === 'indexed') {
          toast.success(`"${file.name}" indexed (${result.data.chunk_count ?? 0} chunks)`);
        } else if (result.data.status === 'failed') {
          toast.error(result.data.processing_error || 'Indexing failed');
        } else {
          toast.success(`"${file.name}" uploaded — indexing in progress`);
        }
        refetch();
      } catch (err: any) {
        const msg = err?.response?.data?.message || err?.message || 'Upload failed';
        toast.error(msg);
      } finally {
        setUploadingFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    },
    [activeOrganizationId, uploadMutation, refetch]
  );

  const onFilesSelected = (files: FileList | null) => {
    if (!files?.length) return;
    Array.from(files).forEach((file) => handleUpload(file));
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    onFilesSelected(e.dataTransfer.files);
  };

  const handleDeleteClick = (doc: DocumentRecord) => {
    setDocToDelete(doc);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!activeOrganizationId || !docToDelete) return;
    try {
      await deleteMutation.mutateAsync({ documentId: docToDelete.id, organizationId: activeOrganizationId });
      toast.success('Document deleted');
      setIsDeleteModalOpen(false);
      setDocToDelete(null);
    } catch {
      toast.error('Failed to delete document');
    }
  };

  const handleDeleteDriveClick = (doc: DriveDocumentRecord) => {
    setDocToDeleteDrive(doc);
    setIsDeleteDriveModalOpen(true);
  };

  const confirmDeleteDrive = async () => {
    if (!activeOrganizationId || !docToDeleteDrive) return;
    try {
      await deleteDriveMutation.mutateAsync({ documentId: docToDeleteDrive.id, organizationId: activeOrganizationId });
      toast.success('Google Drive Document deleted');
      setIsDeleteDriveModalOpen(false);
      setDocToDeleteDrive(null);
    } catch {
      toast.error('Failed to delete Google Drive document');
    }
  };

  return (
    <div className="flex flex-col gap-8 h-full">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="m-0 text-2xl font-bold text-primary-text tracking-tight">Documents</h1>
            <p className="m-0 mt-1 text-sm text-secondary-text">
              Upload files to index them for RAG. Chat with an assistant that has{' '}
              <code className="text-xs bg-gray-100 dark:bg-white/10 px-1 rounded">rag_search</code> enabled.
            </p>
          </div>
          <Link href="/chat">
            <Button variant="primary" className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Go to Chat
            </Button>
          </Link>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col sm:flex-row items-center gap-4 bg-secondary-bg p-2 rounded-xl border border-border-color">
          <div className="flex-1 w-full relative">
            <Input
              placeholder="Search documents by title or ID..."
              icon={<Search size={18} />}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-transparent border-none shadow-none focus:ring-0"
            />
          </div>
          <div className="h-8 w-px bg-border-color hidden sm:block" />
          <div className="flex items-center gap-2 pr-2 w-full sm:w-auto">
            <div className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-secondary-text">
              <Filter size={16} />
              Status
            </div>
            <div className="flex bg-tertiary-bg p-1 rounded-lg">
              <button onClick={() => setFilterStatus('all')} className={`cursor-pointer border-none px-3 py-1.5 text-xs font-medium transition-all rounded-md ${filterStatus === 'all' ? 'bg-card-bg shadow-sm text-primary-text' : 'text-secondary-text hover:text-primary-text bg-transparent'}`}>All</button>
              <button onClick={() => setFilterStatus('indexed')} className={`cursor-pointer border-none px-3 py-1.5 text-xs font-medium transition-all rounded-md ${filterStatus === 'indexed' ? 'bg-card-bg shadow-sm text-primary-text' : 'text-secondary-text hover:text-primary-text bg-transparent'}`}>Indexed</button>
              <button onClick={() => setFilterStatus('failed')} className={`cursor-pointer border-none px-3 py-1.5 text-xs font-medium transition-all rounded-md ${filterStatus === 'failed' ? 'bg-card-bg shadow-sm text-primary-text' : 'text-secondary-text hover:text-primary-text bg-transparent'}`}>Failed</button>
            </div>
          </div>
        </div>

        {hasHydrated && !activeOrganizationId && (
          <div className="rounded-xl border border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 p-4 text-sm text-amber-800 dark:text-amber-200">
            No organization selected. Choose one in Settings → General before viewing documents.
          </div>
        )}

        <div className="flex items-center gap-2 mt-4 mb-6">
          <button
            onClick={() => setActiveTab('local')}
            className={`px-6 py-2.5 rounded-full font-medium text-sm transition-all duration-300 cursor-pointer ${activeTab === 'local'
                ? 'bg-black dark:bg-white text-white dark:text-gray-900 shadow-xl shadow-black/10 dark:shadow-white/10 scale-105'
                : 'bg-black/5 dark:bg-white/5 text-gray-600 dark:text-gray-400 hover:bg-black/10 dark:hover:bg-white/10'
              }`}
          >
            Local Files
          </button>
          <button
            onClick={() => setActiveTab('drive')}
            className={`px-6 py-2.5 rounded-full font-medium text-sm flex items-center gap-2 transition-all duration-300 cursor-pointer ${activeTab === 'drive'
                ? 'bg-[#4285F4] text-white shadow-xl shadow-blue-500/20 scale-105'
                : 'bg-[#4285F4]/10 text-[#4285F4] hover:bg-[#4285F4]/20'
              }`}
          >
            <HardDrive className="w-4 h-4" /> Google Drive
          </button>
        </div>

        {activeTab === 'local' ? (
          <>
            {/* Upload zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative cursor-pointer rounded-2xl border-2 border-dashed py-8 px-12 text-center transition-all ${dragOver
                ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-500/10'
                : 'border-gray-300 dark:border-white/20 hover:border-blue-400 dark:hover:border-blue-500/50 hover:bg-gray-50 dark:hover:bg-white/5'
                }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept={ACCEPTED_TYPES}
                multiple
                onChange={(e) => onFilesSelected(e.target.files)}
              />
              <div className="flex flex-col items-center gap-3">
                {uploadMutation.isPending ? (
                  <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
                ) : (
                  <CloudUpload className="w-10 h-10 text-gray-400 dark:text-gray-500" />
                )}
                <div>
                  <p className="text-base font-medium text-gray-900 dark:text-white">
                    {uploadMutation.isPending
                      ? `Uploading ${uploadingFile}…`
                      : 'Drop files here or click to upload'}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    PDF, Word, Excel, PowerPoint, CSV, TXT, HTML, JSON — max 50 MB
                  </p>
                </div>
              </div>
            </div>

            {/* Document list */}
            <div className="rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden">
              <div className="p-5 border-b border-gray-100 dark:border-white/5 flex items-center justify-between">
                <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-gray-400" />
                  Uploaded Documents
                </h2>
                <span className="text-xs text-gray-500">{documents.length} total</span>
              </div>

              {isLoading ? (
                <div className="flex flex-col">
                  {[1, 2, 3, 4, 5].map(i => (
                    <div key={i} className="flex items-center justify-between gap-4 px-5 py-4 border-b border-gray-100 dark:border-white/5 last:border-0">
                      <div className="flex items-center gap-3">
                        <Skeleton className="w-10 h-10 rounded-lg shrink-0" />
                        <div className="flex flex-col gap-1.5">
                          <Skeleton className="h-4 w-48" />
                          <Skeleton className="h-3 w-32" />
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Skeleton className="w-16 h-6 rounded-full" />
                        <Skeleton className="w-8 h-8 rounded-lg" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : documents.length === 0 ? (
                <div className="p-12 text-center text-gray-500 dark:text-gray-400 text-sm">
                  No documents yet. Upload a file above to get started.
                </div>
              ) : (
                <>
                  <ul className="divide-y divide-gray-100 dark:divide-white/5">
                    {paginatedDocuments.map((doc) => (
                      <li
                        key={doc.id}
                        className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center shrink-0">
                            {doc.status === 'indexed' ? (
                              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                            ) : doc.status === 'failed' ? (
                              <AlertCircle className="w-5 h-5 text-red-500" />
                            ) : (
                              <Upload className="w-5 h-5 text-blue-500" />
                            )}
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium text-gray-900 dark:text-white truncate">
                              {doc.title || doc.reference_id}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {doc.chunk_count} chunks · {new Date(doc.created_at).toLocaleString()}
                              {doc.processing_error && (
                                <span className="text-red-500 ml-2">{doc.processing_error}</span>
                              )}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          {statusBadge(doc.status)}
                          <button
                            onClick={() => handleDeleteClick(doc)}
                            disabled={deleteMutation.isPending}
                            className="cursor-pointer p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors disabled:cursor-not-allowed"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                  {totalLocalPages > 1 && (
                    <div className="p-4 border-t border-gray-100 dark:border-white/5 flex items-center justify-between bg-gray-50/50 dark:bg-white/[0.02]">
                      <Button variant="secondary" size="sm" onClick={() => setLocalPage(p => Math.max(1, p - 1))} disabled={localPage === 1}>Previous</Button>
                      <span className="text-xs text-gray-500">Page {localPage} of {totalLocalPages}</span>
                      <Button variant="secondary" size="sm" onClick={() => setLocalPage(p => Math.min(totalLocalPages, p + 1))} disabled={localPage === totalLocalPages}>Next</Button>
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        ) : (
          <div className="rounded-xl bg-white dark:bg-[#111113] border border-gray-200 dark:border-white/10 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="p-5 border-b border-gray-100 dark:border-white/5 flex items-center justify-between bg-blue-50/30 dark:bg-blue-500/5">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-[#4285F4]" />
                Synced Google Drive Files
              </h2>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 px-3 py-1 bg-green-100 dark:bg-green-500/10 text-green-700 dark:text-green-400 rounded-full text-xs font-medium">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                  Auto-Syncing
                </div>
                <span className="text-xs text-gray-500">{driveDocuments.length} total</span>
              </div>
            </div>

            {isLoadingDrive ? (
                <div className="flex flex-col">
                  {[1, 2, 3, 4, 5].map(i => (
                    <div key={i} className="flex items-center justify-between gap-4 px-5 py-4 border-b border-gray-100 dark:border-white/5 last:border-0">
                      <div className="flex items-center gap-3">
                        <Skeleton className="w-10 h-10 rounded-lg shrink-0" />
                        <div className="flex flex-col gap-1.5">
                          <Skeleton className="h-4 w-48" />
                          <Skeleton className="h-3 w-32" />
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Skeleton className="w-16 h-6 rounded-full" />
                        <Skeleton className="w-8 h-8 rounded-lg" />
                      </div>
                    </div>
                  ))}
                </div>
            ) : driveDocuments.length === 0 ? (
              <div className="p-12 text-center">
                <HardDrive className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400 text-sm">
                  No Google Drive documents synced yet.
                </p>
                <p className="text-xs text-gray-400 mt-2 max-w-sm mx-auto">
                  Ensure the Google Drive Connector is enabled and a valid Service Account credential is provided. The background poller will automatically sync files here.
                </p>
              </div>
            ) : (
              <>
                <ul className="divide-y divide-gray-100 dark:divide-white/5">
                  {paginatedDriveDocuments.map((doc) => (
                    <li
                      key={doc.id}
                      className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-lg bg-[#4285F4]/10 flex items-center justify-center shrink-0">
                          {doc.status === 'indexed' ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                          ) : doc.status === 'failed' ? (
                            <AlertCircle className="w-5 h-5 text-red-500" />
                          ) : (
                            <Loader2 className="w-5 h-5 text-[#4285F4] animate-spin" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <a
                            href={doc.web_view_link}
                            target="_blank"
                            rel="noreferrer"
                            className="font-medium text-[#4285F4] hover:underline truncate block"
                          >
                            {doc.title}
                          </a>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {doc.mime_type} · {new Date(doc.updated_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        {statusBadge(doc.status)}
                        <button
                          onClick={() => handleDeleteDriveClick(doc)}
                          disabled={deleteDriveMutation.isPending}
                          className="cursor-pointer p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors disabled:cursor-not-allowed"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
                {totalDrivePages > 1 && (
                  <div className="p-4 border-t border-gray-100 dark:border-white/5 flex items-center justify-between bg-gray-50/50 dark:bg-white/[0.02]">
                    <Button variant="secondary" size="sm" onClick={() => setDrivePage(p => Math.max(1, p - 1))} disabled={drivePage === 1}>Previous</Button>
                    <span className="text-xs text-gray-500">Page {drivePage} of {totalDrivePages}</span>
                    <Button variant="secondary" size="sm" onClick={() => setDrivePage(p => Math.min(totalDrivePages, p + 1))} disabled={drivePage === totalDrivePages}>Next</Button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete Document"
        description={`Are you sure you want to delete "${docToDelete?.title || docToDelete?.reference_id || 'this document'}"? This action cannot be undone.`}
        maxWidth="max-w-md"
      >
        <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-border-color">
          <Button variant="ghost" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
          <Button variant="primary" className="bg-accent-danger hover:bg-accent-danger/90 text-white border-transparent" onClick={confirmDelete} disabled={deleteMutation.isPending}>
            {deleteMutation.isPending ? 'Deleting...' : 'Yes, Delete Document'}
          </Button>
        </div>
      </Modal>

      <Modal
        isOpen={isDeleteDriveModalOpen}
        onClose={() => setIsDeleteDriveModalOpen(false)}
        title="Delete Google Drive Document"
        description={`Are you sure you want to delete "${docToDeleteDrive?.title || 'this document'}"? This action cannot be undone.`}
        maxWidth="max-w-md"
      >
        <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-border-color">
          <Button variant="ghost" onClick={() => setIsDeleteDriveModalOpen(false)}>Cancel</Button>
          <Button variant="primary" className="bg-accent-danger hover:bg-accent-danger/90 text-white border-transparent" onClick={confirmDeleteDrive} disabled={deleteDriveMutation.isPending}>
            {deleteDriveMutation.isPending ? 'Deleting...' : 'Yes, Delete Document'}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
