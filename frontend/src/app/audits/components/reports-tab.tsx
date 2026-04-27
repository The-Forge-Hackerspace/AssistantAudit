"use client";

import { useCallback, useEffect, useState } from "react";
import { FileDown, FileText, Loader2, Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { reportsApi } from "@/services/api";
import type { AuditReport, AuditReportStatus } from "@/types";

interface ReportsTabProps {
  auditId: number;
}

const STATUS_LABEL: Record<AuditReportStatus, string> = {
  draft: "Brouillon",
  generating: "Génération…",
  ready: "Prêt",
  error: "Erreur",
};

const STATUS_VARIANT: Record<AuditReportStatus, "secondary" | "default" | "destructive"> = {
  draft: "secondary",
  generating: "secondary",
  ready: "default",
  error: "destructive",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  const norm = dateStr.endsWith("Z") || dateStr.includes("+") ? dateStr : dateStr + "Z";
  const d = new Date(norm);
  return d.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ReportsTab({ auditId }: ReportsTabProps) {
  const [reports, setReports] = useState<AuditReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AuditReport | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await reportsApi.list(auditId);
      setReports(data.sort((a, b) => (a.created_at < b.created_at ? 1 : -1)));
    } catch {
      toast.error("Impossible de charger les rapports.");
    } finally {
      setLoading(false);
    }
  }, [auditId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const report = await reportsApi.create({ audit_id: auditId, template_name: "complete" });
      toast.success("Rapport créé. Cliquez sur 'Générer PDF' pour produire le document.");
      setReports((prev) => [report, ...prev]);
    } catch {
      toast.error("Erreur lors de la création du rapport.");
    } finally {
      setCreating(false);
    }
  };

  const handleGenerate = async (report: AuditReport) => {
    setGeneratingId(report.id);
    try {
      const updated = await reportsApi.generate(report.id);
      toast.success("Rapport généré.");
      setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch {
      toast.error("Erreur lors de la génération du rapport.");
      load();
    } finally {
      setGeneratingId(null);
    }
  };

  const handleDownload = async (report: AuditReport) => {
    setDownloadingId(report.id);
    try {
      const blob = await reportsApi.download(report.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `rapport_audit_${report.audit_id}_${report.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Erreur lors du téléchargement.");
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await reportsApi.delete(deleteTarget.id);
      toast.success("Rapport supprimé.");
      setReports((prev) => prev.filter((r) => r.id !== deleteTarget.id));
    } catch {
      toast.error("Erreur lors de la suppression.");
    } finally {
      setDeleteTarget(null);
    }
  };

  return (
    <Card>
      <CardContent className="pt-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold">Rapports d&apos;audit</h3>
            <p className="text-sm text-muted-foreground">
              Génération du rapport PDF complet pour cet audit (page de garde, synthèse exécutive,
              résultats détaillés, recommandations).
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={load} disabled={loading}>
              <RefreshCw className={loading ? "animate-spin" : ""} />
            </Button>
            <Button size="sm" onClick={handleCreate} disabled={creating}>
              {creating ? <Loader2 className="animate-spin" /> : <Plus />}
              Créer un rapport
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          </div>
        ) : reports.length === 0 ? (
          <div className="rounded-lg border border-dashed p-8 text-center">
            <FileText className="mx-auto mb-2 size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Aucun rapport pour cet audit. Cliquez sur « Créer un rapport » pour commencer.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Réf.</th>
                  <th className="px-3 py-2 text-left font-medium">Statut</th>
                  <th className="px-3 py-2 text-left font-medium">Créé le</th>
                  <th className="px-3 py-2 text-left font-medium">Généré le</th>
                  <th className="px-3 py-2 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id} className="border-t">
                    <td className="px-3 py-2 font-mono">RPT-{r.id}</td>
                    <td className="px-3 py-2">
                      <Badge variant={STATUS_VARIANT[r.status]}>{STATUS_LABEL[r.status]}</Badge>
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">{formatDate(r.created_at)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{formatDate(r.generated_at)}</td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleGenerate(r)}
                          disabled={generatingId === r.id || r.status === "generating"}
                          title={r.status === "ready" ? "Régénérer" : "Générer PDF"}
                        >
                          {generatingId === r.id ? (
                            <Loader2 className="animate-spin" />
                          ) : (
                            <RefreshCw />
                          )}
                          {r.status === "ready" ? "Régénérer" : "Générer"}
                        </Button>
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => handleDownload(r)}
                          disabled={r.status !== "ready" || downloadingId === r.id}
                          title="Télécharger le PDF"
                        >
                          {downloadingId === r.id ? (
                            <Loader2 className="animate-spin" />
                          ) : (
                            <FileDown />
                          )}
                          PDF
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteTarget(r)}
                          title="Supprimer le rapport"
                        >
                          <Trash2 />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="text-xs text-muted-foreground italic">
          Une interface complète d&apos;édition des sections (toggles, contenu personnalisé, logos)
          arrivera prochainement (TOS-68).
        </p>
      </CardContent>

      <AlertDialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer ce rapport ?</AlertDialogTitle>
            <AlertDialogDescription>
              Cette action est irréversible. Le PDF généré sera également supprimé du disque.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Supprimer</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
