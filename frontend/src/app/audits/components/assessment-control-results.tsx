"use client";

import { useState } from "react";
import {
  Pencil,
  Loader2,
  CheckCircle,
  Zap,
  AlertCircle,
  CircleDot,
  Minus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { assessmentsApi } from "@/services/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { Assessment, ComplianceStatus } from "@/types";
import {
  COMPLIANCE_LABELS,
  COMPLIANCE_CLASSES,
  SEVERITY_VARIANTS,
} from "../lib/constants";

export interface AssessmentControlResultsProps {
  assessmentId: number;
  results: Assessment["results"];
  onResultUpdated: () => void;
}

export function AssessmentControlResults({
  assessmentId,
  results,
  onResultUpdated,
}: AssessmentControlResultsProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{
    status: ComplianceStatus;
    evidence: string;
    comment: string;
    remediation_note: string;
  }>({ status: "not_assessed", evidence: "", comment: "", remediation_note: "" });
  const [saving, setSaving] = useState(false);

  // Suppress unused variable warning
  void assessmentId;

  const openEdit = (r: Assessment["results"][0]) => {
    setEditingId(r.id);
    setEditForm({
      status: r.status,
      evidence: r.evidence || "",
      comment: r.comment || "",
      remediation_note: r.remediation_note || "",
    });
  };

  const handleSave = async () => {
    if (editingId === null) return;
    setSaving(true);
    try {
      await assessmentsApi.updateResult(editingId, {
        status: editForm.status,
        evidence: editForm.evidence || undefined,
        comment: editForm.comment || undefined,
        remediation_note: editForm.remediation_note || undefined,
      });
      setEditingId(null);
      onResultUpdated();
    } catch {
      toast.error("Erreur lors de la sauvegarde de l'évaluation");
    } finally {
      setSaving(false);
    }
  };

  const statusIcon = (s: ComplianceStatus) => {
    switch (s) {
      case "compliant": return <CheckCircle className="size-4 text-green-600" />;
      case "non_compliant": return <AlertCircle className="size-4 text-red-600" />;
      case "partially_compliant": return <CircleDot className="size-4 text-yellow-600" />;
      case "not_applicable": return <Minus className="size-4 text-gray-400" />;
      default: return <CircleDot className="size-4 text-gray-300" />;
    }
  };

  if (results.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground text-center border-t">
        Aucun contrôle à évaluer.
      </div>
    );
  }

  return (
    <div className="border-t">
      <div className="max-h-[400px] overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12"></TableHead>
              <TableHead className="w-[100px]">Réf.</TableHead>
              <TableHead>Contrôle</TableHead>
              <TableHead className="w-[90px]">Sévérité</TableHead>
              <TableHead className="w-[130px]">Statut</TableHead>
              <TableHead className="w-[80px] text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{statusIcon(r.status)}</TableCell>
                <TableCell>
                  <code className="text-xs bg-muted px-1 py-0.5 rounded">{r.control_ref_id || `C${r.control_id}`}</code>
                </TableCell>
                <TableCell>
                  <p className="text-sm truncate max-w-xs">{r.control_title || `Contrôle #${r.control_id}`}</p>
                  {r.is_auto_assessed && (
                    <Badge variant="outline" className="text-[10px] px-1 py-0 mt-0.5">
                      <Zap className="h-2.5 w-2.5 mr-0.5" />auto
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  {r.control_severity && (
                    <Badge variant={SEVERITY_VARIANTS[r.control_severity] || "outline"} className="text-xs">
                      {r.control_severity}
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold", COMPLIANCE_CLASSES[r.status])}>
                    {COMPLIANCE_LABELS[r.status]}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openEdit(r)}>
                    <Pencil />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Edit control result dialog */}
      <Dialog open={editingId !== null} onOpenChange={(open) => { if (!open) setEditingId(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Évaluer le contrôle</DialogTitle>
            <DialogDescription>
              {results.find((r) => r.id === editingId)?.control_title || "Contrôle"}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label>Statut de conformité *</Label>
              <Select value={editForm.status} onValueChange={(v) => setEditForm(prev => ({ ...prev, status: v as ComplianceStatus }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="not_assessed">Non évalué</SelectItem>
                    <SelectItem value="compliant">Conforme</SelectItem>
                    <SelectItem value="non_compliant">Non conforme</SelectItem>
                    <SelectItem value="partially_compliant">Partiellement conforme</SelectItem>
                    <SelectItem value="not_applicable">Non applicable</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="result-evidence">Preuve / Évidence</Label>
              <Textarea
                id="result-evidence"
                value={editForm.evidence}
                onChange={(e) => { const value = e.target.value; setEditForm(prev => ({ ...prev, evidence: value })); }}
                placeholder="Captures d'écran, commandes exécutées, résultats..."
                rows={3}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="result-comment">Commentaire</Label>
              <Textarea
                id="result-comment"
                value={editForm.comment}
                onChange={(e) => { const value = e.target.value; setEditForm(prev => ({ ...prev, comment: value })); }}
                placeholder="Observations de l'auditeur..."
                rows={2}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="result-remediation">Note de remédiation</Label>
              <Textarea
                id="result-remediation"
                value={editForm.remediation_note}
                onChange={(e) => { const value = e.target.value; setEditForm(prev => ({ ...prev, remediation_note: value })); }}
                placeholder="Actions recommandées pour la mise en conformité..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingId(null)}>Annuler</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Sauvegarder
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
