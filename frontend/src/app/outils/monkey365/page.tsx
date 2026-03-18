"use client";

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";

import { toolsApi, entreprisesApi } from "@/services/api";
import type { Entreprise, Monkey365Config, Monkey365ScanCreate } from "@/types/api";

export default function Monkey365Page() {
  const [activeTab, setActiveTab] = useState("launch");
  const [loading, setLoading] = useState(false);
  const [launching, setLaunching] = useState(false);

  // Entreprises state
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [selectedEntrepriseId, setSelectedEntrepriseId] = useState<string>("");

  // Auth fields
  const [tenantId, setTenantId] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [authMethod, setAuthMethod] = useState("client_credentials");

  // Config fields
  const [collectModules, setCollectModules] = useState<string[]>([]);
  const [promptBehavior, setPromptBehavior] = useState("Auto");
  const [includeEntraId, setIncludeEntraId] = useState(true);
  const [exportFormats, setExportFormats] = useState<string[]>(["JSON"]);
  const [scanSites, setScanSites] = useState<string[]>([]);
  const [forceMsalDesktop, setForceMsalDesktop] = useState(false);
  const [verbose, setVerbose] = useState(false);

  // Tag inputs state
  const [collectInput, setCollectInput] = useState("");
  const [siteInput, setSiteInput] = useState("");

  // Load entreprises
  useEffect(() => {
    const loadEntreprises = async () => {
      try {
        const data = await entreprisesApi.list();
        setEntreprises(Array.isArray(data) ? data : (data as any).items || []);
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
    const params = [
      `$param = @{`,
      `    TenantID = "${tenantId}"`,
      `    ClientID = "${clientId}"`,
      `    ClientSecret = "***"`,
    ];

    if (collectModules.length > 0) {
      params.push(`    Collect = "${collectModules.join(",")}"`);
    }

    if (promptBehavior !== "Auto") {
      params.push(`    PromptBehavior = "${promptBehavior}"`);
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
    if (!selectedEntrepriseId || !tenantId || !clientId || !clientSecret) {
      toast.error("Veuillez remplir les champs obligatoires (Entreprise, Tenant ID, Client ID, Client Secret)");
      return;
    }

    setLaunching(true);
    try {
      const config: Monkey365Config = {
        tenant_id: tenantId,
        client_id: clientId,
        client_secret: clientSecret,
        auth_method: authMethod,
        collect: collectModules.length > 0 ? collectModules : undefined,
        prompt_behavior: promptBehavior,
        include_entra_id: includeEntraId,
        export_to: exportFormats,
        scan_sites: scanSites.length > 0 ? scanSites : undefined,
        force_msal_desktop: forceMsalDesktop,
        verbose: verbose,
      };

      const payload: Monkey365ScanCreate = {
        entreprise_id: parseInt(selectedEntrepriseId, 10),
        config,
      };

      await toolsApi.launchMonkey365Scan(payload);
      toast.success("Scan Monkey365 lancé en arrière-plan");
      
      // Clear sensitive fields
      setClientSecret("");
      
      // Navigate to history tab
      setActiveTab("history");
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
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
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
                <div className="space-y-2">
                  <Label htmlFor="authMethod">Méthode d'authentification</Label>
                  <Select value={authMethod} onValueChange={setAuthMethod}>
                    <SelectTrigger id="authMethod">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="client_credentials">Client Credentials (Application)</SelectItem>
                      <SelectItem value="interactive">Interactive (User)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
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
                  {/* Prompt Behavior */}
                  <div className="space-y-2">
                    <Label htmlFor="promptBehavior">Prompt Behavior</Label>
                    <Select value={promptBehavior} onValueChange={setPromptBehavior}>
                      <SelectTrigger id="promptBehavior">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Auto">Auto</SelectItem>
                        <SelectItem value="SelectAccount">SelectAccount</SelectItem>
                        <SelectItem value="Always">Always</SelectItem>
                        <SelectItem value="Never">Never</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

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

        <TabsContent value="history">
          <Card>
            <CardContent className="p-6 text-center text-muted-foreground">
              Implémentation de l'historique dans la tâche suivante (Task 13).
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
