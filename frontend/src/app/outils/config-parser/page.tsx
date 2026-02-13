"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FileCode,
  Upload,
  Shield,
  AlertTriangle,
  ShieldAlert,
  Info,
  Loader2,
  Network,
  List,
  Bug,
  Link2,
  CheckCircle2,
  XCircle,
  ClipboardCheck,
  History,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toolsApi, equipementsApi } from "@/services/api";
import type {
  ConfigUploadResponse,
  SecurityFinding,
  InterfaceInfo,
  FirewallRuleInfo,
  Equipement,
  ConfigAnalysisSummary,
  PrefillResult,
} from "@/types";
import { toast } from "sonner";
import {
  SEVERITY_LABELS,
  SEVERITY_COLORS,
  SEVERITY_VARIANTS,
} from "@/lib/constants";

interface AssessmentOption {
  id: number;
  campaign_id: number;
  framework_id: number;
  framework_name: string;
  created_at: string;
}

export default function ConfigParserPage() {
  const [result, setResult] = useState<ConfigUploadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // Equipment linking
  const [equipements, setEquipements] = useState<Equipement[]>([]);
  const [selectedEquipementId, setSelectedEquipementId] = useState<string>("");
  const [loadingEquipements, setLoadingEquipements] = useState(false);

  // Saved analyses
  const [savedAnalyses, setSavedAnalyses] = useState<ConfigAnalysisSummary[]>([]);

  // Prefill
  const [prefillDialogOpen, setPrefillDialogOpen] = useState(false);
  const [assessments, setAssessments] = useState<AssessmentOption[]>([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string>("");
  const [prefilling, setPrefilling] = useState(false);
  const [prefillResult, setPrefillResult] = useState<PrefillResult | null>(null);

  // Load equipements on mount
  useEffect(() => {
    loadEquipements();
  }, []);

  // Load saved analyses when equipment changes
  const loadSavedAnalyses = useCallback(async (eqId?: number) => {
    try {
      const analyses = await toolsApi.listConfigAnalyses(eqId);
      setSavedAnalyses(analyses);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    const eqId = selectedEquipementId && selectedEquipementId !== "none"
      ? parseInt(selectedEquipementId) : undefined;
    loadSavedAnalyses(eqId);
  }, [selectedEquipementId, loadSavedAnalyses]);

  const loadEquipements = async () => {
    setLoadingEquipements(true);
    try {
      const res = await equipementsApi.list(1, 100);
      setEquipements(res.items);
    } catch (err) {
      console.error("Erreur chargement équipements:", err);
    } finally {
      setLoadingEquipements(false);
    }
  };

  const handleUpload = async (file: File) => {
    setLoading(true);
    try {
      const eqId = selectedEquipementId && selectedEquipementId !== "none"
        ? parseInt(selectedEquipementId) : undefined;
      const res = await toolsApi.analyzeConfig(file, eqId);
      setResult(res);
      const linked = eqId ? " et liée à l'équipement" : "";
      toast.success(
        `Configuration analysée${linked} — ${res.analysis.findings.length} constat(s)`
      );
      // Refresh saved analyses
      if (eqId) loadSavedAnalyses(eqId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur lors de l'analyse";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  const handleDeleteAnalysis = async (id: number) => {
    try {
      await toolsApi.deleteConfigAnalysis(id);
      toast.success("Analyse supprimée");
      const eqId = selectedEquipementId && selectedEquipementId !== "none"
        ? parseInt(selectedEquipementId) : undefined;
      loadSavedAnalyses(eqId);
    } catch {
      toast.error("Erreur lors de la suppression");
    }
  };

  const openPrefillDialog = async () => {
    if (!result?.config_analysis_id || !selectedEquipementId || selectedEquipementId === "none") {
      toast.error("Veuillez d'abord lier l'analyse à un équipement");
      return;
    }
    try {
      const list = await toolsApi.listAssessmentsForEquipment(parseInt(selectedEquipementId));
      setAssessments(list);
      if (list.length === 0) {
        toast.warning("Aucun assessment trouvé pour cet équipement. Créez d'abord une campagne d'évaluation.");
        return;
      }
      setPrefillDialogOpen(true);
      setPrefillResult(null);
      setSelectedAssessmentId("");
    } catch {
      toast.error("Erreur lors du chargement des assessments");
    }
  };

  const handlePrefill = async () => {
    if (!result?.config_analysis_id || !selectedAssessmentId) return;
    setPrefilling(true);
    try {
      const res = await toolsApi.prefillAudit(
        result.config_analysis_id,
        parseInt(selectedAssessmentId)
      );
      setPrefillResult(res);
      toast.success(
        `${res.controls_prefilled} contrôle(s) pré-rempli(s) — ` +
        `${res.controls_compliant} conforme(s), ${res.controls_non_compliant} non conforme(s)`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur lors du pré-remplissage";
      toast.error(msg);
    } finally {
      setPrefilling(false);
    }
  };

  const findings = result?.analysis?.findings || [];
  const critCount = findings.filter((f) => f.severity === "critical").length;
  const highCount = findings.filter((f) => f.severity === "high").length;
  const medCount = findings.filter((f) => f.severity === "medium").length;
  const lowCount = findings.filter((f) => f.severity === "low").length;

  // Group equipements by type for the selector
  const firewalls = equipements.filter((e) => e.type_equipement === "firewall");
  const reseaux = equipements.filter((e) => e.type_equipement === "reseau");
  const serveurs = equipements.filter((e) => e.type_equipement === "serveur");
  const autres = equipements.filter(
    (e) => !["firewall", "reseau", "serveur"].includes(e.type_equipement)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <FileCode className="h-6 w-6" />
          Analyseur de Configuration
        </h1>
        <p className="text-muted-foreground">
          Upload d&apos;un export de configuration réseau, analyse de sécurité
          et liaison à un équipement pour pré-remplir l&apos;audit
        </p>
      </div>

      {/* Equipment selector + Upload zone */}
      {!result && (
        <>
          {/* Equipment selector */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Link2 className="h-4 w-4" />
                Équipement cible (optionnel)
              </CardTitle>
              <CardDescription>
                Sélectionnez un équipement pour sauvegarder l&apos;analyse et
                pouvoir pré-remplir automatiquement les contrôles d&apos;audit
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Select
                value={selectedEquipementId}
                onValueChange={setSelectedEquipementId}
              >
                <SelectTrigger className="w-full max-w-md">
                  <SelectValue placeholder={
                    loadingEquipements
                      ? "Chargement…"
                      : "Aucun équipement (analyse seule)"
                  } />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">
                    Aucun équipement (analyse seule)
                  </SelectItem>
                  {firewalls.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>Firewalls</SelectLabel>
                      {firewalls.map((eq) => (
                        <SelectItem key={eq.id} value={String(eq.id)}>
                          {eq.hostname || eq.ip_address}
                          {eq.fabricant ? ` (${eq.fabricant})` : ""}
                          {" — "}{eq.ip_address}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                  {reseaux.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>Réseau</SelectLabel>
                      {reseaux.map((eq) => (
                        <SelectItem key={eq.id} value={String(eq.id)}>
                          {eq.hostname || eq.ip_address}
                          {eq.fabricant ? ` (${eq.fabricant})` : ""}
                          {" — "}{eq.ip_address}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                  {serveurs.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>Serveurs</SelectLabel>
                      {serveurs.map((eq) => (
                        <SelectItem key={eq.id} value={String(eq.id)}>
                          {eq.hostname || eq.ip_address}
                          {eq.fabricant ? ` (${eq.fabricant})` : ""}
                          {" — "}{eq.ip_address}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                  {autres.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>Autres</SelectLabel>
                      {autres.map((eq) => (
                        <SelectItem key={eq.id} value={String(eq.id)}>
                          {eq.hostname || eq.ip_address}
                          {eq.fabricant ? ` (${eq.fabricant})` : ""}
                          {" — "}{eq.ip_address}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                </SelectContent>
              </Select>

              {selectedEquipementId && selectedEquipementId !== "none" && (
                <p className="mt-2 text-sm text-green-600 flex items-center gap-1">
                  <CheckCircle2 className="h-4 w-4" />
                  L&apos;analyse sera automatiquement liée à cet équipement
                </p>
              )}
            </CardContent>
          </Card>

          {/* Upload zone */}
          <Card>
            <CardContent className="pt-6">
              <div
                className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                  dragOver
                    ? "border-primary bg-primary/5"
                    : "border-muted-foreground/25 hover:border-primary/50"
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
              >
                {loading ? (
                  <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                    <p className="text-lg font-medium">Analyse en cours…</p>
                    <p className="text-sm text-muted-foreground">
                      Parsing de la configuration et détection des problèmes de sécurité
                    </p>
                  </div>
                ) : (
                  <>
                    <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-lg font-medium mb-2">
                      Glissez-déposez un fichier de configuration
                    </p>
                    <p className="text-sm text-muted-foreground mb-4">
                      FortiGate (.conf, .txt) • OPNsense (.xml)
                    </p>
                    <label>
                      <Button asChild variant="outline">
                        <span>
                          <Upload className="h-4 w-4 mr-2" />
                          Parcourir…
                        </span>
                      </Button>
                      <input
                        type="file"
                        className="hidden"
                        accept=".conf,.txt,.xml,.cfg"
                        onChange={handleFileInput}
                      />
                    </label>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Saved analyses history */}
          {savedAnalyses.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <History className="h-4 w-4" />
                  Analyses sauvegardées
                  <Badge variant="outline" className="ml-2">
                    {savedAnalyses.length}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fichier</TableHead>
                      <TableHead>Vendor</TableHead>
                      <TableHead>Hostname</TableHead>
                      <TableHead>Constats</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead className="w-10"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {savedAnalyses.map((a) => (
                      <TableRow key={a.id}>
                        <TableCell className="font-medium">{a.filename}</TableCell>
                        <TableCell>{a.vendor}</TableCell>
                        <TableCell>{a.hostname || "—"}</TableCell>
                        <TableCell>
                          <Badge variant={a.findings_count > 0 ? "destructive" : "secondary"}>
                            {a.findings_count}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {new Date(a.created_at).toLocaleDateString("fr-FR")}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleDeleteAnalysis(a.id)}
                          >
                            <Trash2 className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card>
              <CardContent className="pt-4 text-center">
                <p className="text-sm text-muted-foreground">Vendor</p>
                <p className="text-lg font-bold">{result.analysis.vendor}</p>
                {result.analysis.hostname && (
                  <p className="text-sm text-muted-foreground">
                    {result.analysis.hostname}
                  </p>
                )}
              </CardContent>
            </Card>
            <Card className={critCount > 0 ? "border-red-300 bg-red-50 dark:bg-red-950/20" : ""}>
              <CardContent className="pt-4 text-center">
                <p className="text-sm text-muted-foreground">Critique</p>
                <p className="text-2xl font-bold text-red-600">{critCount}</p>
              </CardContent>
            </Card>
            <Card className={highCount > 0 ? "border-orange-300 bg-orange-50 dark:bg-orange-950/20" : ""}>
              <CardContent className="pt-4 text-center">
                <p className="text-sm text-muted-foreground">Élevé</p>
                <p className="text-2xl font-bold text-orange-600">{highCount}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 text-center">
                <p className="text-sm text-muted-foreground">Moyen</p>
                <p className="text-2xl font-bold text-yellow-600">{medCount}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 text-center">
                <p className="text-sm text-muted-foreground">Faible</p>
                <p className="text-2xl font-bold text-blue-600">{lowCount}</p>
              </CardContent>
            </Card>
          </div>

          {/* Linked equipment info + prefill button */}
          {result.config_analysis_id && (
            <Card className="border-green-200 bg-green-50 dark:bg-green-950/20">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Link2 className="h-5 w-5 text-green-600" />
                    <span className="font-medium text-green-700 dark:text-green-400">
                      Analyse sauvegardée et liée à l&apos;équipement
                    </span>
                    <Badge variant="outline" className="text-green-700 dark:text-green-400">
                      #{result.config_analysis_id}
                    </Badge>
                  </div>
                  <Button
                    onClick={openPrefillDialog}
                    className="gap-2"
                  >
                    <ClipboardCheck className="h-4 w-4" />
                    Pré-remplir l&apos;audit
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tabs: Findings / Interfaces / Rules */}
          <Tabs defaultValue="findings" className="space-y-4">
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger value="findings" className="gap-1">
                  <Bug className="h-4 w-4" />
                  Constats ({findings.length})
                </TabsTrigger>
                <TabsTrigger value="interfaces" className="gap-1">
                  <Network className="h-4 w-4" />
                  Interfaces ({result.analysis.interfaces.length})
                </TabsTrigger>
                <TabsTrigger value="rules" className="gap-1">
                  <List className="h-4 w-4" />
                  Règles ({result.analysis.firewall_rules.length})
                </TabsTrigger>
              </TabsList>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setResult(null)}
              >
                Nouvelle analyse
              </Button>
            </div>

            {/* Findings tab */}
            <TabsContent value="findings">
              <Card>
                <CardContent className="pt-6">
                  {findings.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <Shield className="h-12 w-12 mx-auto mb-4 text-green-500" />
                      <p className="text-lg font-medium">
                        Aucun problème de sécurité détecté
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {findings.map((finding, idx) => (
                        <FindingCard key={idx} finding={finding} />
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Interfaces tab */}
            <TabsContent value="interfaces">
              <Card>
                <CardContent className="pt-6">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Nom</TableHead>
                        <TableHead>IP / Masque</TableHead>
                        <TableHead>Statut</TableHead>
                        <TableHead>VLAN</TableHead>
                        <TableHead>Accès autorisés</TableHead>
                        <TableHead>Description</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.analysis.interfaces.map((iface, idx) => (
                        <InterfaceRow key={idx} iface={iface} />
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Rules tab */}
            <TabsContent value="rules">
              <Card>
                <CardContent className="pt-6">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>#</TableHead>
                        <TableHead>Nom</TableHead>
                        <TableHead>Source</TableHead>
                        <TableHead>Destination</TableHead>
                        <TableHead>Service</TableHead>
                        <TableHead>Action</TableHead>
                        <TableHead>Log</TableHead>
                        <TableHead>Actif</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.analysis.firewall_rules.map((rule, idx) => (
                        <RuleRow key={idx} rule={rule} />
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}

      {/* Prefill Dialog */}
      <Dialog open={prefillDialogOpen} onOpenChange={setPrefillDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ClipboardCheck className="h-5 w-5" />
              Pré-remplir l&apos;audit
            </DialogTitle>
            <DialogDescription>
              Les constats de l&apos;analyse de configuration seront mappés aux
              contrôles du référentiel de l&apos;assessment sélectionné.
            </DialogDescription>
          </DialogHeader>

          {!prefillResult ? (
            <>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Assessment à pré-remplir</label>
                  <Select
                    value={selectedAssessmentId}
                    onValueChange={setSelectedAssessmentId}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner un assessment…" />
                    </SelectTrigger>
                    <SelectContent>
                      {assessments.map((a) => (
                        <SelectItem key={a.id} value={String(a.id)}>
                          {a.framework_name} — {new Date(a.created_at).toLocaleDateString("fr-FR")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="rounded-lg border p-3 bg-amber-50 dark:bg-amber-950/20 text-sm">
                  <p className="font-medium text-amber-700 dark:text-amber-400 mb-1">Attention</p>
                  <p className="text-amber-600 dark:text-amber-500">
                    Les contrôles déjà évalués seront écrasés par les résultats
                    de l&apos;analyse automatique. Cette action est irréversible.
                  </p>
                </div>
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setPrefillDialogOpen(false)}
                >
                  Annuler
                </Button>
                <Button
                  onClick={handlePrefill}
                  disabled={!selectedAssessmentId || prefilling}
                  className="gap-2"
                >
                  {prefilling && <Loader2 className="h-4 w-4 animate-spin" />}
                  Pré-remplir
                </Button>
              </DialogFooter>
            </>
          ) : (
            <>
              {/* Prefill results */}
              <div className="space-y-4 py-4">
                <div className="grid grid-cols-3 gap-3">
                  <Card>
                    <CardContent className="pt-3 text-center">
                      <p className="text-2xl font-bold">{prefillResult.controls_prefilled}</p>
                      <p className="text-xs text-muted-foreground">Pré-remplis</p>
                    </CardContent>
                  </Card>
                  <Card className="border-green-200">
                    <CardContent className="pt-3 text-center">
                      <p className="text-2xl font-bold text-green-600">{prefillResult.controls_compliant}</p>
                      <p className="text-xs text-muted-foreground">Conformes</p>
                    </CardContent>
                  </Card>
                  <Card className="border-red-200">
                    <CardContent className="pt-3 text-center">
                      <p className="text-2xl font-bold text-red-600">{prefillResult.controls_non_compliant}</p>
                      <p className="text-xs text-muted-foreground">Non conformes</p>
                    </CardContent>
                  </Card>
                </div>

                {prefillResult.details.length > 0 && (
                  <div className="max-h-80 overflow-y-auto rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[80px]">Réf.</TableHead>
                          <TableHead>Contrôle</TableHead>
                          <TableHead className="w-[160px] text-right">Résultat</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {prefillResult.details.map((d, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-mono text-sm whitespace-nowrap">{d.control_ref}</TableCell>
                            <TableCell className="text-sm">{d.control_title}</TableCell>
                            <TableCell className="text-right">
                              {d.status === "compliant" ? (
                                <Badge variant="outline" className="text-green-600 gap-1 whitespace-nowrap">
                                  <CheckCircle2 className="h-3 w-3" />
                                  Conforme
                                </Badge>
                              ) : (
                                <Badge variant="destructive" className="gap-1 whitespace-nowrap">
                                  <XCircle className="h-3 w-3" />
                                  Non conforme ({d.findings_count})
                                </Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>

              <DialogFooter>
                <Button onClick={() => setPrefillDialogOpen(false)}>
                  Fermer
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Finding card ──
function FindingCard({ finding }: { finding: SecurityFinding }) {
  const SeverityIcon =
    finding.severity === "critical"
      ? ShieldAlert
      : finding.severity === "high"
      ? AlertTriangle
      : finding.severity === "medium"
      ? Shield
      : Info;

  return (
    <div
      className={`rounded-lg border p-4 ${
        SEVERITY_COLORS[finding.severity] || "bg-gray-50"
      }`}
    >
      <div className="flex items-start gap-3">
        <SeverityIcon className="h-5 w-5 mt-0.5 shrink-0" />
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant={SEVERITY_VARIANTS[finding.severity] || "outline"}>
              {SEVERITY_LABELS[finding.severity] || finding.severity}
            </Badge>
            <Badge variant="outline">{finding.category}</Badge>
            <span className="font-semibold text-sm">{finding.title}</span>
          </div>
          <p className="text-sm">{finding.description}</p>
          {finding.remediation && (
            <p className="text-sm italic">
              <strong>Recommandation :</strong> {finding.remediation}
            </p>
          )}
          {finding.reference && (
            <p className="text-xs text-muted-foreground">
              Réf : {finding.reference}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Interface row ──
function InterfaceRow({ iface }: { iface: InterfaceInfo }) {
  return (
    <TableRow>
      <TableCell className="font-medium">{iface.name}</TableCell>
      <TableCell className="font-mono text-sm">
        {iface.ip_address || "—"}
        {iface.netmask && ` / ${iface.netmask}`}
      </TableCell>
      <TableCell>
        <Badge variant={iface.status === "up" ? "default" : "secondary"}>
          {iface.status}
        </Badge>
      </TableCell>
      <TableCell>{iface.vlan ?? "—"}</TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1">
          {iface.allowed_access.length > 0
            ? iface.allowed_access.map((a) => (
                <Badge key={a} variant="outline" className="text-xs">
                  {a}
                </Badge>
              ))
            : "—"}
        </div>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        {iface.description || "—"}
      </TableCell>
    </TableRow>
  );
}

// ── Rule row ──
function RuleRow({ rule }: { rule: FirewallRuleInfo }) {
  const isPermit = rule.action === "accept" || rule.action === "pass";
  const isDangerous =
    isPermit &&
    (rule.source_address === "all" || rule.source_address === "any") &&
    (rule.dest_address === "all" || rule.dest_address === "any") &&
    (rule.service === "ALL" || rule.service === "any" || rule.service === "any/any");

  return (
    <TableRow className={isDangerous ? "bg-red-50 dark:bg-red-950/20" : ""}>
      <TableCell className="font-mono">{rule.rule_id}</TableCell>
      <TableCell className="font-medium">{rule.name || "—"}</TableCell>
      <TableCell className="text-sm">
        {rule.source_interface && (
          <span className="text-muted-foreground">{rule.source_interface}:</span>
        )}
        {rule.source_address || "—"}
      </TableCell>
      <TableCell className="text-sm">
        {rule.dest_interface && (
          <span className="text-muted-foreground">{rule.dest_interface}:</span>
        )}
        {rule.dest_address || "—"}
      </TableCell>
      <TableCell className="font-mono text-sm">{rule.service || "—"}</TableCell>
      <TableCell>
        <Badge variant={isPermit ? "default" : "destructive"}>
          {rule.action}
        </Badge>
      </TableCell>
      <TableCell>
        {rule.log_traffic ? (
          <Badge variant="outline" className="text-green-700">
            Oui
          </Badge>
        ) : (
          <span className="text-muted-foreground text-sm">Non</span>
        )}
      </TableCell>
      <TableCell>
        {rule.enabled ? (
          <Badge variant="outline" className="text-green-700">
            Oui
          </Badge>
        ) : (
          <Badge variant="secondary">Non</Badge>
        )}
      </TableCell>
    </TableRow>
  );
}
