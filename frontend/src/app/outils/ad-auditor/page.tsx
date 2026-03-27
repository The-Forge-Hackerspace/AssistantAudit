"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ShieldCheck,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ClipboardCheck,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
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
import { toast } from "sonner";

import { equipementsApi, toolsApi } from "@/services/api";
import type {
  Equipement,
  ADAuditResultSummary,
  ADAuditResultRead,
  ADAuditCreate,
  PrefillResult,
} from "@/types";

import { AuditForm } from "./components/audit-form";
import { AuditResults, SummaryCard } from "./components/audit-results";

// ══════════════════════════════════════════════════════════════
// Page principale
// ══════════════════════════════════════════════════════════════
export default function ADAuditorPage() {
  // ── State ──
  const [equipements, setEquipements] = useState<Equipement[]>([]);
  const [loadingEquipements, setLoadingEquipements] = useState(true);
  const [audits, setAudits] = useState<ADAuditResultSummary[]>([]);
  const [loadingAudits, setLoadingAudits] = useState(false);
  const [selectedAudit, setSelectedAudit] = useState<ADAuditResultRead | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // Form state
  const [selectedEquipementId, setSelectedEquipementId] = useState<string>("");
  const [targetHost, setTargetHost] = useState("");
  const [targetPort, setTargetPort] = useState("389");
  const [useSsl, setUseSsl] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [domain, setDomain] = useState("");
  const [authMethod, setAuthMethod] = useState<"ntlm" | "simple">("ntlm");
  const [launching, setLaunching] = useState(false);

  // Prefill state
  const [prefillDialogOpen, setPrefillDialogOpen] = useState(false);
  const [prefillAuditId, setPrefillAuditId] = useState<number | null>(null);
  const [assessments, setAssessments] = useState<
    { id: number; campaign_id: number; framework_id: number; framework_name: string; created_at: string }[]
  >([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string>("");
  const [prefilling, setPrefilling] = useState(false);
  const [prefillResult, setPrefillResult] = useState<PrefillResult | null>(null);

  // ── Loading ──
  const loadEquipements = useCallback(async () => {
    setLoadingEquipements(true);
    try {
      const res = await equipementsApi.list(1, 100);
      setEquipements(res.items);
    } catch {
      toast.error("Erreur lors du chargement des données");
    } finally {
      setLoadingEquipements(false);
    }
  }, []);

  const loadAudits = useCallback(async () => {
    setLoadingAudits(true);
    try {
      const data = await toolsApi.listADAudits();
      setAudits(data);
    } catch {
      toast.error("Erreur lors du chargement des audits");
    } finally {
      setLoadingAudits(false);
    }
  }, []);

  useEffect(() => {
    loadEquipements();
    loadAudits();
  }, [loadEquipements, loadAudits]);

  // Polling
  useEffect(() => {
    const hasRunning = audits.some((a) => a.status === "running");
    if (!hasRunning) return;
    const interval = setInterval(loadAudits, 3000);
    return () => clearInterval(interval);
  }, [audits, loadAudits]);

  // Auto-fill host when equipment selected
  useEffect(() => {
    if (selectedEquipementId) {
      const eq = equipements.find((e) => e.id === Number(selectedEquipementId));
      if (eq) {
        setTargetHost(eq.ip_address.split("/")[0]);
      }
    }
  }, [selectedEquipementId, equipements]);

  // Auto-adjust port for SSL
  useEffect(() => {
    setTargetPort(useSsl ? "636" : "389");
  }, [useSsl]);

  // ── Actions ──
  const handleLaunch = async () => {
    if (!targetHost || !username || !password || !domain) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    setLaunching(true);
    try {
      const params: ADAuditCreate = {
        target_host: targetHost,
        target_port: Number(targetPort),
        use_ssl: useSsl,
        username,
        password,
        domain,
        auth_method: authMethod,
        equipement_id: selectedEquipementId ? Number(selectedEquipementId) : undefined,
      };
      await toolsApi.launchADAudit(params);
      toast.success("Audit AD lancé en arrière-plan");
      loadAudits();
      // Reset form password for security
      setPassword("");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erreur lors du lancement";
      toast.error(msg);
    } finally {
      setLaunching(false);
    }
  };

  const handleViewDetail = async (auditId: number) => {
    try {
      const detail = await toolsApi.getADAudit(auditId);
      setSelectedAudit(detail);
      setDetailOpen(true);
    } catch {
      toast.error("Erreur lors du chargement du détail");
    }
  };

  const handleDelete = async (auditId: number) => {
    try {
      await toolsApi.deleteADAudit(auditId);
      toast.success("Audit supprimé");
      loadAudits();
    } catch {
      toast.error("Erreur lors de la suppression");
    }
  };

  const handleOpenPrefill = async (auditId: number, equipementId: number | null) => {
    if (!equipementId) {
      toast.error("Cet audit n'est pas lié à un équipement");
      return;
    }
    setPrefillAuditId(auditId);
    setPrefillResult(null);
    setSelectedAssessmentId("");
    try {
      const data = await toolsApi.listAssessmentsForEquipment(equipementId);
      setAssessments(data);
      setPrefillDialogOpen(true);
    } catch {
      toast.error("Erreur lors du chargement des assessments");
    }
  };

  const handlePrefill = async () => {
    if (!prefillAuditId || !selectedAssessmentId) return;
    setPrefilling(true);
    try {
      const result = await toolsApi.prefillFromADAudit(
        prefillAuditId,
        Number(selectedAssessmentId)
      );
      setPrefillResult(result);
      toast.success(`${result.controls_prefilled} contrôles pré-remplis`);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erreur lors du pré-remplissage";
      toast.error(msg);
    } finally {
      setPrefilling(false);
    }
  };

  // ── Render ──
  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link href="/outils">
              <Button variant="ghost" size="sm">
                <ArrowLeft data-icon="inline-start" /> Outils
              </Button>
            </Link>
          </div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <ShieldCheck className="size-6 text-cyan-500" />
            Audit Active Directory
          </h1>
          <p className="text-muted-foreground">
            Audit automatisé d&apos;un domaine AD via LDAP : comptes privilégiés, politique de mots de passe, GPO, LAPS
          </p>
        </div>
      </div>

      {/* Connection Form */}
      <AuditForm
        equipements={equipements}
        loadingEquipements={loadingEquipements}
        selectedEquipementId={selectedEquipementId}
        setSelectedEquipementId={setSelectedEquipementId}
        targetHost={targetHost}
        setTargetHost={setTargetHost}
        targetPort={targetPort}
        setTargetPort={setTargetPort}
        useSsl={useSsl}
        setUseSsl={setUseSsl}
        username={username}
        setUsername={setUsername}
        password={password}
        setPassword={setPassword}
        domain={domain}
        setDomain={setDomain}
        authMethod={authMethod}
        setAuthMethod={setAuthMethod}
        launching={launching}
        handleLaunch={handleLaunch}
        loadAudits={loadAudits}
      />

      {/* Audit History + Detail Dialog */}
      <AuditResults
        audits={audits}
        loadingAudits={loadingAudits}
        handleViewDetail={handleViewDetail}
        handleOpenPrefill={handleOpenPrefill}
        handleDelete={handleDelete}
        selectedAudit={selectedAudit}
        detailOpen={detailOpen}
        onOpenChange={setDetailOpen}
      />

      {/* ── Prefill Dialog ── */}
      <Dialog open={prefillDialogOpen} onOpenChange={setPrefillDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Pré-remplir un assessment</DialogTitle>
            <DialogDescription>
              Sélectionnez l&apos;assessment à pré-remplir avec les résultats de l&apos;audit AD.
            </DialogDescription>
          </DialogHeader>

          {prefillResult ? (
            <div className="flex flex-col gap-4">
              <div className="grid gap-3 grid-cols-2">
                <SummaryCard label="Pré-remplis" value={prefillResult.controls_prefilled} icon={<ClipboardCheck className="size-4" />} />
                <SummaryCard label="Conformes" value={prefillResult.controls_compliant} icon={<CheckCircle2 className="size-4 text-green-500" />} color="text-green-600" />
                <SummaryCard label="Non conformes" value={prefillResult.controls_non_compliant} icon={<XCircle className="size-4 text-red-500" />} color="text-red-600" />
                <SummaryCard label="Partiels" value={prefillResult.controls_partial} icon={<AlertTriangle className="size-4 text-yellow-500" />} color="text-yellow-600" />
              </div>
              <DialogFooter>
                <Button onClick={() => setPrefillDialogOpen(false)}>Fermer</Button>
              </DialogFooter>
            </div>
          ) : (
            <>
              {assessments.length === 0 ? (
                <p className="text-muted-foreground py-4">
                  Aucun assessment trouvé pour cet équipement. Créez d&apos;abord un assessment avec le framework AD.
                </p>
              ) : (
                <div className="flex flex-col gap-4">
                  <div className="flex flex-col gap-2">
                    <Label>Assessment</Label>
                    <Select value={selectedAssessmentId} onValueChange={setSelectedAssessmentId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Sélectionner un assessment" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {assessments.map((a) => (
                            <SelectItem key={a.id} value={String(a.id)}>
                              #{a.id} — {a.framework_name}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setPrefillDialogOpen(false)}>
                      Annuler
                    </Button>
                    <Button onClick={handlePrefill} disabled={!selectedAssessmentId || prefilling}>
                      {prefilling ? (
                        <>
                          <Loader2 className="animate-spin" data-icon="inline-start" />
                          Pré-remplissage...
                        </>
                      ) : (
                        <>
                          <ClipboardCheck data-icon="inline-start" />
                          Pré-remplir
                        </>
                      )}
                    </Button>
                  </DialogFooter>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
