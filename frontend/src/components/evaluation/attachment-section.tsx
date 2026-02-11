"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  Loader2,
  Upload,
  Download,
  Trash2,
  Eye,
  Image as ImageIcon,
  Paperclip,
  FileText,
  FileCode,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { attachmentsApi } from "@/services/api";
import { getAccessToken } from "@/lib/api-client";
import { toast } from "sonner";
import type { Attachment } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const MAX_UPLOAD_SIZE = 16 * 1024 * 1024; // 16 Mo

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export function isImageMime(mime: string): boolean {
  return mime.startsWith("image/");
}

export function isTextMime(mime: string): boolean {
  return (
    mime.startsWith("text/") ||
    mime === "application/json" ||
    mime === "application/xml" ||
    mime === "application/x-yaml"
  );
}

export function AttachmentSection({
  controlResultId,
  attachments,
  onChanged,
  readOnly = false,
}: {
  controlResultId: number;
  attachments: Attachment[];
  onChanged: () => void;
  readOnly?: boolean;
}) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [previewImage, setPreviewImage] = useState<{ att: Attachment; blobUrl: string } | null>(null);
  const [textPreview, setTextPreview] = useState<{
    att: Attachment;
    content: string;
  } | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [thumbUrls, setThumbUrls] = useState<Record<number, string>>({});
  const blobUrlsRef = useRef<string[]>([]);

  const fetchBlob = useCallback(async (url: string) => {
    const token = getAccessToken() || "";
    const resp = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blobUrl = URL.createObjectURL(await resp.blob());
    blobUrlsRef.current.push(blobUrl);
    return blobUrl;
  }, []);

  useEffect(() => {
    const imageAtts = attachments.filter((a) => isImageMime(a.mime_type));
    imageAtts.forEach(async (att) => {
      if (thumbUrls[att.id]) return;
      try {
        const url = await fetchBlob(`${API_BASE}/attachments/${att.id}/preview`);
        setThumbUrls((prev) => ({ ...prev, [att.id]: url }));
      } catch {
        /* thumbnail non critique */
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attachments, fetchBlob]);

  // Cleanup all blob URLs on unmount
  useEffect(() => {
    return () => {
      blobUrlsRef.current.forEach(URL.revokeObjectURL);
    };
  }, []);

  const handleFiles = async (files: FileList | File[]) => {
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        if (file.size > MAX_UPLOAD_SIZE) {
          toast.error(`${file.name} dépasse la limite de 16 Mo`);
          continue;
        }
        await attachmentsApi.upload(controlResultId, file);
      }
      onChanged();
      toast.success("Fichier(s) uploadé(s)");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erreur lors de l'upload";
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);

  const handleDelete = async (id: number) => {
    try {
      await attachmentsApi.delete(id);
      onChanged();
      toast.success("Pièce jointe supprimée");
    } catch {
      toast.error("Erreur lors de la suppression");
    }
    setDeleteTarget(null);
  };

  const handlePreviewImage = async (att: Attachment) => {
    setLoadingPreview(true);
    try {
      const blobUrl = await fetchBlob(`${API_BASE}/attachments/${att.id}/preview`);
      setPreviewImage({ att, blobUrl });
    } catch {
      toast.error("Impossible de charger l'image");
    } finally {
      setLoadingPreview(false);
    }
  };

  const handlePreviewText = async (att: Attachment) => {
    setLoadingPreview(true);
    try {
      const resp = await fetch(`${API_BASE}/attachments/${att.id}/preview`, {
        headers: { Authorization: `Bearer ${getAccessToken() || ""}` },
      });
      const text = await resp.text();
      setTextPreview({ att, content: text });
    } catch {
      toast.error("Impossible de charger le contenu");
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleDownload = async (att: Attachment) => {
    try {
      const resp = await fetch(`${API_BASE}/attachments/${att.id}/download`, {
        headers: { Authorization: `Bearer ${getAccessToken() || ""}` },
      });
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = att.original_filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Erreur lors du téléchargement");
    }
  };

  return (
    <div className="space-y-3">
      <Label className="text-xs font-medium flex items-center gap-1.5">
        <Paperclip className="h-3.5 w-3.5" />
        Pièces jointes ({attachments.length})
      </Label>

      {/* Drop zone */}
      {!readOnly && (
        <div
          className={`relative border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
            dragOver
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-muted-foreground/50"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          {uploading ? (
            <div className="flex items-center justify-center gap-2 py-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">Upload en cours…</span>
            </div>
          ) : (
            <>
              <Upload className="h-6 w-6 mx-auto text-muted-foreground/50 mb-1" />
              <p className="text-xs text-muted-foreground">
                Glissez-déposez des fichiers ici ou{" "}
                <label className="text-primary cursor-pointer hover:underline">
                  parcourir
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    accept=".png,.jpg,.jpeg,.gif,.bmp,.webp,.svg,.pdf,.doc,.docx,.xls,.xlsx,.txt,.log,.conf,.cfg,.ini,.yaml,.yml,.json,.xml,.csv,.md,.zip,.gz,.tar,.pcap,.cap"
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        handleFiles(e.target.files);
                        e.target.value = "";
                      }
                    }}
                  />
                </label>
              </p>
              <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                Images, PDF, configs, logs, captures réseau (max 16 Mo)
              </p>
            </>
          )}
        </div>
      )}

      {/* Attached files list */}
      {attachments.length > 0 && (
        <div className="space-y-2">
          {attachments.map((att) => (
            <div
              key={att.id}
              className="flex items-center gap-3 p-2 rounded-md border bg-background hover:bg-muted/30 transition-colors group"
            >
              {/* Thumbnail / icon */}
              {isImageMime(att.mime_type) ? (
                <button
                  type="button"
                  className="shrink-0 w-12 h-12 rounded border overflow-hidden bg-muted/50 cursor-pointer"
                  onClick={() => handlePreviewImage(att)}
                >
                  {thumbUrls[att.id] ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={thumbUrls[att.id]}
                      alt={att.original_filename}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <ImageIcon className="h-4 w-4 text-muted-foreground" />
                    </div>
                  )}
                </button>
              ) : (
                <div className="shrink-0 w-12 h-12 rounded border flex items-center justify-center bg-muted/30">
                  {isTextMime(att.mime_type) ? (
                    <FileCode className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <FileText className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
              )}

              {/* File info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{att.original_filename}</p>
                <p className="text-[10px] text-muted-foreground">
                  {formatFileSize(att.file_size)}
                  {att.uploaded_by && ` • ${att.uploaded_by}`}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                {isTextMime(att.mime_type) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => handlePreviewText(att)}
                    disabled={loadingPreview}
                  >
                    <Eye className="h-3.5 w-3.5" />
                  </Button>
                )}
                {isImageMime(att.mime_type) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => handlePreviewImage(att)}
                    disabled={loadingPreview}
                  >
                    <Eye className="h-3.5 w-3.5" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => handleDownload(att)}
                >
                  <Download className="h-3.5 w-3.5" />
                </Button>
                {!readOnly && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 text-red-500 hover:text-red-700"
                    onClick={() => setDeleteTarget(att.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Image preview dialog */}
      <Dialog
        open={!!previewImage}
        onOpenChange={() => {
          if (previewImage) {
            URL.revokeObjectURL(previewImage.blobUrl);
            setPreviewImage(null);
          }
        }}
      >
        <DialogContent className="max-w-4xl max-h-[90vh] p-2 pt-10">
          <DialogTitle className="sr-only">
            {previewImage?.att.original_filename || "Aperçu"}
          </DialogTitle>
          {previewImage && (
            <div className="space-y-2">
              <div className="flex items-center justify-between px-2">
                <p className="text-sm font-medium truncate mr-2">{previewImage.att.original_filename}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={() => handleDownload(previewImage.att)}
                >
                  <Download className="h-3.5 w-3.5 mr-1.5" />
                  Télécharger
                </Button>
              </div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewImage.blobUrl}
                alt={previewImage.att.original_filename}
                className="w-full max-h-[75vh] object-contain rounded"
              />
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Text preview dialog */}
      <Dialog open={!!textPreview} onOpenChange={() => setTextPreview(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] pt-10">
          <DialogTitle className="text-sm font-medium">
            {textPreview?.att.original_filename || "Aperçu"}
          </DialogTitle>
          {textPreview && (
            <div className="space-y-2">
              <div className="flex items-center justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDownload(textPreview.att)}
                >
                  <Download className="h-3.5 w-3.5 mr-1.5" />
                  Télécharger
                </Button>
              </div>
              <pre className="bg-muted rounded-md p-4 text-xs overflow-auto max-h-[65vh] whitespace-pre-wrap font-mono">
                {textPreview.content}
              </pre>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <AlertDialog open={deleteTarget !== null} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer cette pièce jointe ?</AlertDialogTitle>
            <AlertDialogDescription>
              Cette action est irréversible. Le fichier sera supprimé du serveur.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteTarget && handleDelete(deleteTarget)}>
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
