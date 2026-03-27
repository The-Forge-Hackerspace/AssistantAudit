"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  ShieldCheck,
  Play,
  Loader2,
  FileSearch,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";
import { agentsApi, oradadApi } from "@/services/api";
import { cn } from "@/lib/utils";
import type { Agent, OradadTask, AnssiReport, AnssiCheckResult } from "@/types";

// ── Constants ──
const ANSSI_LEVELS: Record<number, { label: string; color: string; bg: string }> = {
  1: { label: "Critique", color: "text-red-700 dark:text-red-400", bg: "bg-red-500" },
  2: { label: "Lacunes", color: "text-orange-700 dark:text-orange-400", bg: "bg-orange-500" },
  3: { label: "Basique", color: "text-yellow-700 dark:text-yellow-400", bg: "bg-yellow-500" },
  4: { label: "Bon", color: "text-emerald-700 dark:text-emerald-400", bg: "bg-emerald-500" },
  5: { label: "État de l'art", color: "text-emerald-800 dark:text-emerald-300", bg: "bg-emerald-700" },
};

function taskStatusBadge(status: string) {
  switch (status) {
    case "completed":
      return <Badge variant="default" className="bg-emerald-600">Terminé</Badge>;
    case "running":
      return <Badge variant="secondary" className="bg-blue-500/20 text-blue-700 dark:text-blue-400">En cours</Badge>;
    case "pending":
    case "dispatched":
      return <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-700 dark:text-yellow-400">En attente</Badge>;
    case "failed":
      return <Badge variant="destructive">Échoué</Badge>;
    case "cancelled":
      return <Badge variant="outline">Annulé</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function findingStatusIcon(status: string) {
  switch (status) {
    case "pass":
      return <CheckCircle2 className="size-4 text-emerald-500" />;
    case "fail":
      return <XCircle className="size-4 text-red-500" />;
    case "warning":
      return <AlertTriangle className="size-4 text-yellow-500" />;
    default:
      return <HelpCircle className="size-4 text-muted-foreground" />;
  }
}

function findingStatusLabel(status: string) {
  switch (status) {
    case "pass": return "Conforme";
    case "fail": return "Non conforme";
    case "warning": return "Avertissement";
    default: return "Non vérifié";
  }
}

// ── Page ──
export default function OradadPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  // Agents
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(true);

  // Tasks
  const [tasks, setTasks] = useState<OradadTask[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(true);

  // Launch form
  const [selectedAgentUuid, setSelectedAgentUuid] = useState<string>("");
  const [domain, setDomain] = useState("");
  const [collectConfidential, setCollectConfidential] = useState(false);
  const [launching, setLaunching] = useState(false);

  // Report view
  const [selectedTask, setSelectedTask] = useState<OradadTask | null>(null);
  const [report, setReport] = useState<AnssiReport | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  // Filter agents to only those with "oradad" in allowed_tools and active
  const oradadAgents = useMemo(
    () => agents.filter((a) => a.status === "active" && a.allowed_tools.includes("oradad")),
    [agents]
  );

  // ── Fetch data ──
  const fetchAgents = useCallback(async () => {
    try {
      const data = await agentsApi.list();
      setAgents(data);
    } catch {
      // non-blocking
    } finally {
      setLoadingAgents(false);
    }
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await oradadApi.listTasks();
      setTasks(data);
    } catch {
      toast.error("Erreur lors du chargement des collectes");
    } finally {
      setLoadingTasks(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchTasks();
  }, [fetchAgents, fetchTasks]);

  // Poll running tasks
  useEffect(() => {
    const hasRunning = tasks.some((t) => t.status === "running" || t.status === "pending" || t.status === "dispatched");
    if (!hasRunning) return;
    const interval = setInterval(fetchTasks, 5000);
    return () => clearInterval(interval);
  }, [tasks, fetchTasks]);

  // ── Launch collect ──
  const handleLaunch = async () => {
    if (!selectedAgentUuid) {
      toast.error("Sélectionnez un agent");
      return;
    }
    setLaunching(true);
    try {
      await agentsApi.dispatch({
        agent_uuid: selectedAgentUuid,
        tool: "oradad",
        parameters: {
          domain: domain || undefined,
          collect_confidential: collectConfidential,
        },
      });
      toast.success("Collecte ORADAD lancée");
      setDomain("");
      setCollectConfidential(false);
      await fetchTasks();
    } catch {
      toast.error("Erreur lors du lancement de la collecte");
    } finally {
      setLaunching(false);
    }
  };

  // ── View report ──
  const handleViewReport = async (task: OradadTask) => {
    setSelectedTask(task);
    setReport(null);
    if (!task.has_report) return;
    setLoadingReport(true);
    try {
      const data = await oradadApi.getReport(task.task_uuid);
      setReport(data);
    } catch {
      toast.error("Erreur lors du chargement du rapport");
    } finally {
      setLoadingReport(false);
    }
  };

  // ── Launch analysis ──
  const handleAnalyze = async () => {
    if (!selectedTask) return;
    setAnalyzing(true);
    try {
      const data = await oradadApi.analyze(selectedTask.task_uuid);
      setReport(data);
      setSelectedTask({ ...selectedTask, has_report: true });
      // Update task in list
      setTasks((prev) =>
        prev.map((t) =>
          t.task_uuid === selectedTask.task_uuid ? { ...t, has_report: true } : t
        )
      );
      toast.success("Analyse ANSSI terminée");
    } catch {
      toast.error("Erreur lors de l'analyse ANSSI");
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Group findings by category ──
  const groupedFindings = useMemo(() => {
    if (!report) return new Map<string, AnssiCheckResult[]>();
    const groups = new Map<string, AnssiCheckResult[]>();
    // Sort: fail first, then warning, then pass, then not_checked; within each by level desc
    const sorted = [...report.findings].sort((a, b) => {
      const statusOrder = { fail: 0, warning: 1, pass: 2, not_checked: 3 };
      const sa = statusOrder[a.status as keyof typeof statusOrder] ?? 4;
      const sb = statusOrder[b.status as keyof typeof statusOrder] ?? 4;
      if (sa !== sb) return sa - sb;
      return b.level - a.level;
    });
    for (const f of sorted) {
      const cat = f.category || "Autre";
      if (!groups.has(cat)) groups.set(cat, []);
      groups.get(cat)!.push(f);
    }
    return groups;
  }, [report]);

  const levelInfo = report ? ANSSI_LEVELS[report.level] || ANSSI_LEVELS[1] : null;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <ShieldCheck className="size-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Collecte Active Directory</h1>
          <p className="text-sm text-muted-foreground">
            ORADAD (ANSSI) — Collecte et analyse de sécurité Active Directory
          </p>
        </div>
      </div>

      {/* ── Launch section ── */}
      <Card>
        <CardHeader>
          <CardTitle>Lancer une collecte</CardTitle>
          <CardDescription>
            Sélectionnez un agent avec l&apos;outil ORADAD pour collecter les données AD.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-2">
                <Label>Agent</Label>
                {loadingAgents ? (
                  <Skeleton className="h-10 w-full" />
                ) : oradadAgents.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Aucun agent actif avec l&apos;outil ORADAD
                  </p>
                ) : (
                  <Select value={selectedAgentUuid} onValueChange={setSelectedAgentUuid}>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner un agent" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        {oradadAgents.map((a) => (
                          <SelectItem key={a.agent_uuid} value={a.agent_uuid}>
                            {a.name} {a.last_ip ? `(${a.last_ip})` : ""}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="oradad-domain">Domaine (optionnel)</Label>
                <Input
                  id="oradad-domain"
                  placeholder="Auto-détecté si vide"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                />
              </div>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <Checkbox
                  checked={collectConfidential}
                  onCheckedChange={(v) => setCollectConfidential(v === true)}
                />
                <span className="text-sm">Collecter les attributs confidentiels</span>
              </label>
              <div className="flex-1" />
              <Button
                onClick={handleLaunch}
                disabled={launching || !selectedAgentUuid}
              >
                {launching ? (
                  <Loader2 data-icon="inline-start" className="animate-spin" />
                ) : (
                  <Play data-icon="inline-start" />
                )}
                Lancer la collecte
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Results section ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Résultats des collectes</CardTitle>
              <CardDescription>
                Historique des collectes ORADAD et rapports ANSSI
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={fetchTasks}>
              <RefreshCw data-icon="inline-start" />
              Actualiser
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loadingTasks ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : tasks.length === 0 ? (
            <div className="flex flex-col items-center gap-4 py-16">
              <ShieldCheck className="size-12 text-muted-foreground" />
              <p className="text-muted-foreground">Aucune collecte ORADAD</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Rapport ANSSI</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map((task) => (
                  <TableRow
                    key={task.task_uuid}
                    className={cn(
                      "cursor-pointer",
                      selectedTask?.task_uuid === task.task_uuid && "bg-muted/50"
                    )}
                    onClick={() => handleViewReport(task)}
                  >
                    <TableCell>
                      {task.created_at
                        ? new Date(task.created_at).toLocaleDateString("fr-FR", {
                            day: "2-digit",
                            month: "2-digit",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "—"}
                    </TableCell>
                    <TableCell className="font-medium">
                      {task.agent_name || "—"}
                    </TableCell>
                    <TableCell>{taskStatusBadge(task.status)}</TableCell>
                    <TableCell>
                      {task.has_report ? (
                        <Badge variant="default" className="bg-emerald-600">
                          Disponible
                        </Badge>
                      ) : task.status === "completed" ? (
                        <Badge variant="outline">Non analysé</Badge>
                      ) : (
                        <span className="text-sm text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {task.status === "completed" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleViewReport(task);
                          }}
                        >
                          <FileSearch data-icon="inline-start" />
                          {task.has_report ? "Voir le rapport" : "Détails"}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ── Detail / Report section ── */}
      {selectedTask && selectedTask.status === "completed" && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                {report ? "Rapport de sécurité AD — ANSSI" : "Collecte terminée"}
              </CardTitle>
              {!report && !loadingReport && (
                <Button onClick={handleAnalyze} disabled={analyzing}>
                  {analyzing ? (
                    <Loader2 data-icon="inline-start" className="animate-spin" />
                  ) : (
                    <ShieldCheck data-icon="inline-start" />
                  )}
                  Lancer l&apos;analyse ANSSI
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {loadingReport || analyzing ? (
              <div className="flex flex-col items-center gap-4 py-12">
                <Loader2 className="size-8 animate-spin text-primary" />
                <p className="text-muted-foreground">
                  {analyzing ? "Analyse ANSSI en cours..." : "Chargement du rapport..."}
                </p>
              </div>
            ) : report && levelInfo ? (
              <div className="flex flex-col gap-6">
                {/* Score card */}
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <Card className="border-2">
                    <CardContent className="flex flex-col items-center gap-2 py-6">
                      <span className="text-5xl font-bold">{report.score}</span>
                      <span className="text-sm text-muted-foreground">/100</span>
                      <Badge className={cn("text-sm", levelInfo.bg)}>
                        Niveau {report.level} — {levelInfo.label}
                      </Badge>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="flex flex-col gap-3 py-6">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Conformes</span>
                        <span className="font-semibold text-emerald-600">{report.stats.passed}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Non conformes</span>
                        <span className="font-semibold text-red-600">{report.stats.failed}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Avertissements</span>
                        <span className="font-semibold text-yellow-600">{report.stats.warning}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Non vérifiés</span>
                        <span className="font-semibold text-muted-foreground">{report.stats.not_checked}</span>
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="flex flex-col gap-2 py-6">
                      <span className="text-sm font-medium">Résumé</span>
                      <p className="text-sm text-muted-foreground">
                        {report.stats.total_checks} contrôles vérifiés.{" "}
                        {report.stats.failed > 0
                          ? `${report.stats.failed} point(s) nécessitent une action corrective.`
                          : "Tous les points vérifiés sont conformes."}
                      </p>
                    </CardContent>
                  </Card>
                </div>

                <Separator />

                {/* Findings by category */}
                <div>
                  <h3 className="mb-4 text-lg font-semibold">Détail des contrôles</h3>
                  <Accordion type="multiple" className="flex flex-col gap-2">
                    {Array.from(groupedFindings.entries()).map(([category, findings]) => {
                      const failCount = findings.filter((f) => f.status === "fail").length;
                      const warnCount = findings.filter((f) => f.status === "warning").length;
                      return (
                        <AccordionItem key={category} value={category} className="rounded-lg border px-4">
                          <AccordionTrigger className="hover:no-underline">
                            <div className="flex items-center gap-3">
                              <span className="font-medium capitalize">{category.replace(/_/g, " ")}</span>
                              <span className="text-sm text-muted-foreground">
                                {findings.length} contrôle(s)
                              </span>
                              {failCount > 0 && (
                                <Badge variant="destructive" className="text-xs">
                                  {failCount} échoué(s)
                                </Badge>
                              )}
                              {warnCount > 0 && (
                                <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 text-xs">
                                  {warnCount} avert.
                                </Badge>
                              )}
                            </div>
                          </AccordionTrigger>
                          <AccordionContent>
                            <div className="flex flex-col gap-3 pb-2">
                              {findings.map((finding) => (
                                <div
                                  key={finding.vuln_id}
                                  className={cn(
                                    "rounded-lg border p-4",
                                    finding.status === "fail" && "border-red-200 bg-red-50/50 dark:border-red-900 dark:bg-red-950/20",
                                    finding.status === "warning" && "border-yellow-200 bg-yellow-50/50 dark:border-yellow-900 dark:bg-yellow-950/20"
                                  )}
                                >
                                  <div className="flex items-start gap-3">
                                    {findingStatusIcon(finding.status)}
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2">
                                        <span className="font-medium">{finding.title}</span>
                                        <Badge variant="outline" className="text-xs">
                                          Niveau {finding.level}
                                        </Badge>
                                        <Badge
                                          variant={finding.status === "fail" ? "destructive" : finding.status === "pass" ? "default" : "secondary"}
                                          className={cn("text-xs", finding.status === "pass" && "bg-emerald-600")}
                                        >
                                          {findingStatusLabel(finding.status)}
                                        </Badge>
                                      </div>
                                      {finding.description && (
                                        <p className="mt-1 text-sm text-muted-foreground">
                                          {finding.description}
                                        </p>
                                      )}
                                      {finding.evidence && (
                                        <p className="mt-1 text-xs font-mono text-muted-foreground">
                                          {finding.evidence}
                                        </p>
                                      )}
                                      {finding.recommendation && finding.status !== "pass" && (
                                        <div className="mt-2 rounded bg-muted p-2">
                                          <span className="text-xs font-medium">Recommandation :</span>
                                          <p className="text-xs text-muted-foreground">
                                            {finding.recommendation}
                                          </p>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      );
                    })}
                  </Accordion>
                </div>
              </div>
            ) : !report ? (
              <div className="flex flex-col items-center gap-4 py-12">
                <FileSearch className="size-12 text-muted-foreground" />
                <p className="text-muted-foreground">
                  Cliquez sur « Lancer l&apos;analyse ANSSI » pour générer le rapport de sécurité.
                </p>
              </div>
            ) : null}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
