"use client";

import { useState } from "react";
import {
  FileCode,
  Upload,
  Shield,
  AlertTriangle,
  ShieldAlert,
  Info,
  ChevronDown,
  ChevronUp,
  Loader2,
  Network,
  List,
  Bug,
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
import { toolsApi } from "@/services/api";
import type { ConfigUploadResponse, SecurityFinding, InterfaceInfo, FirewallRuleInfo } from "@/types";
import { toast } from "sonner";
import {
  SEVERITY_LABELS,
  SEVERITY_COLORS,
  SEVERITY_VARIANTS,
} from "@/lib/constants";

export default function ConfigParserPage() {
  const [result, setResult] = useState<ConfigUploadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleUpload = async (file: File) => {
    setLoading(true);
    try {
      const res = await toolsApi.analyzeConfig(file);
      setResult(res);
      toast.success(
        `Configuration analysée — ${res.analysis.findings.length} constat(s)`
      );
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

  const findings = result?.analysis?.findings || [];
  const critCount = findings.filter((f) => f.severity === "critical").length;
  const highCount = findings.filter((f) => f.severity === "high").length;
  const medCount = findings.filter((f) => f.severity === "medium").length;
  const lowCount = findings.filter((f) => f.severity === "low").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <FileCode className="h-6 w-6" />
          Analyseur de Configuration
        </h1>
        <p className="text-muted-foreground">
          Upload d&apos;un export de configuration réseau (FortiGate, OPNsense)
          pour analyse automatique de sécurité
        </p>
      </div>

      {/* Upload zone */}
      {!result && (
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
              💡 <strong>Recommandation :</strong> {finding.remediation}
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
