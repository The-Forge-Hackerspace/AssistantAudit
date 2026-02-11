"use client";

import { useState } from "react";
import {
  Lock,
  Search,
  Loader2,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Clock,
  Plus,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toolsApi } from "@/services/api";
import type { SSLCheckResult, SecurityFinding } from "@/types";
import { toast } from "sonner";
import { SEVERITY_LABELS, SEVERITY_COLORS, SEVERITY_VARIANTS } from "@/lib/constants";

export default function SSLCheckerPage() {
  const [host, setHost] = useState("");
  const [port, setPort] = useState("443");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SSLCheckResult[]>([]);
  const [activeTab, setActiveTab] = useState<string>("");

  // Batch mode
  const [batchHosts, setBatchHosts] = useState<string[]>([""]);

  const handleCheck = async () => {
    if (!host.trim()) {
      toast.error("Veuillez saisir un nom d'hôte ou une adresse IP");
      return;
    }
    setLoading(true);
    try {
      const result = await toolsApi.sslCheck({
        host: host.trim(),
        port: Number(port) || 443,
      });
      setResults((prev) => [result, ...prev]);
      setActiveTab(result.host);
      toast.success(
        `Vérification terminée — ${result.findings.length} constat(s)`
      );
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Erreur lors de la vérification";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchCheck = async () => {
    const hosts = batchHosts
      .map((h) => h.trim())
      .filter((h) => h.length > 0);
    if (hosts.length === 0) {
      toast.error("Ajoutez au moins un hôte");
      return;
    }
    setLoading(true);
    try {
      const batchResults = await toolsApi.sslCheckBatch(
        hosts.map((h) => ({ host: h, port: 443 }))
      );
      setResults((prev) => [...batchResults, ...prev]);
      if (batchResults.length > 0) {
        setActiveTab(batchResults[0].host);
      }
      toast.success(`${batchResults.length} vérification(s) terminée(s)`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur batch";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const removeResult = (host: string) => {
    setResults((prev) => prev.filter((r) => r.host !== host));
    if (activeTab === host && results.length > 1) {
      setActiveTab(results.find((r) => r.host !== host)?.host || "");
    }
  };

  const activeResult = results.find((r) => r.host === activeTab);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Lock className="h-6 w-6" />
          Vérificateur SSL/TLS
        </h1>
        <p className="text-muted-foreground">
          Vérification de certificats et protocoles TLS — détection de
          faiblesses cryptographiques
        </p>
      </div>

      {/* Check form */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Single check */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Vérification unique</CardTitle>
            <CardDescription>
              Testez un hôte spécifique
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <div className="flex-1">
                <Label>Hôte</Label>
                <Input
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  placeholder="example.com ou 192.168.1.1"
                  onKeyDown={(e) => e.key === "Enter" && handleCheck()}
                />
              </div>
              <div className="w-24">
                <Label>Port</Label>
                <Input
                  value={port}
                  onChange={(e) => setPort(e.target.value)}
                  placeholder="443"
                  type="number"
                />
              </div>
            </div>
            <Button
              onClick={handleCheck}
              disabled={loading}
              className="w-full"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Search className="h-4 w-4 mr-2" />
              )}
              Vérifier
            </Button>
          </CardContent>
        </Card>

        {/* Batch check */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Vérification par lot</CardTitle>
            <CardDescription>
              Testez plusieurs hôtes en une fois (max 20)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {batchHosts.map((h, idx) => (
              <div key={idx} className="flex gap-2">
                <Input
                  value={h}
                  onChange={(e) => {
                    const updated = [...batchHosts];
                    updated[idx] = e.target.value;
                    setBatchHosts(updated);
                  }}
                  placeholder={`Hôte ${idx + 1}`}
                />
                {batchHosts.length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() =>
                      setBatchHosts(batchHosts.filter((_, i) => i !== idx))
                    }
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setBatchHosts([...batchHosts, ""])}
                disabled={batchHosts.length >= 20}
              >
                <Plus className="h-4 w-4 mr-1" />
                Ajouter
              </Button>
              <Button
                size="sm"
                onClick={handleBatchCheck}
                disabled={loading}
                className="flex-1"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Search className="h-4 w-4 mr-2" />
                )}
                Tout vérifier
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="flex-wrap h-auto gap-1 p-1">
            {results.map((r) => (
              <TabsTrigger key={r.host} value={r.host} className="gap-1">
                {r.certificate && !r.certificate.error ? (
                  r.certificate.is_expired ? (
                    <ShieldX className="h-3 w-3 text-red-500" />
                  ) : r.certificate.is_trusted ? (
                    <ShieldCheck className="h-3 w-3 text-green-500" />
                  ) : (
                    <ShieldAlert className="h-3 w-3 text-yellow-500" />
                  )
                ) : (
                  <ShieldX className="h-3 w-3 text-red-500" />
                )}
                {r.host}
              </TabsTrigger>
            ))}
          </TabsList>

          {results.map((result) => (
            <TabsContent key={result.host} value={result.host}>
              <SSLResultView result={result} onRemove={() => removeResult(result.host)} />
            </TabsContent>
          ))}
        </Tabs>
      )}
    </div>
  );
}

