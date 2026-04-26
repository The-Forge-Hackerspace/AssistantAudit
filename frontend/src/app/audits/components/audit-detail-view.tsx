"use client";

import {
  ClipboardCheck,
  Building2,
  Calendar,
  BarChart3,
  FileText,
  ArrowLeft,
  FileBarChart,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { auditsApi } from "@/services/api";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { Audit, AuditStatus } from "@/types";
import {
  STATUS_LABELS,
  STATUS_VARIANTS,
  STATUS_ICONS,
} from "../lib/constants";
import { CampaignsTab } from "./campaigns-tab";

export interface AuditDetailViewProps {
  audit: Audit;
  entrepriseMap: Record<number, string>;
  onBack: () => void;
  onAuditUpdated: (a: Audit) => void;
}

export function AuditDetailView({
  audit,
  entrepriseMap,
  onBack,
  onAuditUpdated,
}: AuditDetailViewProps) {
  const router = useRouter();
  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
    } catch { return "—"; }
  };

  const handleStatusChange = async (newStatus: AuditStatus) => {
    try {
      const updated = await auditsApi.update(audit.id, { status: newStatus });
      onAuditUpdated(updated);
    } catch {
      toast.error("Erreur lors du changement de statut");
    }
  };

  const StatusIcon = STATUS_ICONS[audit.status];

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <ClipboardCheck className="size-6" />
            {audit.nom_projet}
          </h1>
          <p className="text-muted-foreground">
            {entrepriseMap[audit.entreprise_id] || `Entreprise #${audit.entreprise_id}`}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push(`/audits/${audit.id}/synthese`)}
          title="Synthèse exécutive"
        >
          <FileBarChart className="size-4 mr-1" />
          Synthèse
        </Button>
        <Badge variant={STATUS_VARIANTS[audit.status]} className="text-sm px-3 py-1">
          <StatusIcon className="size-4 mr-1" />
          {STATUS_LABELS[audit.status]}
        </Badge>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs font-medium text-muted-foreground">Entreprise</p>
            <p className="text-sm font-medium mt-1 flex items-center gap-1">
              <Building2 className="h-3.5 w-3.5" />
              {entrepriseMap[audit.entreprise_id] || `#${audit.entreprise_id}`}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs font-medium text-muted-foreground">Date de début</p>
            <p className="text-sm font-medium mt-1 flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {formatDate(audit.date_debut)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs font-medium text-muted-foreground">Campagnes</p>
            <p className="text-sm font-medium mt-1 flex items-center gap-1">
              <BarChart3 className="h-3.5 w-3.5" />
              {audit.total_campaigns ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs font-medium text-muted-foreground">Changer le statut</p>
            <Select value={audit.status} onValueChange={(v) => handleStatusChange(v as AuditStatus)}>
              <SelectTrigger className="h-7 mt-1 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="NOUVEAU">Nouveau</SelectItem>
                  <SelectItem value="EN_COURS">En cours</SelectItem>
                  <SelectItem value="TERMINE">Terminé</SelectItem>
                  <SelectItem value="ARCHIVE">Archivé</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      </div>

      {/* Documents */}
      {(audit.lettre_mission_path || audit.contrat_path || audit.planning_path) && (
        <div className="flex gap-2 flex-wrap">
          {audit.lettre_mission_path && <Badge variant="secondary"><FileText className="size-3 mr-1" />Lettre de mission</Badge>}
          {audit.contrat_path && <Badge variant="secondary"><FileText className="size-3 mr-1" />Contrat</Badge>}
          {audit.planning_path && <Badge variant="secondary"><FileText className="size-3 mr-1" />Planning</Badge>}
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="campagnes">
        <TabsList>
          <TabsTrigger value="contexte">Contexte</TabsTrigger>
          <TabsTrigger value="campagnes">Campagnes</TabsTrigger>
        </TabsList>

        <TabsContent value="contexte">
          <Card>
            <CardContent className="pt-6 flex flex-col gap-6">
              {audit.objectifs && (
                <div>
                  <p className="text-sm font-semibold text-muted-foreground mb-1">Objectifs</p>
                  <p className="text-sm whitespace-pre-wrap">{audit.objectifs}</p>
                </div>
              )}
              {audit.limites && (
                <div>
                  <p className="text-sm font-semibold text-muted-foreground mb-1">Limites / Périmètre</p>
                  <p className="text-sm whitespace-pre-wrap">{audit.limites}</p>
                </div>
              )}
              {(audit.hypotheses || audit.risques_initiaux) && (
                <div className="grid grid-cols-2 gap-6">
                  {audit.hypotheses && (
                    <div>
                      <p className="text-sm font-semibold text-muted-foreground mb-1">Hypothèses</p>
                      <p className="text-sm whitespace-pre-wrap">{audit.hypotheses}</p>
                    </div>
                  )}
                  {audit.risques_initiaux && (
                    <div>
                      <p className="text-sm font-semibold text-muted-foreground mb-1">Risques initiaux</p>
                      <p className="text-sm whitespace-pre-wrap">{audit.risques_initiaux}</p>
                    </div>
                  )}
                </div>
              )}
              {!audit.objectifs && !audit.limites && !audit.hypotheses && !audit.risques_initiaux && (
                <p className="text-sm text-muted-foreground text-center py-6">
                  Aucune information de contexte renseignée.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="campagnes">
          <CampaignsTab auditId={audit.id} entrepriseId={audit.entreprise_id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
