"use client";

import { useEffect, useState, useCallback, lazy, Suspense } from "react";
import {
  Castle,
  Play,
  Loader2,
  Trash2,
  Eye,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Shield,
  Server,
  RefreshCw,
  ClipboardCheck,
  ArrowLeft,
  Info,
  Terminal,
  BarChart3,
} from "lucide-react";
import Link from "next/link";

import { useAuth } from "@/contexts/auth-context";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Progress } from "@/components/ui/progress";
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

import { toolsApi } from "@/services/api";
import type {
  PingCastleResultSummary,
  PingCastleResultRead,
  PingCastleCreate,
} from "@/types";

// Lazy-load terminal component (heavy dep: xterm.js)
const PingCastleTerminal = lazy(
  () => import("@/components/pingcastle-terminal")
);

// ── Helpers ──

function scoreColor(score: number | null): string {
  if (score === null || score === undefined) return "text-muted-foreground";
  if (score === 0) return "text-green-600";
  if (score <= 25) return "text-green-500";
  if (score <= 50) return "text-yellow-500";
  if (score <= 75) return "text-orange-500";
  return "text-red-500";
}

function scoreBadge(score: number | null) {
  if (score === null || score === undefined) return <Badge variant="secondary">N/A</Badge>;
  if (score === 0) return <Badge className="bg-green-600">0</Badge>;
  if (score <= 25) return <Badge className="bg-green-500">{score}</Badge>;
  if (score <= 50) return <Badge className="bg-yellow-500 text-black">{score}</Badge>;
  if (score <= 75) return <Badge className="bg-orange-500">{score}</Badge>;
  return <Badge variant="destructive">{score}</Badge>;
}

function getSeverityVariant(severity: string): "destructive" | "secondary" | "outline" {
  if (severity === "critical" || severity === "high") return "destructive";
  if (severity === "medium") return "secondary";
  return "outline";
}

