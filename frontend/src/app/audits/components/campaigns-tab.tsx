"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Plus,
  Loader2,
  Target,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
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
import { campaignsApi } from "@/services/api";
import { toast } from "sonner";
import type { CampaignSummary, CampaignStatus } from "@/types";
import { CAMPAIGN_LABELS } from "../lib/constants";
import { CampaignDetail } from "./campaign-detail";

export interface CampaignsTabProps {
  auditId: number;
  entrepriseId: number;
}

export function CampaignsTab({ auditId, entrepriseId }: CampaignsTabProps) {
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [campaignName, setCampaignName] = useState("");
  const [campaignDesc, setCampaignDesc] = useState("");

  // Expanded campaign detail
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await campaignsApi.list(1, 100, auditId);
      setCampaigns(res.items);
    } catch {
      toast.error("Erreur lors du chargement des campagnes");
    } finally {
      setLoading(false);
    }
  }, [auditId]);

  useEffect(() => { loadCampaigns(); }, [loadCampaigns]);

  const handleCreate = async () => {
    if (!campaignName.trim()) { setFormError("Le nom est obligatoire"); return; }
    setSaving(true); setFormError("");
    try {
      await campaignsApi.create({ name: campaignName, description: campaignDesc || undefined, audit_id: auditId });
      setCreateOpen(false);
      setCampaignName(""); setCampaignDesc("");
      loadCampaigns();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
    } finally { setSaving(false); }
  };

  const handleStatusChange = async (id: number, newStatus: CampaignStatus) => {
    try {
      // Utiliser les endpoints dédiés qui gèrent aussi le statut des équipements
      if (newStatus === "in_progress") {
        await campaignsApi.start(id);
      } else if (newStatus === "completed") {
        await campaignsApi.complete(id);
      } else {
        await campaignsApi.update(id, { status: newStatus });
      }
      loadCampaigns();
    } catch {
      toast.error("Erreur lors du changement de statut de la campagne");
    }
  };

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
    } catch { return "—"; }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {campaigns.length} campagne{campaigns.length !== 1 ? "s" : ""} d&apos;évaluation
        </p>
        <Button size="sm" onClick={() => { setFormError(""); setCampaignName(""); setCampaignDesc(""); setCreateOpen(true); }}>
          <Plus data-icon="inline-start" />
          Nouvelle campagne
        </Button>
      </div>

      {/* Campaign list */}
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : campaigns.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">
            <Target className="size-10 mx-auto mb-3 opacity-50" />
            <p className="font-medium">Aucune campagne</p>
            <p className="text-sm mt-1">Créez une campagne pour commencer les évaluations</p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {campaigns.map((c) => (
            <Card key={c.id} className="overflow-hidden">
              <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/30 transition-colors"
                onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <Target className="size-4 text-muted-foreground shrink-0" />
                  <div className="min-w-0">
                    <p className="font-medium truncate">{c.name}</p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                      <span>{formatDate(c.created_at)}</span>
                      <span>{c.total_assessments} évaluation{c.total_assessments !== 1 ? "s" : ""}</span>
                      {c.compliance_score !== null && (
                        <span className="font-medium text-foreground">{c.compliance_score}% conformité</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <div onClick={(e) => e.stopPropagation()}>
                    <Select value={c.status} onValueChange={(v) => handleStatusChange(c.id, v as CampaignStatus)}>
                      <SelectTrigger className="h-7 w-[130px] text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {(Object.keys(CAMPAIGN_LABELS) as CampaignStatus[]).map((s) => (
                            <SelectItem key={s} value={s}>{CAMPAIGN_LABELS[s]}</SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>

                  {expandedId === c.id ? (
                    <ChevronUp className="size-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="size-4 text-muted-foreground" />
                  )}
                </div>
              </div>

              {/* Expanded: campaign details with assessments */}
              {expandedId === c.id && (
                <div className="border-t">
                  <CampaignDetail
                    campaignId={c.id}
                    entrepriseId={entrepriseId}
                    onAssessmentChanged={loadCampaigns}
                  />
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Dialog: Create campaign */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouvelle campagne d&apos;évaluation</DialogTitle>
            <DialogDescription>
              Créez une campagne pour regrouper les évaluations de cet audit
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="campaign-name">Nom de la campagne *</Label>
              <Input
                id="campaign-name"
                value={campaignName}
                onChange={(e) => setCampaignName(e.target.value)}
                placeholder="ex: Évaluation réseau Q1 2026"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="campaign-desc">Description</Label>
              <Textarea
                id="campaign-desc"
                value={campaignDesc}
                onChange={(e) => setCampaignDesc(e.target.value)}
                placeholder="Description de la campagne..."
                rows={3}
              />
            </div>
          </div>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Annuler</Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Créer la campagne
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