function SSLResultView({
  result,
  onRemove,
}: {
  result: SSLCheckResult;
  onRemove: () => void;
}) {
  const cert = result.certificate;

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Certificate status */}
        <Card>
          <CardContent className="pt-4 text-center">
            {cert && !cert.error ? (
              <>
                {cert.is_expired ? (
                  <XCircle className="h-8 w-8 mx-auto mb-2 text-red-500" />
                ) : cert.is_trusted ? (
                  <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                ) : (
                  <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-yellow-500" />
                )}
                <p className="text-sm font-medium">
                  {cert.is_expired
                    ? "Expiré"
                    : cert.is_trusted
                    ? "Valide & Approuvé"
                    : "Non approuvé"}
                </p>
              </>
            ) : (
              <>
                <XCircle className="h-8 w-8 mx-auto mb-2 text-red-500" />
                <p className="text-sm font-medium">Erreur</p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Days remaining */}
        <Card>
          <CardContent className="pt-4 text-center">
            <Clock className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-2xl font-bold">
              {cert && cert.days_remaining >= 0 ? cert.days_remaining : "—"}
            </p>
            <p className="text-xs text-muted-foreground">jour(s) restant(s)</p>
          </CardContent>
        </Card>

        {/* Protocols */}
        <Card>
          <CardContent className="pt-4 text-center">
            <Shield className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-2xl font-bold">
              {result.protocols.filter((p) => p.supported && p.is_secure).length}
              /
              {result.protocols.filter((p) => p.supported).length}
            </p>
            <p className="text-xs text-muted-foreground">protocoles sécurisés</p>
          </CardContent>
        </Card>

        {/* Findings */}
        <Card>
          <CardContent className="pt-4 text-center">
            <Info className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-2xl font-bold">{result.findings.length}</p>
            <p className="text-xs text-muted-foreground">constat(s)</p>
          </CardContent>
        </Card>
      </div>

      {/* Detail tabs */}
      <Tabs defaultValue="cert" className="space-y-4">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="cert">Certificat</TabsTrigger>
            <TabsTrigger value="protocols">Protocoles</TabsTrigger>
            <TabsTrigger value="findings">
              Constats ({result.findings.length})
            </TabsTrigger>
          </TabsList>
          <Button variant="ghost" size="sm" onClick={onRemove}>
            <Trash2 className="h-4 w-4 mr-1" />
            Retirer
          </Button>
        </div>

        {/* Certificate tab */}
        <TabsContent value="cert">
          <Card>
            <CardContent className="pt-6">
              {cert && !cert.error ? (
                <div className="grid md:grid-cols-2 gap-y-3 gap-x-8">
                  <InfoRow label="Sujet (CN)" value={cert.subject} />
                  <InfoRow label="Émetteur" value={cert.issuer} />
                  <InfoRow label="Organisation" value={cert.organization || "—"} />
                  <InfoRow label="Numéro de série" value={cert.serial_number} mono />
                  <InfoRow
                    label="Valide depuis"
                    value={cert.not_before ? new Date(cert.not_before).toLocaleDateString("fr-FR") : "—"}
                  />
                  <InfoRow
                    label="Expire le"
                    value={cert.not_after ? new Date(cert.not_after).toLocaleDateString("fr-FR") : "—"}
                  />
                  <InfoRow
                    label="Auto-signé"
                    value={cert.self_signed ? "Oui ⚠️" : "Non ✅"}
                  />
                  <InfoRow
                    label="Approuvé (CA)"
                    value={cert.is_trusted ? "Oui ✅" : "Non ⚠️"}
                  />
                  {cert.san.length > 0 && (
                    <div className="md:col-span-2">
                      <span className="text-sm text-muted-foreground">
                        SAN (Subject Alternative Names) :
                      </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {cert.san.map((s, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <XCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
                  <p className="font-medium">
                    Impossible de récupérer le certificat
                  </p>
                  {cert?.error && (
                    <p className="text-sm mt-2">{cert.error}</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Protocols tab */}
        <TabsContent value="protocols">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Protocole</TableHead>
                    <TableHead>Supporté</TableHead>
                    <TableHead>Sécurisé</TableHead>
                    <TableHead>Statut</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.protocols.map((proto) => (
                    <TableRow key={proto.name}>
                      <TableCell className="font-medium">{proto.name}</TableCell>
                      <TableCell>
                        {proto.supported ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-muted-foreground" />
                        )}
                      </TableCell>
                      <TableCell>
                        {proto.is_secure ? (
                          <Badge variant="default">Sûr</Badge>
                        ) : (
                          <Badge variant="destructive">Obsolète</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {proto.supported && !proto.is_secure ? (
                          <Badge variant="destructive">
                            ⚠️ À désactiver
                          </Badge>
                        ) : proto.supported && proto.is_secure ? (
                          <Badge variant="default">✅ OK</Badge>
                        ) : (
                          <span className="text-muted-foreground text-sm">
                            Non supporté
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Findings tab */}
        <TabsContent value="findings">
          <Card>
            <CardContent className="pt-6 space-y-3">
              {result.findings.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <ShieldCheck className="h-12 w-12 mx-auto mb-4 text-green-500" />
                  <p>Aucun problème détecté</p>
                </div>
              ) : (
                result.findings.map((finding, idx) => (
                  <FindingRow key={idx} finding={finding} />
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function InfoRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <span className="text-sm text-muted-foreground">{label}</span>
      <p className={`font-medium ${mono ? "font-mono text-sm" : ""}`}>
        {value || "—"}
      </p>
    </div>
  );
}

function FindingRow({ finding }: { finding: SecurityFinding }) {
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
        SEVERITY_COLORS[finding.severity] || ""
      }`}
    >
      <div className="flex items-start gap-3">
        <SeverityIcon className="h-5 w-5 mt-0.5 shrink-0" />
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant={SEVERITY_VARIANTS[finding.severity] || "outline"}>
              {SEVERITY_LABELS[finding.severity] || finding.severity}
            </Badge>
            <span className="font-semibold text-sm">{finding.title}</span>
          </div>
          <p className="text-sm">{finding.description}</p>
          {finding.remediation && (
            <p className="text-sm italic">
              💡 <strong>Recommandation :</strong> {finding.remediation}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