function statusBadge(status: string) {
  switch (status) {
    case "success":
      return <Badge className="bg-green-600"><CheckCircle2 className="h-3 w-3 mr-1" />Succès</Badge>;
    case "failed":
      return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Échoué</Badge>;
    case "running":
      return <Badge className="bg-blue-500"><Loader2 className="h-3 w-3 mr-1 animate-spin" />En cours</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}

function formatDuration(seconds: number | null): string {
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

// ── Page ──

export default function PingCastlePage() {
  const [activeTab, setActiveTab] = useState("automated");
  const [results, setResults] = useState<PingCastleResultSummary[]>([]);
  const [selectedResult, setSelectedResult] = useState<PingCastleResultRead | null>(null);
  const [loading, setLoading] = useState(false);
  const [launching, setLaunching] = useState(false);

  // Form state
  const [form, setForm] = useState<PingCastleCreate>({
    target_host: "",
    domain: "",
    username: "",
    password: "",
  });

  // Auth context — WebSocket now uses httpOnly cookies (SEC-03)
  const { user } = useAuth();

  // ── Load results ──
  const loadResults = useCallback(async () => {
    setLoading(true);
    try {
      const data = await toolsApi.listPingCastleResults();
      setResults(data);
    } catch {
      toast.error("Impossible de charger les résultats PingCastle");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  // Poll running results
  useEffect(() => {
    const hasRunning = results.some((r) => r.status === "running");
    if (!hasRunning) return;

    const interval = setInterval(loadResults, 5000);
    return () => clearInterval(interval);
  }, [results, loadResults]);

  // ── Launch audit ──
  const handleLaunch = async () => {
    if (!form.target_host || !form.domain || !form.username || !form.password) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    setLaunching(true);
    try {
      await toolsApi.launchPingCastle(form);
      toast.success("Audit PingCastle lancé en arrière-plan");
      setForm((f) => ({ ...f, password: "" }));
      await loadResults();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur lors du lancement";
      toast.error(msg);
    } finally {
      setLaunching(false);
    }
  };

  // ── View detail ──
  const handleViewDetail = async (id: number) => {
    try {
      const detail = await toolsApi.getPingCastleResult(id);
      setSelectedResult(detail);
    } catch {
      toast.error("Impossible de charger le détail");
    }
  };

  // ── Delete ──
  const handleDelete = async (id: number) => {
    try {
      await toolsApi.deletePingCastleResult(id);
      toast.success("Audit PingCastle supprimé");
      setResults((prev) => prev.filter((r) => r.id !== id));
      if (selectedResult?.id === id) setSelectedResult(null);
    } catch {
      toast.error("Impossible de supprimer");
    }
  };

  // ── Detail view ──
  if (selectedResult) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => setSelectedResult(null)}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Retour
          </Button>
          <div>
            <h1 className="text-2xl font-bold">
              PingCastle #{selectedResult.id} — {selectedResult.domain}
            </h1>
            <p className="text-muted-foreground">
              DC : {selectedResult.target_host} | {formatDate(selectedResult.created_at)}
            </p>
          </div>
          <div className="ml-auto">{statusBadge(selectedResult.status)}</div>
        </div>

        {/* Score cards */}
        {selectedResult.status === "success" && (
          <div className="grid gap-4 md:grid-cols-5">
            {[
              { label: "Global", score: selectedResult.global_score, icon: Shield },
              { label: "Stale Objects", score: selectedResult.stale_objects_score, icon: Clock },
              { label: "Privileged", score: selectedResult.privileged_accounts_score, icon: Shield },
              { label: "Trusts", score: selectedResult.trust_score, icon: Server },
              { label: "Anomalies", score: selectedResult.anomaly_score, icon: AlertTriangle },
            ].map(({ label, score, icon: Icon }) => (
              <Card key={label}>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${scoreColor(score)}`}>
                    {score ?? "N/A"}
                  </div>
                  <Progress
                    value={score ?? 0}
                    className="mt-2 h-1.5"
                  />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Maturity level */}
        {selectedResult.maturity_level != null && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Niveau de maturité
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div className="text-4xl font-bold text-primary">
                  {selectedResult.maturity_level}/5
                </div>
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((level) => (
                    <div
                      key={level}
                      className={`w-10 h-3 rounded ${
                        level <= (selectedResult.maturity_level ?? 0)
                          ? "bg-primary"
                          : "bg-muted"
                      }`}
                    />
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error */}
        {selectedResult.error_message && (
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive flex items-center gap-2">
                <XCircle className="h-5 w-5" />
                Erreur
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-sm whitespace-pre-wrap bg-muted p-3 rounded-md">
                {selectedResult.error_message}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Risk rules */}
        {selectedResult.risk_rules && selectedResult.risk_rules.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Règles de risque ({selectedResult.risk_rules.length})
              </CardTitle>
              <CardDescription>
                Règles PingCastle violées, triées par nombre de points (impact)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Points</TableHead>
                    <TableHead>Sévérité</TableHead>
                    <TableHead>Catégorie</TableHead>
                    <TableHead>Rule ID</TableHead>
                    <TableHead className="max-w-md">Description</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {selectedResult.risk_rules.map((rule, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-mono font-bold">{rule.points}</TableCell>
                      <TableCell>
                        <Badge variant={getSeverityVariant(rule.severity)}>
                          {rule.severity}
                        </Badge>
                      </TableCell>
                      <TableCell>{rule.category}</TableCell>
                      <TableCell className="font-mono text-xs">{rule.rule_id}</TableCell>
                      <TableCell className="max-w-md text-xs truncate" title={rule.rationale}>
                        {rule.rationale}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Domain info */}
        {selectedResult.domain_info && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-5 w-5" />
                Informations du domaine
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 md:grid-cols-2 text-sm">
                {Object.entries(selectedResult.domain_info).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-4 py-1 border-b border-border/50">
                    <span className="text-muted-foreground capitalize">
                      {key.replace(/_/g, " ")}
                    </span>
                    <span className="font-medium">{String(value ?? "-")}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  // ── Main view with tabs ──
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Castle className="h-6 w-6" />
            PingCastle — Audit AD avancé
          </h1>
          <p className="text-muted-foreground">
            Audit approfondi d&apos;Active Directory avec PingCastle (healthcheck, scores de risque, règles)
          </p>
        </div>
        <Link href="/outils">
          <Button variant="outline" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Outils
          </Button>
        </Link>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="automated" className="flex items-center gap-1">
            <ClipboardCheck className="h-4 w-4" />
            Audit automatisé
          </TabsTrigger>
          <TabsTrigger value="terminal" className="flex items-center gap-1">
            <Terminal className="h-4 w-4" />
            Terminal interactif
          </TabsTrigger>
        </TabsList>

        {/* ── Onglet Audit automatisé ── */}
        <TabsContent value="automated" className="space-y-6">
          {/* Launch form */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="h-5 w-5" />
                Lancer un audit PingCastle
              </CardTitle>
              <CardDescription>
                Exécute PingCastle en mode healthcheck sur un contrôleur de domaine.
                Les résultats sont analysés et stockés pour le pré-remplissage des audits AD.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="pc-host">Contrôleur de domaine *</Label>
                  <Input
                    id="pc-host"
                    placeholder="192.168.1.10 ou dc01.corp.local"
                    value={form.target_host}
                    onChange={(e) => setForm((f) => ({ ...f, target_host: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pc-domain">Domaine AD *</Label>
                  <Input
                    id="pc-domain"
                    placeholder="corp.local"
                    value={form.domain}
                    onChange={(e) => setForm((f) => ({ ...f, domain: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pc-user">Utilisateur *</Label>
                  <Input
                    id="pc-user"
                    placeholder="DOMAIN\admin ou admin@corp.local"
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pc-pass">Mot de passe *</Label>
                  <Input
                    id="pc-pass"
                    type="password"
                    placeholder="••••••••"
                    value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  />
                </div>
              </div>
              <div className="mt-4 flex gap-2">
                <Button onClick={handleLaunch} disabled={launching}>
                  {launching ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4 mr-2" />
                  )}
                  {launching ? "Lancement..." : "Lancer l'audit"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Results table */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Historique des audits</CardTitle>
                  <CardDescription>
                    {results.length} audit(s) PingCastle enregistré(s)
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={loadResults} disabled={loading}>
                  <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
                  Actualiser
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading && results.length === 0 ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : results.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Castle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Aucun audit PingCastle lancé</p>
                  <p className="text-sm">Utilisez le formulaire ci-dessus pour lancer votre premier audit</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead>DC</TableHead>
                      <TableHead>Domaine</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Maturité</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Durée</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((r) => (
                      <TableRow key={r.id}>
                        <TableCell className="font-mono">#{r.id}</TableCell>
                        <TableCell>{statusBadge(r.status)}</TableCell>
                        <TableCell className="font-mono text-xs">{r.target_host}</TableCell>
                        <TableCell>{r.domain}</TableCell>
                        <TableCell>{scoreBadge(r.global_score)}</TableCell>
                        <TableCell>
                          {r.maturity_level != null ? (
                            <span className="font-medium">{r.maturity_level}/5</span>
                          ) : (
                            "-"
                          )}
                        </TableCell>
                        <TableCell className="text-xs">{formatDate(r.created_at)}</TableCell>
                        <TableCell>{formatDuration(r.duration_seconds)}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            {r.status === "success" && (
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleViewDetail(r.id)}
                                title="Voir détails"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                            )}
                            {r.status === "failed" && (
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleViewDetail(r.id)}
                                title="Voir l'erreur"
                              >
                                <Info className="h-4 w-4" />
                              </Button>
                            )}
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="ghost" size="icon" title="Supprimer">
                                  <Trash2 className="h-4 w-4 text-destructive" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Supprimer cet audit ?</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    L&apos;audit PingCastle #{r.id} sera définitivement supprimé.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Annuler</AlertDialogCancel>
                                  <AlertDialogAction onClick={() => handleDelete(r.id)}>
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
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Onglet Terminal interactif ── */}
        <TabsContent value="terminal" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Terminal className="h-5 w-5" />
                Terminal PingCastle interactif
              </CardTitle>
              <CardDescription>
                Lance PingCastle en mode interactif (menu principal). Vous pouvez naviguer
                dans les menus, choisir les options d&apos;audit et voir les résultats en temps réel.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {user ? (
                <Suspense
                  fallback={
                    <div className="flex items-center justify-center h-64">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                  }
                >
                  <PingCastleTerminal token="" />
                </Suspense>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <AlertTriangle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Authentification requise pour le terminal interactif</p>
                  <p className="text-sm">Veuillez vous reconnecter</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
