"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Terminal,
  Server,
  Monitor,
  Play,
  Loader2,
  Trash2,
  Eye,
  X,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Shield,
  Cpu,
  HardDrive,
  Network,
  Users,
  Activity,
  RefreshCw,
  ClipboardCheck,
  ArrowLeft,
  Info,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

import { equipementsApi, toolsApi } from "@/services/api";
import type {
  Equipement,
  CollectResultSummary,
  CollectResultRead,
  CollectCreate,
  PrefillResult,
} from "@/types";

// ── Constantes ──────────────────────────────────────────────
const STATUS_LABELS: Record<string, string> = {
  running: "En cours",
  success: "Succès",
  failed: "Échec",
};

const STATUS_COLORS: Record<string, string> = {
  running: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  success: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

const METHOD_LABELS: Record<string, string> = {
  ssh: "SSH (Linux)",
  winrm: "WinRM (Windows)",
};

const PROFILE_OPTIONS: { value: string; label: string; description: string }[] = [
  { value: "linux_server", label: "Serveur Linux", description: "OS, kernel, SSH, firewall, utilisateurs, services, stockage" },
  { value: "opnsense", label: "OPNsense", description: "pf rules, Suricata IDS, CARP HA, VPN, packages, interfaces" },
  { value: "stormshield", label: "Stormshield (SNS)", description: "Filter rules, VPN IPsec/SSL, HA, auth, supervision, logs" },
  { value: "fortigate", label: "FortiGate (FortiOS)", description: "Firewall policies, VPN, admin users, FortiGuard, HA, logs" },
];

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
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="size-5" />
            Lancer une collecte
          </CardTitle>
          <CardDescription>
            Connectez-vous à un serveur pour collecter automatiquement les informations d&apos;audit.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          {/* Row 1: Method + Profile + Equipment */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col gap-2">
              <Label>Méthode de connexion</Label>
              <Select value={method} onValueChange={(v) => setMethod(v as "ssh" | "winrm")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="ssh">
                      <span className="flex items-center gap-2">
                        <Server className="size-4" /> SSH — Linux / Firewall
                      </span>
                    </SelectItem>
                    <SelectItem value="winrm">
                      <span className="flex items-center gap-2">
                        <Monitor className="size-4" /> WinRM — Serveur Windows
                      </span>
                    </SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>

            {method === "ssh" && (
              <div className="flex flex-col gap-2">
                <Label>Profil de collecte</Label>
                <Select value={deviceProfile} onValueChange={setDeviceProfile}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {PROFILE_OPTIONS.map((p) => (
                        <SelectItem key={p.value} value={p.value}>
                          <span className="flex items-center gap-2">
                            {p.value === "linux_server" ? (
                              <Server className="size-4" />
                            ) : (
                              <Shield className="size-4" />
                            )}
                            {p.label}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="flex flex-col gap-2">
              <Label>Équipement cible</Label>
              {loadingEquipements ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <Select value={selectedEquipementId} onValueChange={setSelectedEquipementId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner un équipement…" />
                  </SelectTrigger>
                  <SelectContent>
                    {groupedEquipements.serveurs.length > 0 && (
                      <SelectGroup>
                        <SelectLabel>Serveurs</SelectLabel>
                        {groupedEquipements.serveurs.map((e) => (
                          <SelectItem key={e.id} value={String(e.id)}>
                            {e.hostname || e.ip_address} — {e.ip_address}
                            {e.fabricant ? ` (${e.fabricant})` : ""}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    )}
                    {groupedEquipements.firewalls.length > 0 && (
                      <SelectGroup>
                        <SelectLabel>Firewalls</SelectLabel>
                        {groupedEquipements.firewalls.map((e) => (
                          <SelectItem key={e.id} value={String(e.id)}>
                            {e.hostname || e.ip_address} — {e.ip_address}
                            {e.fabricant ? ` (${e.fabricant})` : ""}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    )}
                    {groupedEquipements.reseaux.length > 0 && (
                      <SelectGroup>
                        <SelectLabel>Réseau</SelectLabel>
                        {groupedEquipements.reseaux.map((e) => (
                          <SelectItem key={e.id} value={String(e.id)}>
                            {e.hostname || e.ip_address} — {e.ip_address}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    )}
                    {groupedEquipements.autres.length > 0 && (
                      <SelectGroup>
                        <SelectLabel>Autres</SelectLabel>
                        {groupedEquipements.autres.map((e) => (
                          <SelectItem key={e.id} value={String(e.id)}>
                            {e.hostname || e.ip_address} — {e.ip_address}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    )}
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>

          {/* Row 2: Connection details */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col gap-2">
              <Label>Hôte / IP</Label>
              <Input
                value={targetHost}
                onChange={(e) => setTargetHost(e.target.value)}
                placeholder="192.168.1.10"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label>Port</Label>
              <Input
                value={targetPort}
                onChange={(e) => setTargetPort(e.target.value)}
                placeholder={method === "ssh" ? "22" : "5985"}
                type="number"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label>Utilisateur</Label>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={method === "ssh" ? "root" : "DOMAIN\\admin"}
              />
            </div>
          </div>

          {/* Row 3: Auth */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Label>Mot de passe</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            {method === "ssh" ? (
              <div className="flex flex-col gap-2">
                <Label>Clé privée SSH (optionnel)</Label>
                <Textarea
                  value={privateKey}
                  onChange={(e) => setPrivateKey(e.target.value)}
                  placeholder="-----BEGIN RSA PRIVATE KEY-----..."
                  rows={3}
                  className="font-mono text-xs"
                />
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <Label>Transport</Label>
                  <Select value={transport} onValueChange={setTransport}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem value="ntlm">NTLM</SelectItem>
                        <SelectItem value="kerberos">Kerberos</SelectItem>
                        <SelectItem value="basic">Basic</SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-2 items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useSsl}
                      onChange={(e) => {
                        setUseSsl(e.target.checked);
                        if (e.target.checked && targetPort === "5985") setTargetPort("5986");
                        if (!e.target.checked && targetPort === "5986") setTargetPort("5985");
                      }}
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm">HTTPS (port 5986)</span>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Info box */}
          <div className="rounded-lg border p-3 bg-blue-50 dark:bg-blue-950/20 text-sm">
            <p className="font-medium text-blue-700 dark:text-blue-400 mb-1 flex items-center gap-1">
              <Info className="size-4" /> Informations collectées
            </p>
            <p className="text-blue-600 dark:text-blue-500">
              {method === "winrm"
                ? "OS, mises à jour Windows, WSUS, comptes (admin renommé, politique MdP), pare-feu Windows, RDP/NLA, audit policy, journaux d'événements, Defender, stockage"
                : PROFILE_OPTIONS.find((p) => p.value === deviceProfile)?.description
                  ?? "OS, kernel, mises à jour, SSH config, firewall (ufw/iptables), utilisateurs, services, rsyslog, auditd, PAM, antivirus/EDR, stockage"}
            </p>
          </div>

          {/* Launch button */}
          <Button
            onClick={handleLaunch}
            disabled={launching || !selectedEquipementId || !targetHost || !username}
            className="gap-2"
          >
            {launching ? (
              <Loader2 className="animate-spin" data-icon="inline-start" />
            ) : (
              <Play data-icon="inline-start" />
            )}
            Lancer la collecte
          </Button>
        </CardContent>
      </Card>

      {/* Collects history */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="size-5" />
            Historique des collectes
            {collects.length > 0 && (
              <Badge variant="secondary">{collects.length}</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loadingCollects ? (
            <div className="flex flex-col gap-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : collects.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Terminal className="size-10 mx-auto mb-2 opacity-30" />
              <p>Aucune collecte effectuée</p>
              <p className="text-sm">Lancez une collecte SSH ou WinRM pour commencer</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[60px]">#</TableHead>
                    <TableHead>Méthode</TableHead>
                    <TableHead>Cible</TableHead>
                    <TableHead>Hostname</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Durée</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {collects.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="font-mono text-sm">{c.id}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="gap-1">
                          {c.method === "ssh" ? (
                            c.device_profile && c.device_profile !== "linux_server" ? (
                              <Shield className="size-3" />
                            ) : (
                              <Server className="size-3" />
                            )
                          ) : (
                            <Monitor className="size-3" />
                          )}
                          {c.method === "ssh"
                            ? (PROFILE_OPTIONS.find((p) => p.value === c.device_profile)?.label ?? "SSH (Linux)")
                            : (METHOD_LABELS[c.method] || c.method)}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {c.target_host}:{c.target_port}
                      </TableCell>
                      <TableCell className="text-sm">
                        {c.hostname_collected || "—"}
                      </TableCell>
                      <TableCell>
                        {c.status === "running" ? (
                          <Badge className={STATUS_COLORS.running}>
                            <Loader2 className="size-3 animate-spin" />
                            {STATUS_LABELS.running}
                          </Badge>
                        ) : (
                          <Badge className={STATUS_COLORS[c.status]}>
                            {c.status === "success" ? (
                              <CheckCircle2 className="size-3" />
                            ) : (
                              <XCircle className="size-3" />
                            )}
                            {STATUS_LABELS[c.status]}
                          </Badge>
                        )}
                        {c.error_message && (
                          <p className="text-xs text-red-500 mt-1 max-w-[200px] truncate">
                            {c.error_message}
                          </p>
                        )}
                      </TableCell>
                      <TableCell>
                        {c.summary ? (
                          c.summary.compliance_score != null ? (
                            <div className="flex items-center gap-1">
                              <span className="text-sm font-medium">
                                {c.summary.compliance_score}%
                              </span>
                              <Progress
                                value={c.summary.compliance_score}
                                className="w-16 h-2"
                              />
                            </div>
                          ) : c.summary.firewall_rules_count != null ? (
                            <span className="text-sm text-muted-foreground">
                              {c.summary.firewall_rules_count} règles
                            </span>
                          ) : (
                            "—"
                          )
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {c.duration_seconds != null ? `${c.duration_seconds}s` : "—"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(c.created_at).toLocaleDateString("fr-FR", {
                          day: "2-digit",
                          month: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {c.status === "success" && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleViewDetail(c.id)}
                                title="Voir le détail"
                              >
                                <Eye />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openPrefillDialog(c.id)}
                                title="Pré-remplir un audit"
                              >
                                <ClipboardCheck />
                              </Button>
                            </>
                          )}
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-red-500 hover:text-red-700"
                                title="Supprimer"
                              >
                                <Trash2 />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Supprimer cette collecte ?</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Cette action est irréversible. Les données collectées seront définitivement supprimées.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Annuler</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => handleDelete(c.id)}
                                  className="bg-red-600 hover:bg-red-700"
                                >
                                  Supprimer
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

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


// ══════════════════════════════════════════════════════════════
// Detail View Component
// ══════════════════════════════════════════════════════════════
function CollectDetailView({ collect }: { collect: CollectResultRead }) {
  const summary = collect.summary;
  const isWindows = collect.method === "winrm";
  const isOPNsense = summary?.device_profile === "opnsense" || collect.device_profile === "opnsense";
  const isFirewall = isOPNsense || summary?.device_profile === "stormshield" || summary?.device_profile === "fortigate";

  return (
    <div className="flex flex-col gap-6">
      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card>
            <CardContent className="pt-3 text-center">
              {isFirewall ? (
                <Shield className="size-5 mx-auto mb-1 text-muted-foreground" />
              ) : (
                <Cpu className="size-5 mx-auto mb-1 text-muted-foreground" />
              )}
              <p className="text-sm font-medium">{summary.os_name}</p>
              <p className="text-xs text-muted-foreground">{summary.os_version}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-3 text-center">
              <Shield className="size-5 mx-auto mb-1 text-muted-foreground" />
              {summary.compliance_score != null ? (
                <>
                  <p className="text-2xl font-bold">{summary.compliance_score}%</p>
                  <p className="text-xs text-muted-foreground">Conformité</p>
                </>
              ) : summary.firewall_rules_count != null ? (
                <>
                  <p className="text-2xl font-bold">{summary.firewall_rules_count}</p>
                  <p className="text-xs text-muted-foreground">Règles pare-feu</p>
                </>
              ) : (
                <>
                  <p className="text-2xl font-bold">—</p>
                  <p className="text-xs text-muted-foreground">Conformité</p>
                </>
              )}
            </CardContent>
          </Card>
          <Card className="border-green-200">
            <CardContent className="pt-3 text-center">
              <CheckCircle2 className="size-5 mx-auto mb-1 text-green-600" />
              <p className="text-2xl font-bold text-green-600">{summary.compliant}</p>
              <p className="text-xs text-muted-foreground">Conformes</p>
            </CardContent>
          </Card>
          <Card className="border-red-200">
            <CardContent className="pt-3 text-center">
              <XCircle className="size-5 mx-auto mb-1 text-red-600" />
              <p className="text-2xl font-bold text-red-600">{summary.non_compliant}</p>
              <p className="text-xs text-muted-foreground">Non conformes</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="findings" className="w-full">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="findings" className="gap-1">
            <AlertTriangle className="size-3" /> Findings
          </TabsTrigger>
          <TabsTrigger value="system" className="gap-1">
            <Cpu className="size-3" /> Système
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-1">
            <Shield className="size-3" /> Sécurité
          </TabsTrigger>
          <TabsTrigger value="network" className="gap-1">
            <Network className="size-3" /> Réseau
          </TabsTrigger>
          <TabsTrigger value="users" className="gap-1">
            <Users className="size-3" /> Comptes
          </TabsTrigger>
          <TabsTrigger value="storage" className="gap-1">
            <HardDrive className="size-3" /> Stockage
          </TabsTrigger>
        </TabsList>

        {/* Findings tab */}
        <TabsContent value="findings" className="flex flex-col gap-3">
          {collect.findings && collect.findings.length > 0 ? (
            collect.findings.map((f, idx) => (
              <div
                key={idx}
                className="rounded-lg border p-4 bg-red-50 dark:bg-red-950/20"
              >
                <div className="flex items-start gap-3">
                  <XCircle className="size-5 mt-0.5 shrink-0 text-red-600" />
                  <div className="flex-1 flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="destructive">{f.severity}</Badge>
                      <Badge variant="outline">{f.control_ref}</Badge>
                      <span className="font-semibold text-sm">{f.title}</span>
                    </div>
                    <p className="text-sm">{f.description}</p>
                    {f.remediation && (
                      <p className="text-sm italic">
                        <strong>Recommandation :</strong> {f.remediation}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle2 className="size-10 mx-auto mb-2 text-green-500 opacity-50" />
              <p>Aucun finding détecté — tous les contrôles sont conformes</p>
            </div>
          )}
        </TabsContent>

        {/* System tab */}
        <TabsContent value="system">
          <div className="flex flex-col gap-4">
            {collect.os_info && (
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">Informations système</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {isOPNsense ? (
                    <>
                      <InfoRow label="Distribution" value={collect.os_info.distro as string} />
                      <InfoRow label="Version" value={collect.os_info.version as string} />
                      <InfoRow label="Version complète" value={collect.os_info.version_full as string} />
                      <InfoRow label="Kernel" value={collect.os_info.kernel as string} />
                      <InfoRow label="Architecture" value={collect.os_info.arch as string} />
                      <InfoRow label="Uptime" value={collect.os_info.uptime as string} />
                    </>
                  ) : isWindows ? (
                    <>
                      <InfoRow label="OS" value={collect.os_info.caption as string} />
                      <InfoRow label="Version" value={collect.os_info.version as string} />
                      <InfoRow label="Build" value={collect.os_info.build as string} />
                      <InfoRow label="Domaine" value={collect.os_info.domain as string} />
                      <InfoRow
                        label="Joint au domaine"
                        value={collect.os_info.is_domain_joined ? "Oui" : "Non"}
                      />
                    </>
                  ) : (
                    <>
                      <InfoRow label="Distribution" value={collect.os_info.distro as string} />
                      <InfoRow label="Version" value={collect.os_info.version_id as string} />
                      <InfoRow label="Kernel" value={collect.os_info.kernel as string} />
                      <InfoRow label="Architecture" value={collect.os_info.arch as string} />
                      <InfoRow label="Uptime" value={collect.os_info.uptime as string} />
                    </>
                  )}
                </div>
              </div>
            )}

            {collect.updates && (
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">Mises à jour</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {isOPNsense ? (
                    <>
                      <InfoRow
                        label="Mises à jour disponibles"
                        value={collect.updates.updates_available ? "Oui" : "Non"}
                      />
                    </>
                  ) : isWindows ? (
                    <>
                      <InfoRow label="Dernière MàJ" value={collect.updates.last_update_date as string} />
                      <InfoRow
                        label="WSUS configuré"
                        value={collect.updates.wsus_configured ? "Oui" : "Non"}
                      />
                      {collect.updates.wsus_server && (
                        <InfoRow label="Serveur WSUS" value={collect.updates.wsus_server as string} />
                      )}
                    </>
                  ) : (
                    <>
                      <InfoRow
                        label="MàJ en attente"
                        value={String(collect.updates.pending_updates ?? "N/A")}
                      />
                      <InfoRow
                        label="MàJ sécurité"
                        value={String(collect.updates.security_updates ?? "N/A")}
                      />
                      <InfoRow
                        label="MàJ auto"
                        value={collect.updates.auto_updates_configured ? "Oui" : "Non"}
                      />
                    </>
                  )}
                </div>
                {isOPNsense && !!collect.updates.pkg_audit && (
                  <div className="mt-3">
                    <h4 className="text-sm font-medium mb-1">Audit des packages (pkg audit)</h4>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.updates.pkg_audit as string}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {collect.services && (
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">{isOPNsense ? "Services & VPN" : "Services"}</h3>
                {isOPNsense ? (
                  <div className="flex flex-col gap-3">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <InfoRow label="OpenVPN" value={collect.services.openvpn_status as string || "Non configuré"} />
                      <InfoRow label="IPsec" value={collect.services.ipsec_status as string || "Non configuré"} />
                      <InfoRow label="WireGuard" value={collect.services.wireguard_status as string || "Non configuré"} />
                      <InfoRow label="CARP (HA)" value={collect.services.carp_status as string || "Non configuré"} />
                    </div>
                    {!!collect.services.services_list && (
                      <div className="mt-2">
                        <h4 className="text-sm font-medium mb-1">Liste des services</h4>
                        <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                          {collect.services.services_list as string}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                    {isWindows
                      ? (collect.services.services_running as string || "N/A")
                      : (collect.services.running as string || "N/A")}
                  </pre>
                )}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Security tab */}
        <TabsContent value="security">
          <div className="flex flex-col gap-4">
            {collect.security && (
              <>
                {/* Pare-feu */}
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Pare-feu</h3>
                  {isOPNsense ? (
                    <div className="flex flex-col gap-3">
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow label="Moteur" value={collect.security.firewall_engine as string || "pf"} />
                        <InfoRow label="Activé" value={(collect.security.firewall_enabled as boolean) ? "Oui" : "Non"} />
                        <InfoRow label="Nombre de règles" value={String(collect.security.firewall_rules_count ?? 0)} />
                        <InfoRow label="États actifs" value={collect.security.states_count as string || "N/A"} />
                      </div>
                      {!!collect.security.firewall_rules && (
                        <div>
                          <h4 className="text-sm font-medium mb-1">Règles pf</h4>
                          <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                            {collect.security.firewall_rules as string}
                          </pre>
                        </div>
                      )}
                      {!!collect.security.nat_rules && (
                        <div>
                          <h4 className="text-sm font-medium mb-1">Règles NAT</h4>
                          <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                            {collect.security.nat_rules as string}
                          </pre>
                        </div>
                      )}
                      {!!collect.security.aliases && (
                        <div>
                          <h4 className="text-sm font-medium mb-1">Aliases</h4>
                          <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                            {collect.security.aliases as string}
                          </pre>
                        </div>
                      )}
                    </div>
                  ) : isWindows ? (
                    <div className="flex flex-col gap-2">
                      <InfoRow
                        label="Tous profils activés"
                        value={(collect.security.firewall_all_enabled as boolean) ? "Oui" : "Non"}
                      />
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                        {collect.security.firewall_raw as string || "N/A"}
                      </pre>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2">
                      <InfoRow label="Status" value={collect.security.firewall_status as string} />
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                        {collect.security.firewall_details as string || "N/A"}
                      </pre>
                    </div>
                  )}
                </div>

                {/* SSH / RDP / IDS */}
                {isOPNsense ? (
                  <>
                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">SSH</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow label="PermitRootLogin" value={collect.security.ssh_permit_root_login as string} />
                      </div>
                      {!!collect.security.ssh_config_raw && (
                        <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto mt-2">
                          {collect.security.ssh_config_raw as string}
                        </pre>
                      )}
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">IDS / IPS (Suricata)</h3>
                      <InfoRow label="Statut" value={collect.security.suricata_status as string || "Non actif"} />
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Journalisation</h3>
                      <InfoRow label="Syslog distant" value={collect.security.syslog_remote as string || "Non configuré"} />
                    </div>
                  </>
                ) : isWindows ? (
                  <>
                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">RDP</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow
                          label="RDP activé"
                          value={(collect.security.rdp_enabled as boolean) ? "Oui" : "Non"}
                        />
                        <InfoRow
                          label="NLA activé"
                          value={(collect.security.rdp_nla_enabled as boolean) ? "Oui" : "Non"}
                        />
                      </div>
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Antivirus / EDR</h3>
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                        {collect.security.defender_raw as string || "N/A"}
                      </pre>
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Journalisation</h3>
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                        {collect.security.audit_policy as string || "N/A"}
                      </pre>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">SSH</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow label="PermitRootLogin" value={collect.security.ssh_permit_root_login as string} />
                        <InfoRow label="PasswordAuth" value={collect.security.ssh_password_authentication as string} />
                      </div>
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto mt-2">
                        {collect.security.sshd_config_raw as string || "N/A"}
                      </pre>
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Antivirus / EDR</h3>
                      <InfoRow label="Agent détecté" value={collect.security.antivirus_edr as string || "Aucun"} />
                    </div>

                    <div className="rounded-lg border p-4">
                      <h3 className="font-semibold mb-2">Journalisation</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <InfoRow label="rsyslog" value={collect.security.rsyslog_active as string} />
                        <InfoRow label="auditd" value={collect.security.auditd_active as string} />
                      </div>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </TabsContent>

        {/* Network tab */}
        <TabsContent value="network">
          {collect.network && (
            <div className="flex flex-col gap-4">
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">{isOPNsense ? "Interfaces" : "Configuration IP"}</h3>
                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                  {collect.network.interfaces as string ||
                   collect.network.ip_config as string ||
                   collect.network.ip_addresses as string || "N/A"}
                </pre>
              </div>
              {isOPNsense && !!collect.network.routes && (
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Routes</h3>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                    {collect.network.routes as string}
                  </pre>
                </div>
              )}
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">Ports en écoute</h3>
                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                  {collect.network.listening_ports as string || "N/A"}
                </pre>
              </div>
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold mb-2">DNS</h3>
                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                  {collect.network.dns_servers as string ||
                   collect.network.dns as string || "N/A"}
                </pre>
              </div>
            </div>
          )}
        </TabsContent>

        {/* Users tab */}
        <TabsContent value="users">
          {collect.users && (
            <div className="flex flex-col gap-4">
              {isOPNsense ? (
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Comptes système avec shell</h3>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-60 overflow-y-auto">
                    {collect.users.users_with_shell as string || "N/A"}
                  </pre>
                </div>
              ) : isWindows ? (
                <>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Compte Administrateur</h3>
                    <InfoRow
                      label="Renommé"
                      value={(collect.users.admin_renamed as boolean) ? "Oui" : "Non"}
                    />
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto mt-2">
                      {collect.users.admin_account_raw as string || "N/A"}
                    </pre>
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Utilisateurs locaux</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.users.local_users as string || "N/A"}
                    </pre>
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Administrateurs locaux</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.users.local_admins as string || "N/A"}
                    </pre>
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Politique de mot de passe</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                      {(collect.users.password_policy as Record<string, unknown>)?.raw as string || "N/A"}
                    </pre>
                  </div>
                </>
              ) : (
                <>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Utilisateurs avec shell</h3>
                    {Array.isArray(collect.users.users_with_shell) ? (
                      <div className="rounded-md border">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Utilisateur</TableHead>
                              <TableHead>UID</TableHead>
                              <TableHead>Shell</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(collect.users.users_with_shell as { username: string; uid: string; shell: string }[]).map(
                              (u, idx) => (
                                <TableRow key={idx}>
                                  <TableCell className="font-mono text-sm">{u.username}</TableCell>
                                  <TableCell className="text-sm">{u.uid}</TableCell>
                                  <TableCell className="font-mono text-sm">{u.shell}</TableCell>
                                </TableRow>
                              )
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    ) : (
                      <pre className="text-xs bg-muted p-3 rounded">N/A</pre>
                    )}
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Sudoers</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.users.sudoers_raw as string || "N/A"}
                    </pre>
                  </div>
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-2">Dernières connexions</h3>
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-40 overflow-y-auto">
                      {collect.users.last_logins as string || "N/A"}
                    </pre>
                  </div>
                </>
              )}
            </div>
          )}
        </TabsContent>

        {/* Storage tab */}
        <TabsContent value="storage">
          {collect.storage && (
            <div className="flex flex-col gap-4">
              {isOPNsense ? (
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Configuration OPNsense</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <InfoRow label="Taille config.xml" value={collect.storage.config_xml_size as string || "N/A"} />
                    <InfoRow label="Sauvegardes" value={`${collect.storage.config_backup_count ?? 0} fichier(s)`} />
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border p-4">
                  <h3 className="font-semibold mb-2">Utilisation disque</h3>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    {collect.storage.disk_usage as string || "N/A"}
                  </pre>
                </div>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}


// ── Info row helper ──
function InfoRow({ label, value }: { label: string; value: string | undefined | null }) {
  return (
    <div className="flex justify-between py-1 border-b border-dashed last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-right max-w-[60%] truncate">{value || "N/A"}</span>
    </div>
  );
}
