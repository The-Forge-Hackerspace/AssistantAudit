"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  Loader2,
  ClipboardCheck,
  Shield,
  ChevronDown,
  ChevronUp,
  Server,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
import { Separator } from "@/components/ui/separator";
import {
  campaignsApi,
  assessmentsApi,
  frameworksApi,
  sitesApi,
  equipementsApi,
} from "@/services/api";
import { toast } from "sonner";
import type {
  Campaign,
  FrameworkSummary,
  Site,
  Equipement,
  Score,
} from "@/types";
import { AssessmentControlResults } from "./assessment-control-results";

export interface CampaignDetailProps {
  campaignId: number;
  entrepriseId: number;
  onAssessmentChanged: () => void;
}

export function CampaignDetail({
  campaignId,
  entrepriseId,
  onAssessmentChanged,
}: CampaignDetailProps) {
  const router = useRouter();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [score, setScore] = useState<Score | null>(null);
  const [loading, setLoading] = useState(true);
  const [createAssessmentOpen, setCreateAssessmentOpen] = useState(false);

  // Assessment creation form
  const [frameworks, setFrameworks] = useState<FrameworkSummary[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [equipements, setEquipements] = useState<Equipement[]>([]);
  const [selectedSite, setSelectedSite] = useState<string>("");
  const [selectedEquipement, setSelectedEquipement] = useState<string>("");
  const [selectedFramework, setSelectedFramework] = useState<string>("");
  const [assessmentNotes, setAssessmentNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Expanded assessment
  const [expandedAssessmentId, setExpandedAssessmentId] = useState<number | null>(null);

  const loadCampaign = useCallback(async () => {
    setLoading(true);
    try {
      const [c, s] = await Promise.all([
        campaignsApi.get(campaignId),
        campaignsApi.score(campaignId).catch(() => null),
      ]);
      setCampaign(c);
      setScore(s);
    } catch {
      toast.error("Erreur lors du chargement de la campagne");
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => { loadCampaign(); }, [loadCampaign]);

  const openCreateAssessment = async () => {
    setFormError("");
    setSelectedSite(""); setSelectedEquipement(""); setSelectedFramework(""); setAssessmentNotes("");
    setEquipements([]);

    try {
      const [fwRes, siteRes] = await Promise.all([
        frameworksApi.list(1, 100, true),
        sitesApi.list(1, 100, entrepriseId),
      ]);
      setFrameworks(fwRes.items);
      setSites(siteRes.items);
    } catch { /* ignore */ }

    setCreateAssessmentOpen(true);
  };

  const handleSiteChange = async (siteId: string) => {
    setSelectedSite(siteId);
    setSelectedEquipement("");
    if (siteId) {
      try {
        const res = await equipementsApi.list(1, 100, { site_id: Number(siteId) });
        setEquipements(res.items);
      } catch { setEquipements([]); }
    } else {
      setEquipements([]);
    }
  };

  const handleCreateAssessment = async () => {
    if (!selectedEquipement) { setFormError("Sélectionnez un équipement"); return; }
    if (!selectedFramework) { setFormError("Sélectionnez un référentiel"); return; }
    setSaving(true); setFormError("");
    try {
      await assessmentsApi.create(campaignId, {
        equipement_id: Number(selectedEquipement),
        framework_id: Number(selectedFramework),
        notes: assessmentNotes || undefined,
      });
      setCreateAssessmentOpen(false);
      loadCampaign();
      onAssessmentChanged();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
    } finally { setSaving(false); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!campaign) {
    return <div className="p-4 text-sm text-muted-foreground">Impossible de charger la campagne.</div>;
  }

  return (
    <div className="p-4 flex flex-col gap-4">
      {/* Score bar */}
      {score && score.total_controls > 0 && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Score de conformité</span>
            <span className="font-bold text-lg">{score.compliance_score}%</span>
          </div>
          <Progress value={score.compliance_score} className="h-2" />
          <div className="grid grid-cols-5 gap-2 text-xs text-center">
            <div>
              <div className="font-medium text-green-600">{score.compliant}</div>
              <div className="text-muted-foreground">Conformes</div>
            </div>
            <div>
              <div className="font-medium text-red-600">{score.non_compliant}</div>
              <div className="text-muted-foreground">Non conformes</div>
            </div>
            <div>
              <div className="font-medium text-yellow-600">{score.partially_compliant}</div>
              <div className="text-muted-foreground">Partiels</div>
            </div>
            <div>
              <div className="font-medium text-gray-500">{score.not_applicable}</div>
              <div className="text-muted-foreground">N/A</div>
            </div>
            <div>
              <div className="font-medium text-gray-400">{score.not_assessed}</div>
              <div className="text-muted-foreground">Non évalués</div>
            </div>
          </div>
        </div>
      )}

      {campaign.description && (
        <p className="text-sm text-muted-foreground">{campaign.description}</p>
      )}

      <Separator />

      {/* Assessments header */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          {campaign.assessments.length} évaluation{campaign.assessments.length !== 1 ? "s" : ""}
        </p>
        <Button size="sm" variant="outline" onClick={openCreateAssessment}>
          <Plus data-icon="inline-start" />
          Ajouter une évaluation
        </Button>
      </div>

      {/* Assessment list */}
      {campaign.assessments.length === 0 ? (
        <div className="text-center py-6 text-muted-foreground">
          <Shield className="size-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Aucune évaluation dans cette campagne</p>
          <p className="text-xs mt-1">Ajoutez une évaluation pour associer un équipement à un référentiel</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {campaign.assessments.map((assessment) => (
            <div key={assessment.id} className="border rounded-lg overflow-hidden">
              <div
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/30 transition-colors"
                onClick={() => setExpandedAssessmentId(expandedAssessmentId === assessment.id ? null : assessment.id)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Server className="size-4 text-muted-foreground shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">
                      {assessment.equipement_hostname || assessment.equipement_ip || `Équipement #${assessment.equipement_id}`}
                      {assessment.equipement_ip && assessment.equipement_hostname && (
                        <span className="text-xs text-muted-foreground ml-2 font-mono">{assessment.equipement_ip}</span>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      <Shield className="size-3 inline mr-1" />
                      {assessment.framework_name || `Framework #${assessment.framework_id}`}
                      {assessment.compliance_score !== null && (
                        <span className="ml-2 font-medium text-foreground">{assessment.compliance_score}%</span>
                      )}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {assessment.compliance_score !== null && (
                    <div className="w-16">
                      <Progress value={assessment.compliance_score} className="h-1.5" />
                    </div>
                  )}
                  <Badge variant="outline" className="text-xs">
                    {assessment.results.length} contrôles
                  </Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(`/audits/evaluation?assessmentId=${assessment.id}`);
                    }}
                  >
                    <ClipboardCheck data-icon="inline-start" />
                    Évaluer
                  </Button>
                  {expandedAssessmentId === assessment.id ? (
                    <ChevronUp className="size-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="size-4 text-muted-foreground" />
                  )}
                </div>
              </div>

              {/* Expanded: control results */}
              {expandedAssessmentId === assessment.id && (
                <AssessmentControlResults
                  assessmentId={assessment.id}
                  results={assessment.results}
                  onResultUpdated={loadCampaign}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Dialog: Create assessment */}
      <Dialog open={createAssessmentOpen} onOpenChange={setCreateAssessmentOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Nouvelle évaluation</DialogTitle>
            <DialogDescription>
              Associez un équipement à un référentiel pour créer les contrôles à évaluer
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label>Site *</Label>
              <Select value={selectedSite} onValueChange={handleSiteChange}>
                <SelectTrigger><SelectValue placeholder="Sélectionner un site" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {sites.map((s) => (<SelectItem key={s.id} value={String(s.id)}>{s.nom}</SelectItem>))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Équipement *</Label>
              <Select value={selectedEquipement} onValueChange={setSelectedEquipement} disabled={!selectedSite}>
                <SelectTrigger><SelectValue placeholder={selectedSite ? "Sélectionner un équipement" : "Sélectionnez d'abord un site"} /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {equipements.map((eq) => (
                      <SelectItem key={eq.id} value={String(eq.id)}>
                        <span className="font-mono text-xs mr-2">{eq.ip_address}</span>
                        {eq.hostname || eq.type_equipement}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Référentiel *</Label>
              <Select value={selectedFramework} onValueChange={setSelectedFramework}>
                <SelectTrigger><SelectValue placeholder="Sélectionner un référentiel" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {frameworks.map((fw) => (
                      <SelectItem key={fw.id} value={String(fw.id)}>
                        {fw.name} <span className="text-xs text-muted-foreground ml-1">v{fw.version} · {fw.total_controls} contrôles</span>
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="assessment-notes">Notes</Label>
              <Textarea
                id="assessment-notes"
                value={assessmentNotes}
                onChange={(e) => setAssessmentNotes(e.target.value)}
                placeholder="Notes pour cette évaluation..."
                rows={2}
              />
            </div>
          </div>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateAssessmentOpen(false)}>Annuler</Button>
            <Button onClick={handleCreateAssessment} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Créer l&apos;évaluation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
