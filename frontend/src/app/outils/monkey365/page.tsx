"use client";

import { useCallback, useRef } from "react";
import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Play,
  Loader2,
  AlertTriangle,
  ArrowLeft,
  X,
  Plus,
  FileText,
  Copy,
  Check,
  Smartphone,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

import { toolsApi, entreprisesApi, auditsApi } from "@/services/api";
import type { Audit, Entreprise, Monkey365Config, Monkey365ScanCreate, Monkey365ScanResultSummary, Monkey365ScanResultDetail, Monkey365ScanLogs, Monkey365ImportResult } from "@/types/api";

export default function Monkey365Page() {
  const [activeTab, setActiveTab] = useState("launch");
  const [loading, setLoading] = useState(false);
  const [launching, setLaunching] = useState(false);

  // Entreprises state — persisted in sessionStorage so selection survives navigation
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [selectedEntrepriseId, setSelectedEntrepriseIdState] = useState<string>("");
  const setSelectedEntrepriseId = (id: string) => {
    setSelectedEntrepriseIdState(id);
    if (typeof window !== "undefined") {
      sessionStorage.setItem("monkey365_entreprise", id);
    }
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedEntrepriseId = sessionStorage.getItem("monkey365_entreprise");
    if (storedEntrepriseId) {
      setSelectedEntrepriseIdState(storedEntrepriseId);
    }
  }, []);

  // PowerShell logs state
  const [scanLogs, setScanLogs] = useState<Monkey365ScanLogs | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Simplified config
  const [spoSites, setSpoSites] = useState<string[]>([]);
  const [exportFormats, setExportFormats] = useState<string[]>(["JSON", "HTML"]);
  const [siteInput, setSiteInput] = useState("");
  const [deviceCode, setDeviceCode] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [activeDeviceCode, setActiveDeviceCode] = useState<{ url: string; code: string } | null>(null);

  const [scans, setScans] = useState<Monkey365ScanResultSummary[]>([]);
  const [selectedScan, setSelectedScan] = useState<Monkey365ScanResultDetail | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [openingReport, setOpeningReport] = useState(false);

  // Import vers audit
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importAudits, setImportAudits] = useState<Audit[]>([]);
  const [importAuditId, setImportAuditId] = useState<string>("");
  const [importing, setImporting] = useState(false);

  function formatDuration(seconds: number | null | undefined): string {
    if (!seconds) return "-";
    if (seconds < 60) return `${seconds}s`;
    const min = Math.floor(seconds / 60);
    const sec = seconds % 60;
    return `${min}min ${sec}s`;
  }

  // SQLite returns naive datetimes (no Z suffix). JS treats those as local time
  // instead of UTC, causing a -1h offset in UTC+1. Force UTC interpretation.
  function parseDate(dateStr: string | null): Date | null {
    if (!dateStr) return null;
    const iso = dateStr.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(dateStr)
      ? dateStr
      : dateStr + "Z";
    return new Date(iso);
  }

  function formatTimestamp(dateStr: string | null): string {
    const d = parseDate(dateStr);
    if (!d) return "-";
    return d.toLocaleTimeString("fr-FR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function formatDate(dateStr: string | null): string {
    const d = parseDate(dateStr);
    if (!d) return "-";
    return d.toLocaleString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case "success":
        return <Badge variant="default">Succès</Badge>;
      case "failed":
        return <Badge variant="destructive">Échec</Badge>;
      case "running":
        return <Badge className="bg-blue-500"><Loader2 className="size-3 animate-spin" />En cours</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  }

  const loadScans = useCallback(async () => {
    if (!selectedEntrepriseId) return;
    setLoading(true);
    try {
      const data = await toolsApi.listMonkey365Scans(parseInt(selectedEntrepriseId, 10));
      setScans(data);
    } catch {
      toast.error("Erreur lors du chargement des scans");
    } finally {
      setLoading(false);
    }
  }, [selectedEntrepriseId]);

  const loadScanDetail = async (scanId: number) => {
    try {
      const detail = await toolsApi.getMonkey365ScanDetail(scanId);
      setSelectedScan(detail);
      if (detail.status === "running") {
        // parseDate appends Z so naive UTC timestamps are correctly interpreted
        const created = (parseDate(detail.created_at) ?? new Date()).getTime();
        setElapsedSeconds(Math.floor((Date.now() - created) / 1000));
      } else {
        setElapsedSeconds(detail.duration_seconds || 0);
        // Polling only runs for running scans, so fetch logs eagerly for finished ones
        const logs = await toolsApi.getMonkey365ScanLogs(scanId).catch(() => null);
        if (logs !== null) {
          setScanLogs(logs);
        }
      }
    } catch {
      toast.error("Erreur lors du chargement des détails");
    }
  };

  // Auto-load scans when the selected enterprise changes
  useEffect(() => {
    loadScans();
  }, [loadScans]);

  // Elapsed-seconds ticker — recreate only when id or status changes (not every poll)
  useEffect(() => {
    if (!selectedScan || selectedScan.status !== "running") return;
    const ticker = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(ticker);
  }, [selectedScan?.id, selectedScan?.status]);

  // Clear logs when selected scan changes
  useEffect(() => {
    if (!selectedScan) { setScanLogs(null); }
  }, [selectedScan?.id]);

  // Track the latest device code from logs for the sticky banner
  useEffect(() => {
    if (!scanLogs) { setActiveDeviceCode(null); return; }
    const dcPattern = /open the page (https?:\/\/[^\s]+) and enter the code ([A-Z0-9]{4,12}) to/i;
    const dcFallback = /(https?:\/\/(?:microsoft\.com|aka\.ms|login\.microsoftonline\.com)\/device\S*)\s.*?(?:code[:\s]+)([A-Z0-9\-]{4,12})/i;
    let found: { url: string; code: string } | null = null;
    for (const raw of scanLogs.lines) {
      const line = raw.replace(/\x1B\[[0-9;]*[a-zA-Z]/g, "");
      const m = dcPattern.exec(line) || dcFallback.exec(line);
      if (m) found = { url: m[1], code: m[2] };
    }
    setActiveDeviceCode(found);
  }, [scanLogs]);

  // Centralized per-scan poll: fetch detail + logs together every 2s while running
  useEffect(() => {
    if (!selectedScan?.id || selectedScan.status !== "running") return;
    const scanId = selectedScan.id;
    const poll = async () => {
      try {
        const [updated, logs] = await Promise.all([
          toolsApi.getMonkey365ScanDetail(scanId),
          toolsApi.getMonkey365ScanLogs(scanId).catch(() => null),
        ]);
        setSelectedScan(updated);
        if (logs !== null) {
          setScanLogs(logs);
          logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
        if (updated.status !== "running") {
          setElapsedSeconds(updated.duration_seconds || 0);
        }
      } catch {
        // polling error silently handled
      }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [selectedScan?.id, selectedScan?.status]);

  // Slow background poll to keep scans list fresh without rapid teardown/recreation
  useEffect(() => {
    const interval = setInterval(loadScans, 15000);
    return () => clearInterval(interval);
  }, [loadScans]);

  useEffect(() => {
    const loadEntreprises = async () => {
      try {
        const data = await entreprisesApi.list();
        setEntreprises(Array.isArray(data) ? data : data.items || []);
      } catch (err) {
        toast.error("Impossible de charger les entreprises");
      }
    };
    loadEntreprises();
  }, []);

  const handleAddSite = () => {
    if (!siteInput.trim()) return;
    if (!spoSites.includes(siteInput.trim())) {
      setSpoSites([...spoSites, siteInput.trim()]);
    }
    setSiteInput("");
  };

  const handleRemoveSite = (tag: string) => {
    setSpoSites(spoSites.filter((t) => t !== tag));
  };

  const handleToggleExportFormat = (format: string, checked: boolean) => {
    if (format === "JSON") return;
    if (checked) {
      setExportFormats([...exportFormats, format]);
    } else {
      setExportFormats(exportFormats.filter((f) => f !== format));
    }
  };

  const generatePSPreview = () => {
    const params = [
      `$param = @{`,
      `    Instance        = 'Microsoft365';`,
      `    Collect         = @('ExchangeOnline', 'MicrosoftTeams', 'Purview', 'SharePointOnline', 'AdminPortal');`,
      `    IncludeEntraID  = $true;`,
      `    ExportTo        = @('${exportFormats.join("', '")}');`,
    ];

    if (deviceCode) {
      params.push(`    DeviceCode      = $true;`);
    } else {
      params.push(`    PromptBehavior  = 'SelectAccount';`);
      params.push(`    ForceMSALDesktop = $true;`);
    }

    if (spoSites.length > 0) {
      params.push(`    SpoSites        = @('${spoSites.join("', '")}')`);
    }

    params.push(`}`);
    params.push(`Invoke-Monkey365 @param`);

    return params.join("\n");
  };

  const handleLaunch = async () => {
    if (!selectedEntrepriseId) {
      toast.error("Veuillez sélectionner une entreprise");
      return;
    }

    setLaunching(true);
    try {
      const config: Monkey365Config = {
        spo_sites: spoSites.length > 0 ? spoSites : undefined,
        export_to: exportFormats,
        device_code: deviceCode || undefined,
      };

      const payload: Monkey365ScanCreate = {
        entreprise_id: parseInt(selectedEntrepriseId, 10),
        config,
      };

      await toolsApi.launchMonkey365Scan(payload);
      toast.success("Scan Monkey365 lancé en arrière-plan");
      
      setActiveTab("history");
      await loadScans();
    } catch {
      toast.error("Erreur lors du lancement du scan");
    } finally {
      setLaunching(false);
    }
  };

  const handleOpenReport = async (scanId: number) => {
    setOpeningReport(true);
    try {
      await toolsApi.openMonkey365Report(scanId);
    } catch {
      toast.error("Rapport HTML introuvable ou indisponible");
    } finally {
      setOpeningReport(false);
    }
  };

  const handleCancelScan = async (scanId: number) => {
    try {
      const updated = await toolsApi.cancelMonkey365Scan(scanId);
      setSelectedScan(prev => prev?.id === scanId ? { ...prev, ...updated } : prev);
      setScans(prev => prev.map(s => s.id === scanId ? { ...s, status: updated.status } : s));
      toast.success("Scan annulé");
    } catch {
      toast.error("Impossible d'annuler le scan");
    }
  };

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  const confirmDeleteScan = (scanId: number) => {
    setPendingDeleteId(scanId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteScan = async (scanId: number) => {
    setDeleteDialogOpen(false);
    setDeletingId(scanId);
    try {
      await toolsApi.deleteMonkey365Scan(scanId);
      toast.success("Scan supprimé avec succès");
      setSelectedScan(null);
      await loadScans();
    } catch {
      toast.error("Erreur lors de la suppression du scan");
    } finally {
      setDeletingId(null);
    }
  };

  const handleOpenImportDialog = async () => {
    setImportAuditId("");
    setImportDialogOpen(true);
    try {
      const response = await auditsApi.list(1, 100, selectedScan?.entreprise_id);
      setImportAudits(response.items ?? []);
    } catch {
      toast.error("Impossible de charger les audits");
    }
  };

  const handleConfirmImport = async () => {
    if (!selectedScan || !importAuditId) return;
    setImporting(true);
    try {
      const result: Monkey365ImportResult = await toolsApi.importMonkey365ToAudit(
        selectedScan.id,
        parseInt(importAuditId, 10),
      );
      setImportDialogOpen(false);
      toast.success(
        `Import réussi — ${result.controls_mapped}/${result.controls_total} contrôles mappés (campagne #${result.campaign_id})`,
      );
    } catch {
      toast.error("Erreur lors de l'import vers l'audit");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/outils">
              <Button variant="outline" size="icon">
                <ArrowLeft />
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Monkey365 — Audit Microsoft 365</h1>
          </div>
        </div>

        <Alert className="mb-6 border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800">
          <AlertTriangle className="size-4 text-blue-600 dark:text-blue-400" />
          <AlertDescription className="text-blue-800 dark:text-blue-300">
            Collecte des 5 modules M365 standard. Auth interactive (navigateur) ou Device Code (code appareil).
          </AlertDescription>
        </Alert>

        {/* Enterprise selector — always visible, persisted across navigation */}
        <Card className="mb-4">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-4">
              <Label className="whitespace-nowrap">Entreprise *</Label>
              <Select value={selectedEntrepriseId} onValueChange={setSelectedEntrepriseId}>
                <SelectTrigger className="max-w-sm">
                  <SelectValue placeholder="Sélectionner une entreprise" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {entreprises.map((ent) => (
                      <SelectItem key={ent.id} value={ent.id.toString()}>
                        {ent.nom}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="launch">Lancer un scan</TabsTrigger>
            <TabsTrigger value="history">Historique</TabsTrigger>
            <TabsTrigger value="details">Détails</TabsTrigger>
          </TabsList>

          <TabsContent value="launch" className="flex flex-col gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Configuration du scan</CardTitle>
                <CardDescription>
                  Les paramètres sont fixés pour le cas d'usage standard (99% du temps)
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-6">
                {/* SharePoint Sites */}
                <div className="flex flex-col gap-2">
                  <Label>Sites SharePoint (optionnel)</Label>
                  <div className="flex gap-2">
                    <Input
                      placeholder="https://domain.sharepoint.com"
                      value={siteInput}
                      onChange={(e) => setSiteInput(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && handleAddSite()}
                    />
                    <Button onClick={handleAddSite} size="sm" variant="outline">
                      <Plus />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {spoSites.map((site) => (
                      <Badge key={site} variant="secondary" className="cursor-pointer">
                        {site}
                        <X
                          className="size-3 ml-1 hover:text-destructive"
                          onClick={() => handleRemoveSite(site)}
                        />
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Export Formats */}
                <div className="flex flex-col gap-3">
                  <Label>Formats d'export</Label>
                  <div className="flex flex-col gap-2">
                    {["JSON", "HTML", "CSV"].map((format) => (
                      <div key={format} className="flex items-center space-x-2">
                        <Checkbox
                          checked={exportFormats.includes(format)}
                          disabled={format === "JSON"}
                          onCheckedChange={(checked) =>
                            handleToggleExportFormat(format, checked as boolean)
                          }
                        />
                        <label className="text-sm">
                          {format}
                          {format === "JSON" && <span className="text-xs text-gray-500"> (toujours inclus)</span>}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Device Code toggle */}
                <div className="flex items-center justify-between rounded border p-4">
                  <div className="flex items-center gap-3">
                    <Smartphone className="size-5 text-muted-foreground" />
                    <div>
                      <Label className="text-sm font-medium">Mode Device Code</Label>
                      <p className="text-xs text-muted-foreground">
                        Authentification via code appareil — pour les sessions sans navigateur
                      </p>
                    </div>
                  </div>
                  <Switch checked={deviceCode} onCheckedChange={setDeviceCode} />
                </div>

                {/* Fixed Parameters Info */}
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded border border-gray-200 dark:border-gray-800 flex flex-col gap-2 text-sm">
                  <p className="font-semibold">Paramètres fixés :</p>
                  <ul className="list-disc list-inside flex flex-col gap-1 text-gray-700 dark:text-gray-300">
                    <li>Instance: Microsoft365</li>
                    <li>Authentification: {deviceCode ? "DEVICE CODE (code appareil)" : "INTERACTIVE (navigateur)"}</li>
                    <li>Modules: ExchangeOnline, MicrosoftTeams, Purview, SharePointOnline, AdminPortal</li>
                    <li>IncludeEntraID: $true</li>
                    {!deviceCode && <li>ForceMSALDesktop: $true (MSAL interactive desktop auth)</li>}
                  </ul>
                </div>

                {/* PowerShell Preview */}
                <div className="flex flex-col gap-2">
                  <Label>Aperçu PowerShell</Label>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded overflow-auto text-xs max-h-48">
                    {generatePSPreview()}
                  </pre>
                </div>

                {/* Launch Button */}
                <Button
                  onClick={handleLaunch}
                  disabled={launching || !selectedEntrepriseId}
                  className="w-full"
                  size="lg"
                >
                  {launching ? (
                    <>
                      <Loader2 className="animate-spin" data-icon="inline-start" />
                      Lancement en cours...
                    </>
                  ) : (
                    <>
                      <Play data-icon="inline-start" />
                      Lancer le scan
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history" className="flex flex-col gap-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Historique des scans</CardTitle>
                  </div>
                  <Button
                    onClick={() => loadScans()}
                    disabled={loading || !selectedEntrepriseId}
                    size="sm"
                    variant="outline"
                  >
                    <RefreshCw className={loading ? "animate-spin" : ""} />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {!selectedEntrepriseId ? (
                  <p className="text-gray-500 text-center py-8">Sélectionnez une entreprise pour voir l'historique</p>
                ) : scans.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">Aucun scan pour cette entreprise</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID Scan</TableHead>
                        <TableHead>Statut</TableHead>
                        <TableHead>Findings</TableHead>
                        <TableHead>Créé</TableHead>
                        <TableHead>Durée</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {scans.map((scan) => (
                        <TableRow
                          key={scan.id}
                          onClick={() => { loadScanDetail(scan.id); setActiveTab("details"); }}
                          className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900"
                        >
                          <TableCell className="font-mono text-xs">{scan.scan_id.slice(0, 8)}</TableCell>
                          <TableCell>{getStatusBadge(scan.status)}</TableCell>
                          <TableCell>{scan.findings_count ?? "-"}</TableCell>
                          <TableCell>{formatDate(scan.created_at)}</TableCell>
                          <TableCell>{formatDuration(scan.duration_seconds)}</TableCell>
                          <TableCell>
                             <div className="flex gap-2">
                            <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); loadScanDetail(scan.id); setActiveTab("details"); }}>
                              Détails
                            </Button>
                               <Button
                                 size="sm"
                                 variant="ghost"
                                 onClick={(e) => {
                                   e.stopPropagation();
                                   confirmDeleteScan(scan.id);
                                 }}
                                 disabled={deletingId === scan.id}
                                 className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                               >
                                 {deletingId === scan.id ? <Loader2 className="size-4 animate-spin" /> : <X className="size-4" />}
                               </Button>
                             </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="details" className="flex flex-col gap-4">
            {!selectedScan ? (
              <Card>
                <CardContent className="py-8">
                  <p className="text-gray-500 text-center">Sélectionnez un scan dans l'historique</p>
                </CardContent>
              </Card>
            ) : (
              <>
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Détails du scan</CardTitle>
                      <div className="flex gap-2">
                        {selectedScan.status === "success" && (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleOpenReport(selectedScan.id)}
                              disabled={openingReport}
                            >
                              {openingReport ? (
                                <Loader2 className="animate-spin" data-icon="inline-start" />
                              ) : (
                                <FileText data-icon="inline-start" />
                              )}
                              Rapport HTML
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={handleOpenImportDialog}
                            >
                              <Plus data-icon="inline-start" />
                              Ajouter à l'audit
                            </Button>
                          </>
                        )}
                        {selectedScan.status === "running" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleCancelScan(selectedScan.id)}
                          >
                            <X data-icon="inline-start" />
                            Forcer l'arrêt
                          </Button>
                        )}
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => confirmDeleteScan(selectedScan.id)}
                        disabled={deletingId === selectedScan.id}
                      >
                        {deletingId === selectedScan.id ? (
                          <>
                            <Loader2 className="animate-spin" data-icon="inline-start" />
                            Suppression...
                          </>
                        ) : (
                          <>
                            <X data-icon="inline-start" />
                            Supprimer
                          </>
                        )}
                      </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">ID Scan</p>
                        <p className="font-mono text-sm">{selectedScan.scan_id}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Statut</p>
                        <div>{getStatusBadge(selectedScan.status)}</div>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Créé</p>
                        <p className="text-sm">{formatDate(selectedScan.created_at)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Durée</p>
                        <p className="text-sm">
                          {selectedScan.status === "running"
                            ? `${formatDuration(elapsedSeconds)} (en cours...)`
                            : formatDuration(selectedScan.duration_seconds)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Findings</p>
                        <p className="text-sm">{selectedScan.findings_count ?? "-"}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Chemin de sortie</p>
                        <p className="text-xs font-mono text-gray-600 dark:text-gray-400 break-all">
                          {selectedScan.output_path || "-"}
                        </p>
                      </div>
                    </div>


                    {selectedScan.error_message && (
                      <Alert variant="destructive">
                        <AlertTriangle className="size-4" />
                        <AlertDescription>{selectedScan.error_message}</AlertDescription>
                      </Alert>
                    )}

                    {selectedScan.config_snapshot && (
                      <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded">
                        <p className="font-semibold text-sm mb-2">Configuration</p>
                        <pre className="text-xs overflow-auto max-h-32 text-gray-700 dark:text-gray-300">
                          {JSON.stringify(selectedScan.config_snapshot, null, 2)}
                        </pre>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* PowerShell logs */}
                <Card>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">Logs PowerShell</CardTitle>
                      {selectedScan.status === "running" && (
                        <Badge className="bg-blue-500">
                          <Loader2 className="size-3 animate-spin" />
                          En direct
                        </Badge>
                      )}
                      {scanLogs && scanLogs.total_lines > 500 && (
                        <span className="text-xs text-gray-500">
                          Affichage des 500 dernières lignes sur {scanLogs.total_lines}
                        </span>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    {!scanLogs || scanLogs.lines.length === 0 ? (
                      <p className="text-xs text-gray-500 py-4 text-center">
                        {selectedScan.status === "running"
                          ? "En attente des premiers logs PowerShell…"
                          : "Aucun log disponible"}
                      </p>
                    ) : (
                      <div className="bg-gray-950 rounded p-3 max-h-96 overflow-y-auto font-mono text-xs relative">
                        {activeDeviceCode && (
                          <div className="sticky top-0 z-10 flex items-center justify-between gap-3 rounded bg-indigo-600 px-3 py-2 mb-2 text-white shadow-lg">
                            <div className="flex items-center gap-3 min-w-0">
                              <Smartphone className="size-5 shrink-0" />
                              <a href={activeDeviceCode.url} target="_blank" rel="noopener noreferrer" className="text-indigo-200 underline text-xs truncate">
                                {activeDeviceCode.url}
                              </a>
                              <span className="font-mono text-2xl font-bold tracking-wider shrink-0">{activeDeviceCode.code}</span>
                            </div>
                            <button
                              onClick={async () => {
                                await navigator.clipboard.writeText(activeDeviceCode.code);
                                setCopiedCode(activeDeviceCode.code);
                                toast.success("Code copié !");
                                setTimeout(() => setCopiedCode(null), 2000);
                              }}
                              className="shrink-0 flex items-center gap-1 rounded bg-white/20 hover:bg-white/30 text-white text-xs px-3 py-1.5 font-medium"
                            >
                              {copiedCode === activeDeviceCode.code ? <Check className="size-3" /> : <Copy className="size-3" />}
                              {copiedCode === activeDeviceCode.code ? "Copié !" : "Copier le code"}
                            </button>
                          </div>
                        )}
                        {scanLogs.lines.map((line, i) => {
                          // Strip leftover ANSI escape codes
                          const clean = line.replace(/\x1B\[[0-9;]*[a-zA-Z]/g, "");
                          // Detect device code: MSAL "open the page ... enter the code ..." pattern
                          const dcMatch = clean.match(/open the page (https?:\/\/[^\s]+) and enter the code ([A-Z0-9]{4,12}) to/i)
                            // Also match older "use ... devicelogin ... code XXX" pattern
                            || clean.match(/(https?:\/\/(?:microsoft\.com|aka\.ms|login\.microsoftonline\.com)\/device\S*)\s.*?(?:code[:\s]+)([A-Z0-9\-]{4,12})/i);
                          if (dcMatch) {
                            const dcUrl = dcMatch[1];
                            const codeValue = dcMatch[2];
                            return (
                              <div key={i} className="flex items-center gap-2 rounded bg-indigo-950/60 border border-indigo-500/30 px-2 py-1.5 my-1">
                                <div className="flex-1 text-indigo-200 leading-5 whitespace-pre-wrap break-all">
                                  <span>{clean.slice(0, clean.indexOf(codeValue))}</span>
                                  <span className="text-xl font-bold text-white tracking-wider">{codeValue}</span>
                                  <span>{clean.slice(clean.indexOf(codeValue) + codeValue.length)}</span>
                                </div>
                                <button
                                  onClick={async () => {
                                    await navigator.clipboard.writeText(codeValue);
                                    setCopiedCode(codeValue);
                                    toast.success("Code copié !");
                                    setTimeout(() => setCopiedCode(null), 2000);
                                  }}
                                  className="shrink-0 flex items-center gap-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-2 py-1"
                                >
                                  {copiedCode === codeValue ? <Check className="size-3" /> : <Copy className="size-3" />}
                                  {copiedCode === codeValue ? "Copié" : "Copier"}
                                </button>
                              </div>
                            );
                          }
                          return (
                            <div key={i} className="text-gray-200 leading-5 whitespace-pre-wrap break-all">
                              {clean || "\u00a0"}
                            </div>
                          );
                        })}
                        <div ref={logsEndRef} />
                      </div>
                    )}
                  </CardContent>
                </Card>
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>

      {/* Dialog — importer vers un audit */}
      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Ajouter à un audit</DialogTitle>
            <DialogDescription>
              Sélectionnez l'audit dans lequel importer ce scan Monkey365.
              Une campagne CIS-M365-V5 sera créée automatiquement avec les résultats parsés.
            </DialogDescription>
          </DialogHeader>

          <div className="py-2">
            {importAudits.length === 0 ? (
              <p className="text-sm text-gray-500">Aucun audit disponible pour cette entreprise.</p>
            ) : (
              <Select value={importAuditId} onValueChange={setImportAuditId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un audit…" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {importAudits.map((audit) => (
                      <SelectItem key={audit.id} value={audit.id.toString()}>
                        {audit.nom_projet}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setImportDialogOpen(false)} disabled={importing}>
              Annuler
            </Button>
            <Button onClick={handleConfirmImport} disabled={!importAuditId || importing}>
              {importing ? (
                <>
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                  Import en cours…
                </>
              ) : (
                "Importer"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer ce scan ?</AlertDialogTitle>
            <AlertDialogDescription>
              Ce scan et ses résultats seront définitivement supprimés. Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => pendingDeleteId && handleDeleteScan(pendingDeleteId)}>
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
