"use client";

import { useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Play,
  Loader2,
  AlertTriangle,
  ArrowLeft,
  X,
  Plus,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";

import { toolsApi, entreprisesApi } from "@/services/api";
import type { Entreprise, Monkey365Config, Monkey365ScanCreate, Monkey365ScanResultSummary, Monkey365ScanResultDetail } from "@/types/api";

export default function Monkey365Page() {
  const [activeTab, setActiveTab] = useState("launch");
  const [loading, setLoading] = useState(false);
  const [launching, setLaunching] = useState(false);

  // Entreprises state
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [selectedEntrepriseId, setSelectedEntrepriseId] = useState<string>("");

  // Simplified config - only 2 fields
  const [spoSites, setSpoSites] = useState<string[]>([]);
  const [exportFormats, setExportFormats] = useState<string[]>(["JSON", "HTML"]);
  const [siteInput, setSiteInput] = useState("");

  const [scans, setScans] = useState<Monkey365ScanResultSummary[]>([]);
  const [selectedScan, setSelectedScan] = useState<Monkey365ScanResultDetail | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  function formatDuration(seconds: number | null | undefined): string {
    if (!seconds) return "-";
    if (seconds < 60) return `${seconds}s`;
    const min = Math.floor(seconds / 60);
    const sec = seconds % 60;
    return `${min}min ${sec}s`;
  }

  function formatTimestamp(dateStr: string | null): string {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleTimeString("fr-FR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("fr-FR", {
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
        return <Badge className="bg-blue-500"><Loader2 className="h-3 w-3 mr-1 animate-spin" />En cours</Badge>;
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
    } catch (err) {
      console.error("Failed to load scans:", err);
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
        const created = new Date(detail.created_at).getTime();
        const now = Date.now();
        setElapsedSeconds(Math.floor((now - created) / 1000));
      } else {
        setElapsedSeconds(detail.duration_seconds || 0);
      }
    } catch (err) {
      console.error("Failed to load scan detail:", err);
      toast.error("Erreur lors du chargement des détails");
    }
  };

  useEffect(() => {
    if (selectedScan && selectedScan.status === "running") {
      const interval = setInterval(async () => {
        try {
          const updated = await toolsApi.getMonkey365ScanDetail(selectedScan.id);
          setSelectedScan(updated);
          
          if (updated.status !== "running") {
            clearInterval(interval);
            setElapsedSeconds(updated.duration_seconds || 0);
          }
        } catch (err) {
          console.error("Failed to poll scan status:", err);
        }
      }, 2000);
      
      return () => clearInterval(interval);
    }
  }, [selectedScan]);

  useEffect(() => {
    if (selectedScan && selectedScan.status === "running") {
      const ticker = setInterval(() => {
        setElapsedSeconds(prev => prev + 1);
      }, 1000);
      
      return () => clearInterval(ticker);
    }
  }, [selectedScan]);

  useEffect(() => {
    if (scans.some(s => s.status === "running")) {
      const interval = setInterval(loadScans, 5000);
      return () => clearInterval(interval);
    }
  }, [scans, loadScans]);

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
      `    PromptBehavior  = 'SelectAccount';`,
      `    IncludeEntraID  = $true;`,
      `    ForceMSALDesktop = $true;`,
      `    ExportTo        = @('${exportFormats.join("', '")}');`,
    ];

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
      };

      const payload: Monkey365ScanCreate = {
        entreprise_id: parseInt(selectedEntrepriseId, 10),
        config,
      };

      await toolsApi.launchMonkey365Scan(payload);
      toast.success("Scan Monkey365 lancé en arrière-plan");
      
      setActiveTab("history");
      await loadScans();
    } catch (err) {
      console.error("Failed to launch scan:", err);
      toast.error("Erreur lors du lancement du scan");
    } finally {
      setLaunching(false);
    }
  };

  const handleDeleteScan = async (scanId: number) => {
    if (!confirm("Êtes-vous sûr de vouloir supprimer ce scan ?")) return;
    
    setDeletingId(scanId);
    try {
      await toolsApi.deleteMonkey365Scan(scanId);
      toast.success("Scan supprimé avec succès");
      setSelectedScan(null);
      await loadScans();
    } catch (err) {
      console.error("Failed to delete scan:", err);
      toast.error("Erreur lors de la suppression du scan");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/outils">
              <Button variant="outline" size="icon">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Monkey365 — Audit Microsoft 365</h1>
          </div>
        </div>

        <Alert className="mb-6 border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800">
          <AlertTriangle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          <AlertDescription className="text-blue-800 dark:text-blue-300">
            Mode simplifié : INTERACTIVE auth (navigateur), collecte des 5 modules M365 standard, export JSON + HTML.
          </AlertDescription>
        </Alert>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="launch">Lancer un scan</TabsTrigger>
            <TabsTrigger value="history">Historique</TabsTrigger>
            <TabsTrigger value="details">Détails</TabsTrigger>
          </TabsList>

          <TabsContent value="launch" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Configuration du scan</CardTitle>
                <CardDescription>
                  Les paramètres sont fixés pour le cas d'usage standard (99% du temps)
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Entreprise Selection */}
                <div className="space-y-2">
                  <Label>Entreprise *</Label>
                  <Select value={selectedEntrepriseId} onValueChange={setSelectedEntrepriseId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner une entreprise" />
                    </SelectTrigger>
                    <SelectContent>
                      {entreprises.map((ent) => (
                        <SelectItem key={ent.id} value={ent.id.toString()}>
                          {ent.nom}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* SharePoint Sites */}
                <div className="space-y-2">
                  <Label>Sites SharePoint (optionnel)</Label>
                  <div className="flex gap-2">
                    <Input
                      placeholder="https://domain.sharepoint.com"
                      value={siteInput}
                      onChange={(e) => setSiteInput(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && handleAddSite()}
                    />
                    <Button onClick={handleAddSite} size="sm" variant="outline">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {spoSites.map((site) => (
                      <Badge key={site} variant="secondary" className="cursor-pointer">
                        {site}
                        <X
                          className="h-3 w-3 ml-1 hover:text-destructive"
                          onClick={() => handleRemoveSite(site)}
                        />
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Export Formats */}
                <div className="space-y-3">
                  <Label>Formats d'export</Label>
                  <div className="space-y-2">
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

                {/* Fixed Parameters Info */}
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded border border-gray-200 dark:border-gray-800 space-y-2 text-sm">
                  <p className="font-semibold">Paramètres fixés :</p>
                  <ul className="list-disc list-inside space-y-1 text-gray-700 dark:text-gray-300">
                    <li>Instance: Microsoft365</li>
                    <li>Authentification: INTERACTIVE (navigateur)</li>
                    <li>Modules: ExchangeOnline, MicrosoftTeams, Purview, SharePointOnline, AdminPortal</li>
                    <li>IncludeEntraID: $true</li>
                    <li>ForceMSALDesktop: $true (MSAL interactive desktop auth)</li>
                  </ul>
                </div>

                {/* PowerShell Preview */}
                <div className="space-y-2">
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
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Lancement en cours...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Lancer le scan
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history" className="space-y-4">
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
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
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
                          onClick={() => loadScanDetail(scan.id)}
                          className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900"
                        >
                          <TableCell className="font-mono text-xs">{scan.scan_id.slice(0, 8)}</TableCell>
                          <TableCell>{getStatusBadge(scan.status)}</TableCell>
                          <TableCell>{scan.findings_count ?? "-"}</TableCell>
                          <TableCell>{formatDate(scan.created_at)}</TableCell>
                          <TableCell>{formatDuration(scan.duration_seconds)}</TableCell>
                          <TableCell>
                             <div className="flex gap-2">
                            <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); loadScanDetail(scan.id); }}>
                              Détails
                            </Button>
                               <Button
                                 size="sm"
                                 variant="ghost"
                                 onClick={(e) => {
                                   e.stopPropagation();
                                   handleDeleteScan(scan.id);
                                 }}
                                 disabled={deletingId === scan.id}
                                 className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                               >
                                 {deletingId === scan.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
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

          <TabsContent value="details" className="space-y-4">
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
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDeleteScan(selectedScan.id)}
                        disabled={deletingId === selectedScan.id}
                      >
                        {deletingId === selectedScan.id ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Suppression...
                          </>
                        ) : (
                          <>
                            <X className="h-4 w-4 mr-2" />
                            Supprimer
                          </>
                        )}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
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


                    {selectedScan.auth_mode && (
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">Mode d'authentification</p>
                          <p className="text-sm">{selectedScan.auth_mode}</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">MSAL Desktop Auth</p>
                          <p className="text-sm flex items-center gap-2">
                            <span className={selectedScan.force_msal_desktop ? "text-green-600" : "text-gray-500"}>
                              {selectedScan.force_msal_desktop ? "✓ Activé" : "✗ Désactivé"}
                            </span>
                          </p>
                        </div>
                      </div>
                    )}

                    {selectedScan.error_message && (
                      <Alert variant="destructive">
                        <AlertTriangle className="h-4 w-4" />
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
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
