"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Terminal,
  ClipboardCheck,
  Loader2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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
  CollectResultSummary,
  CollectResultRead,
  CollectCreate,
  PrefillResult,
} from "@/types";

import { CollectForm } from "./components/collect-form";
import { CollectResults } from "./components/collect-results";
import { CollectDetailView } from "./components/collect-detail-view";

// ══════════════════════════════════════════════════════════════
// Page principale
// ══════════════════════════════════════════════════════════════
export default function CollectePage() {
  // ── State ──
  const [equipements, setEquipements] = useState<Equipement[]>([]);
  const [loadingEquipements, setLoadingEquipements] = useState(true);
  const [collects, setCollects] = useState<CollectResultSummary[]>([]);
  const [loadingCollects, setLoadingCollects] = useState(false);
  const [selectedCollect, setSelectedCollect] = useState<CollectResultRead | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // Form
  const [method, setMethod] = useState<"ssh" | "winrm">("ssh");
  const [deviceProfile, setDeviceProfile] = useState("linux_server");
  const [selectedEquipementId, setSelectedEquipementId] = useState<string>("");
  const [targetHost, setTargetHost] = useState("");
  const [targetPort, setTargetPort] = useState("22");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [privateKey, setPrivateKey] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [useSsl, setUseSsl] = useState(false);
  const [transport, setTransport] = useState("ntlm");
  const [launching, setLaunching] = useState(false);

  // Prefill
  const [prefillDialogOpen, setPrefillDialogOpen] = useState(false);
  const [prefillCollectId, setPrefillCollectId] = useState<number | null>(null);
  const [assessments, setAssessments] = useState<
    { id: number; campaign_id: number; framework_id: number; framework_name: string; created_at: string }[]
  >([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string>("");
  const [prefilling, setPrefilling] = useState(false);
  const [prefillResult, setPrefillResult] = useState<PrefillResult | null>(null);

  // ── Chargement ──
  const loadEquipements = useCallback(async () => {
    setLoadingEquipements(true);
    try {
      const res = await equipementsApi.list(1, 100);
      setEquipements(res.items);
    } catch {
      // silently handled
    } finally {
      setLoadingEquipements(false);
    }
  }, []);

  const loadCollects = useCallback(async () => {
    setLoadingCollects(true);
    try {
      const data = await toolsApi.listCollects();
      setCollects(data);
    } catch {
      // silently handled
    } finally {
      setLoadingCollects(false);
    }
  }, []);

  useEffect(() => {
    loadEquipements();
    loadCollects();
  }, [loadEquipements, loadCollects]);

  // Polling des collectes en cours
  useEffect(() => {
    const hasRunning = collects.some((c) => c.status === "running");
    if (!hasRunning) return;
    const interval = setInterval(loadCollects, 3000);
    return () => clearInterval(interval);
  }, [collects, loadCollects]);

  // Auto-fill host when equipment selected
  useEffect(() => {
    if (selectedEquipementId) {
      const eq = equipements.find((e) => e.id === Number(selectedEquipementId));
      if (eq) {
        setTargetHost(eq.ip_address.split("/")[0]); // Strip CIDR
      }
    }
  }, [selectedEquipementId, equipements]);

  // Adjust default port when method changes
  useEffect(() => {
    setTargetPort(method === "ssh" ? "22" : "5985");
    if (method === "winrm") setDeviceProfile("linux_server");
  }, [method]);

  // ── Actions ──
  const handleLaunch = async () => {
    if (!selectedEquipementId || !targetHost || !username) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    setLaunching(true);
    try {
      const params: CollectCreate = {
        equipement_id: Number(selectedEquipementId),
        method,
        device_profile: method === "ssh" ? deviceProfile : undefined,
        target_host: targetHost,
        target_port: Number(targetPort),
        username,
        password: password || undefined,
        private_key: privateKey || undefined,
        passphrase: passphrase || undefined,
        use_ssl: useSsl,
        transport,
      };
      await toolsApi.launchCollect(params);
      toast.success("Collecte lancée en arrière-plan");
      loadCollects();
    } catch {
      toast.error("Erreur lors du lancement de la collecte");
    } finally {
      setLaunching(false);
    }
  };

  const handleViewDetail = async (collectId: number) => {
    try {
      const data = await toolsApi.getCollect(collectId);
      setSelectedCollect(data);
      setDetailOpen(true);
    } catch {
      toast.error("Erreur lors du chargement du détail");
    }
  };

  const handleDelete = async (collectId: number) => {
    try {
      await toolsApi.deleteCollect(collectId);
      toast.success("Collecte supprimée");
      setCollects((prev) => prev.filter((c) => c.id !== collectId));
    } catch {
      toast.error("Erreur lors de la suppression");
    }
  };

  const openPrefillDialog = async (collectId: number) => {
    const collect = collects.find((c) => c.id === collectId);
    if (!collect) return;
    try {
      const data = await toolsApi.listAssessmentsForEquipment(collect.equipement_id);
      setAssessments(data);
      setPrefillCollectId(collectId);
      setPrefillResult(null);
      setSelectedAssessmentId("");
      setPrefillDialogOpen(true);
    } catch {
      toast.error("Erreur chargement des assessments");
    }
  };

  const handlePrefill = async () => {
    if (!prefillCollectId || !selectedAssessmentId) return;
    setPrefilling(true);
    try {
      const res = await toolsApi.prefillFromCollect(
        prefillCollectId,
        Number(selectedAssessmentId)
      );
      setPrefillResult(res);
      toast.success(
        `${res.controls_prefilled} contrôle(s) pré-rempli(s) — ` +
        `${res.controls_compliant} conformes, ${res.controls_non_compliant} non conformes`
      );
    } catch {
      toast.error("Erreur lors du pré-remplissage");
    } finally {
      setPrefilling(false);
    }
  };

  // ── Grouper les équipements par type ──
  const groupedEquipements = {
    serveurs: equipements.filter((e) => e.type_equipement === "serveur"),
    firewalls: equipements.filter((e) => e.type_equipement === "firewall"),
    reseaux: equipements.filter((e) => e.type_equipement === "reseau"),
    autres: equipements.filter(
      (e) => !["serveur", "firewall", "reseau"].includes(e.type_equipement)
    ),
  };

  // ══════════════════════════════════════════════════════════════
  // Render
  // ══════════════════════════════════════════════════════════════
  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link href="/outils">
              <Button variant="ghost" size="sm" className="gap-1">
                <ArrowLeft data-icon="inline-start" />
                Outils
              </Button>
            </Link>
          </div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Terminal className="size-6" />
            Collecte SSH / WinRM
          </h1>
          <p className="text-muted-foreground">
            Collecte automatique d&apos;informations système sur les serveurs via SSH (Linux) ou WinRM (Windows)
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadCollects} className="gap-2">
          <RefreshCw data-icon="inline-start" />
          Rafraîchir
        </Button>
      </div>

      {/* Launch form */}
      <CollectForm
        method={method}
        setMethod={setMethod}
        deviceProfile={deviceProfile}
        setDeviceProfile={setDeviceProfile}
        selectedEquipementId={selectedEquipementId}
        setSelectedEquipementId={setSelectedEquipementId}
        targetHost={targetHost}
        setTargetHost={setTargetHost}
        targetPort={targetPort}
        setTargetPort={setTargetPort}
        username={username}
        setUsername={setUsername}
        password={password}
        setPassword={setPassword}
        privateKey={privateKey}
        setPrivateKey={setPrivateKey}
        passphrase={passphrase}
        setPassphrase={setPassphrase}
        useSsl={useSsl}
        setUseSsl={setUseSsl}
        transport={transport}
        setTransport={setTransport}
        launching={launching}
        loadingEquipements={loadingEquipements}
        groupedEquipements={groupedEquipements}
        onLaunch={handleLaunch}
      />

      {/* Collects history */}
      <CollectResults
        collects={collects}
        loadingCollects={loadingCollects}
        onViewDetail={handleViewDetail}
        onDelete={handleDelete}
        onPrefill={openPrefillDialog}
      />

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-[70vw] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Terminal className="size-5" />
              Détail de la collecte #{selectedCollect?.id}
            </DialogTitle>
            <DialogDescription>
              {selectedCollect?.method === "ssh" ? "SSH" : "WinRM"} →{" "}
              {selectedCollect?.target_host}:{selectedCollect?.target_port} —{" "}
              {selectedCollect?.hostname_collected || "N/A"}
            </DialogDescription>
          </DialogHeader>

          {selectedCollect && (
            <CollectDetailView collect={selectedCollect} />
          )}

          <DialogFooter>
            <Button onClick={() => setDetailOpen(false)}>Fermer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Prefill Dialog */}
      <Dialog open={prefillDialogOpen} onOpenChange={setPrefillDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ClipboardCheck className="size-5" />
              Pré-remplir l&apos;audit
            </DialogTitle>
            <DialogDescription>
              Les résultats de la collecte seront mappés aux contrôles du référentiel
              de l&apos;assessment sélectionné.
            </DialogDescription>
          </DialogHeader>

          {!prefillResult ? (
            <>
              <div className="flex flex-col gap-4 py-4">
                <div className="flex flex-col gap-2">
                  <Label>Assessment à pré-remplir</Label>
                  <Select
                    value={selectedAssessmentId}
                    onValueChange={setSelectedAssessmentId}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner un assessment…" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        {assessments.map((a) => (
                          <SelectItem key={a.id} value={String(a.id)}>
                            {a.framework_name} — {new Date(a.created_at).toLocaleDateString("fr-FR")}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </div>

                <div className="rounded-lg border p-3 bg-amber-50 dark:bg-amber-950/20 text-sm">
                  <p className="font-medium text-amber-700 dark:text-amber-400 mb-1">Attention</p>
                  <p className="text-amber-600 dark:text-amber-500">
                    Les contrôles déjà évalués seront écrasés par les résultats
                    de la collecte automatique. Cette action est irréversible.
                  </p>
                </div>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setPrefillDialogOpen(false)}>
                  Annuler
                </Button>
                <Button
                  onClick={handlePrefill}
                  disabled={!selectedAssessmentId || prefilling}
                  className="gap-2"
                >
                  {prefilling && <Loader2 className="animate-spin" />}
                  Pré-remplir
                </Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <div className="flex flex-col gap-4 py-4">
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
                                  <CheckCircle2 className="size-3" />
                                  Conforme
                                </Badge>
                              ) : (
                                <Badge variant="destructive" className="gap-1 whitespace-nowrap">
                                  <XCircle className="size-3" />
                                  Non conforme
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
