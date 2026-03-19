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
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";

import { toolsApi, entreprisesApi } from "@/services/api";
import type { Entreprise, Monkey365Config, Monkey365ScanCreate, Monkey365ScanResultSummary, Monkey365ScanResultDetail, Monkey365AuthMode } from "@/types/api";

export default function Monkey365Page() {
  const [activeTab, setActiveTab] = useState("launch");
  const [loading, setLoading] = useState(false);
  const [launching, setLaunching] = useState(false);




  // Entreprises state
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [selectedEntrepriseId, setSelectedEntrepriseId] = useState<string>("");

  // Auth mode
  const [authMode, setAuthMode] = useState<Monkey365AuthMode>("interactive");

  // Auth fields
  const [tenantId, setTenantId] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // Config fields
  const [collectModules, setCollectModules] = useState<string[]>([]);
  const [includeEntraId, setIncludeEntraId] = useState(true);
  const [exportFormats, setExportFormats] = useState<string[]>(["JSON"]);
  const [scanSites, setScanSites] = useState<string[]>([]);
  const [forceMsalDesktop, setForceMsalDesktop] = useState(false);
  const [verbose, setVerbose] = useState(false);

  // Tag inputs state
  const [collectInput, setCollectInput] = useState("");
  const [siteInput, setSiteInput] = useState("");

  const [scans, setScans] = useState<Monkey365ScanResultSummary[]>([]);
  const [selectedScan, setSelectedScan] = useState<Monkey365ScanResultDetail | null>(null);

  // Helper functions
  function formatDuration(seconds: number | null | undefined): string {
    if (!seconds) return "-";
    if (seconds < 60) return `${seconds}s`;
    const min = Math.floor(seconds / 60);
    const sec = seconds % 60;
    return `${min}m ${sec}s`;
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
    } catch (err) {
      console.error("Failed to load scan detail:", err);
      toast.error("Erreur lors du chargement des détails");
    }
  };

  // Poll every 5 seconds when any scan is "running"
  useEffect(() => {
    if (scans.some(s => s.status === "running")) {
      const interval = setInterval(loadScans, 5000);
      return () => clearInterval(interval);
    }
  }, [scans, loadScans]);

  // Load entreprises
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

  // Tag Input Handlers
  const handleAddCollect = () => {
    if (!collectInput.trim()) return;
    if (!collectModules.includes(collectInput.trim())) {
      setCollectModules([...collectModules, collectInput.trim()]);
    }
    setCollectInput("");
  };

  const handleRemoveCollect = (tag: string) => {
    setCollectModules(collectModules.filter((t) => t !== tag));
  };

  const handleAddSite = () => {
    if (!siteInput.trim()) return;
    if (!scanSites.includes(siteInput.trim())) {
      setScanSites([...scanSites, siteInput.trim()]);
    }
    setSiteInput("");
  };

  const handleRemoveSite = (tag: string) => {
    setScanSites(scanSites.filter((t) => t !== tag));
  };

  const handleToggleExportFormat = (format: string, checked: boolean) => {
    if (format === "JSON") return; // JSON always checked
    if (checked) {
      setExportFormats([...exportFormats, format]);
    } else {
      setExportFormats(exportFormats.filter((f) => f !== format));
    }
  };

  // Generate PowerShell Preview
  const generatePSPreview = () => {
    const params = [`$param = @{`];

    // Auth mode specific parameters
    if (authMode === "interactive") {
      params.push(`    # Interactive Browser Authentication`);
      params.push(`    PromptBehavior = 'SelectAccount'`);
    } else if (authMode === "device_code") {
      params.push(`    # Device Code Authentication`);
      params.push(`    UseDeviceCode = $true`);
    } else if (authMode === "ropc") {
      params.push(`    # Resource Owner Password Credentials`);
      params.push(`    TenantID = "${tenantId}"`);
      params.push(`    Username = "${username}"`);
      params.push(`    Password = "***"`);
    } else if (authMode === "client_credentials") {
      params.push(`    # Client Credentials (App Registration)`);
      params.push(`    TenantID = "${tenantId}"`);
      params.push(`    ClientID = "${clientId}"`);
      params.push(`    ClientSecret = "***"`);
    }

    if (collectModules.length > 0) {
      params.push(`    Collect = "${collectModules.join(",")}"`);
    }

    if (includeEntraId) {
      params.push(`    IncludeEntraID = $true`);
    } else {
      params.push(`    IncludeEntraID = $false`);
    }

    if (exportFormats.length > 0) {
      params.push(`    ExportTo = "${exportFormats.join(",")}"`);
    }

    if (scanSites.length > 0) {
      params.push(`    ScanSites = @("${scanSites.join('","')}")`);
    }

    if (forceMsalDesktop) {
      params.push(`    ForceMSALDesktop = $true`);
    }

    if (verbose) {
      params.push(`    Verbose = $true`);
    }

    params.push(`}`);
    params.push(`Invoke-Monkey365 @param`);

    return params.join("\n");
  };

  // Submit Handler
  const handleLaunch = async () => {
    // Validate based on auth_mode
    if (!selectedEntrepriseId) {
      toast.error("Veuillez sélectionner une entreprise");
      return;
    }

    if (authMode === "ropc") {
      if (!tenantId || !username || !password) {
        toast.error("Veuillez remplir Tenant ID, Username et Password pour le mode ROPC");
        return;
      }
    } else if (authMode === "client_credentials") {
      if (!tenantId || !clientId || !clientSecret) {
        toast.error("Veuillez remplir Tenant ID, Client ID et Client Secret pour le mode App Registration");
        return;
      }
    }

    setLaunching(true);
    try {
      const config: Monkey365Config = {
        auth_mode: authMode,
        collect: collectModules.length > 0 ? collectModules : undefined,
        include_entra_id: includeEntraId,
        export_to: exportFormats,
        scan_sites: scanSites.length > 0 ? scanSites : undefined,
        force_msal_desktop: forceMsalDesktop,
        verbose: verbose,
      };

      // Add credentials based on auth_mode
      if (authMode === "ropc") {
        config.tenant_id = tenantId;
        config.username = username;
        config.password = password;
      } else if (authMode === "client_credentials") {
        config.tenant_id = tenantId;
        config.client_id = clientId;
        config.client_secret = clientSecret;
      }

      const payload: Monkey365ScanCreate = {
        entreprise_id: parseInt(selectedEntrepriseId, 10),
        config,
      };

      await toolsApi.launchMonkey365Scan(payload);
      toast.success("Scan Monkey365 lancé en arrière-plan");
      
      // Clear sensitive fields
      setClientSecret("");
      setPassword("");
      
      // Navigate to history tab
      setActiveTab("history");
      loadScans();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur lors du lancement";
      toast.error(msg);
    } finally {
      setLaunching(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/outils">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Outils
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Monkey365 — Audit Microsoft 365</h1>
          <p className="text-muted-foreground">
            Lancer un audit complet de la configuration Microsoft 365 et Azure AD
          </p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="launch" className="flex items-center gap-1">
            <Play className="h-4 w-4" />
            Lancer un scan
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-1">
            Scans passés
          </TabsTrigger>
        </TabsList>

        <TabsContent value="launch" className="space-y-6">
          
          {/* Entreprise Selector */}
          <Card>
            <CardHeader>
              <CardTitle>Cible</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-w-md">
                <Label htmlFor="entreprise">Entreprise *</Label>
                <Select value={selectedEntrepriseId} onValueChange={setSelectedEntrepriseId}>
                  <SelectTrigger id="entreprise">
                    <SelectValue placeholder="Sélectionner une entreprise..." />
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
            </CardContent>
          </Card>

          {/* Authentication */}
          <Card>
            <CardHeader>
              <CardTitle>Authentification</CardTitle>
              <CardDescription>Sélectionnez le mode d'authentification pour Microsoft 365</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              
              {/* Auth Mode Selector */}
              <div className="space-y-2">
                <Label htmlFor="authMode">Mode d'authentification</Label>
                <Select value={authMode} onValueChange={(value) => setAuthMode(value as Monkey365AuthMode)}>
                  <SelectTrigger id="authMode">
                    <SelectValue placeholder="Sélectionner un mode..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="interactive">
                      <div className="flex items-center gap-2">
                        <span>Interactive Browser</span>
                        <Badge variant="outline" className="bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20">
                          🟢 Recommandé
                        </Badge>
                      </div>
                    </SelectItem>
                    <SelectItem value="device_code">
                      <div className="flex items-center gap-2">
                        <span>Device Code</span>
                        <Badge variant="outline" className="bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20">
                          🟢 Safest
                        </Badge>
                      </div>
                    </SelectItem>
                    <SelectItem value="ropc">
                      <div className="flex items-center gap-2">
                        <span>Username/Password (ROPC)</span>
                        <Badge variant="outline" className="bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20">
                          🟡 Credentials
                        </Badge>
                      </div>
                    </SelectItem>
                    <SelectItem value="client_credentials">
                      <div className="flex items-center gap-2">
                        <span>App Registration</span>
                        <Badge variant="outline" className="bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20">
                          🟡 App Secret
                        </Badge>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Info badges for each auth mode */}
              {authMode === "interactive" && (
                <Alert>
                  <AlertDescription className="flex items-center gap-2">
                    🔐 <span>Une fenêtre de navigateur s'ouvrira pour la connexion Microsoft.</span>
                  </AlertDescription>
                </Alert>
              )}

              {authMode === "device_code" && (
                <Alert>
                  <AlertDescription className="flex items-center gap-2">
                    📱 <span>Un code d'appareil sera généré. Ouvrez un navigateur pour vous authentifier.</span>
                  </AlertDescription>
                </Alert>
              )}

              {/* Conditional Credential Fields */}
              {authMode === "ropc" && (
                <div className="grid gap-4 md:grid-cols-2 pt-2">
                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="tenantId">Tenant ID *</Label>
                    <Input
                      id="tenantId"
                      value={tenantId}
                      onChange={(e) => setTenantId(e.target.value)}
                      placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="username">Username *</Label>
                    <Input
                      id="username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="user@domain.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">Password *</Label>
                    <Input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••••••••••••••"
                    />
                  </div>
                </div>
              )}

              {authMode === "client_credentials" && (
                <div className="grid gap-4 md:grid-cols-2 pt-2">
                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="tenantId">Tenant ID *</Label>
                    <Input
                      id="tenantId"
                      value={tenantId}
                      onChange={(e) => setTenantId(e.target.value)}
                      placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="clientId">Client ID *</Label>
                    <Input
                      id="clientId"
                      value={clientId}
                      onChange={(e) => setClientId(e.target.value)}
                      placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="clientSecret">Client Secret *</Label>
                    <Input
                      id="clientSecret"
                      type="password"
                      value={clientSecret}
                      onChange={(e) => setClientSecret(e.target.value)}
                      placeholder="••••••••••••••••••••••••"
                    />
                  </div>
                </div>
              )}

            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {/* Scan Configuration */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Configuration du scan</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                
                {/* Collect Modules */}
                <div className="space-y-2">
                  <Label>Modules à collecter (Collect)</Label>
                  <div className="flex gap-2">
                    <Input
                      value={collectInput}
                      onChange={(e) => setCollectInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAddCollect()}
                      placeholder="Ex: AzureAD, ExchangeOnline..."
                    />
                    <Button type="button" variant="secondary" onClick={handleAddCollect}>
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {collectModules.map((tag) => (
                      <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                        {tag}
                        <X className="h-3 w-3 cursor-pointer" onClick={() => handleRemoveCollect(tag)} />
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Scan Sites */}
                <div className="space-y-2">
                  <Label>Sites SharePoint (ScanSites)</Label>
                  <div className="flex gap-2">
                    <Input
                      value={siteInput}
                      onChange={(e) => setSiteInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAddSite()}
                      placeholder="Ex: https://contoso.sharepoint.com"
                    />
                    <Button type="button" variant="secondary" onClick={handleAddSite}>
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {scanSites.map((tag) => (
                      <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                        {tag}
                        <X className="h-3 w-3 cursor-pointer" onClick={() => handleRemoveSite(tag)} />
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  {/* Export Formats */}
                  <div className="space-y-3">
                    <Label>Formats d'export (ExportTo)</Label>
                    <div className="flex flex-wrap gap-4">
                      {["JSON", "HTML", "CSV", "CLIXML"].map((format) => (
                        <div key={format} className="flex items-center space-x-2">
                          <Checkbox
                            id={`export-${format}`}
                            checked={exportFormats.includes(format)}
                            disabled={format === "JSON"}
                            onCheckedChange={(checked: boolean) => handleToggleExportFormat(format, checked)}
                          />
                          <Label htmlFor={`export-${format}`} className="text-sm font-normal cursor-pointer">
                            {format}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  {/* Toggles */}
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="space-y-0.5">
                      <Label>Include Entra ID</Label>
                      <div className="text-xs text-muted-foreground">Inclure les données Entra ID</div>
                    </div>
                    <Switch checked={includeEntraId} onCheckedChange={setIncludeEntraId} />
                  </div>

                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="space-y-0.5">
                      <Label>Verbose</Label>
                      <div className="text-xs text-muted-foreground">Activer les logs détaillés</div>
                    </div>
                    <Switch checked={verbose} onCheckedChange={setVerbose} />
                  </div>
                </div>

                {/* ForceMSALDesktop */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="space-y-0.5">
                      <Label>Force MSAL Desktop</Label>
                      <div className="text-xs text-muted-foreground">Forcer l'authentification MSAL Desktop</div>
                    </div>
                    <Switch checked={forceMsalDesktop} onCheckedChange={setForceMsalDesktop} />
                  </div>
                  {forceMsalDesktop && (
                    <Alert variant="destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        Attention: Activer ForceMSALDesktop peut nécessiter une interaction utilisateur sur le serveur d'exécution !
                      </AlertDescription>
                    </Alert>
                  )}
                </div>

              </CardContent>
            </Card>

            {/* PowerShell Preview */}
            <Card className="flex flex-col">
              <CardHeader>
                <CardTitle>Aperçu PowerShell</CardTitle>
                <CardDescription>Commande générée (lecture seule)</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col">
                <div className="flex-1 bg-muted p-4 rounded-md overflow-x-auto text-xs font-mono whitespace-pre text-muted-foreground">
                  {generatePSPreview()}
                </div>
                <div className="mt-4 pt-4 border-t flex justify-end">
                  <Button onClick={handleLaunch} disabled={launching} className="w-full">
                    {launching ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4 mr-2" />
                    )}
                    {launching ? "Lancement..." : "Lancer le scan"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

                <TabsContent value="history" className="space-y-6">
          {/* Scan history table */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Historique des scans</CardTitle>
                <Button variant="outline" size="sm" onClick={loadScans} disabled={loading}>
                  <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
                  Actualiser
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {scans.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  Aucun scan Monkey365 pour cette entreprise. Lancez un scan depuis l&apos;onglet "Lancer un scan".
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID Scan</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Durée</TableHead>
                      <TableHead>Findings</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {scans.map((scan) => (
                      <TableRow
                        key={scan.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => loadScanDetail(scan.id)}
                      >
                        <TableCell className="font-mono text-xs">
                          {scan.id.toString().substring(0, 8)}...
                        </TableCell>
                        <TableCell>{getStatusBadge(scan.status)}</TableCell>
                        <TableCell>{formatDate(scan.created_at)}</TableCell>
                        <TableCell>{formatDuration(scan.duration_seconds)}</TableCell>
                        <TableCell>{scan.findings_count ?? "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Detail view */}
          {selectedScan && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Détails du scan</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setSelectedScan(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {selectedScan.error_message && (
                  <Alert variant="destructive" className="mb-4">
                    <AlertDescription>{selectedScan.error_message}</AlertDescription>
                  </Alert>
                )}
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold mb-2">Configuration</h4>
                    <pre className="bg-muted p-4 rounded text-xs overflow-auto">
                      {JSON.stringify(selectedScan.config_snapshot, null, 2)}
                    </pre>
                  </div>
                  {selectedScan.output_path && (
                    <div>
                      <h4 className="font-semibold mb-2">Chemin de sortie</h4>
                      <code className="bg-muted p-2 rounded text-xs block">
                        {selectedScan.output_path}
                      </code>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
