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
} from 'lucide-react';
import toast from 'react-hot-toast';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useAppStore } from '@/store/useAppStore';
import { useDocumentsHooks, DocumentRecord } from '@/hooks/api/useDocuments';
import { Modal } from '@/components/ui/Modal';

const ACCEPTED_TYPES = '.pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls,.pptx,.ppt,.html,.json';

function statusBadge(status: DocumentRecord['status']) {
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

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadingFile, setUploadingFile] = useState<string | null>(null);

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<DocumentRecord | null>(null);

  const documents = listResponse?.data || [];

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

  return (
    <div className="min-h-full p-4 md:p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-gray-200 dark:border-white/10 pb-6">
          <div>
            <h1 className="text-3xl font-semibold text-gray-900 dark:text-white tracking-tight">Documents</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">
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

        {hasHydrated && !activeOrganizationId && (
          <div className="rounded-xl border border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 p-4 text-sm text-amber-800 dark:text-amber-200">
            No organization selected. Choose one in Settings → General before uploading.
          </div>
        )}

        {/* Upload zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition-all ${dragOver
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
          <div className="flex flex-col items-center gap-4">
            {uploadMutation.isPending ? (
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
            ) : (
              <CloudUpload className="w-12 h-12 text-gray-400 dark:text-gray-500" />
            )}
            <div>
              <p className="text-lg font-medium text-gray-900 dark:text-white">
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
            <div className="p-12 flex justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : documents.length === 0 ? (
            <div className="p-12 text-center text-gray-500 dark:text-gray-400 text-sm">
              No documents yet. Upload a file above to get started.
            </div>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-white/5">
              {documents.map((doc) => (
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
                      className="p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

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
    </div>
  );
}
