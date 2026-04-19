"use client";

import { Suspense, useEffect, useState, useCallback, useMemo } from "react";
import {
  Radar,
  Play,
  Trash2,
  Eye,
  Loader2,
  Monitor,
  Terminal,
  AlertCircle,
  Check,
  X,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
import { TableSkeleton } from "@/components/skeletons";
import { cn } from "@/lib/utils";
import { useRef } from "react";
import { toast } from "sonner";
import { agentsApi, entreprisesApi } from "@/services/api";
import type { Agent, AgentTask, AgentTaskStatus, Entreprise } from "@/types";
import { LaunchScanDialog } from "./components/launch-scan-dialog";
import { AgentTaskDetail } from "./components/agent-task-detail";

const SCAN_TYPE_LABELS: Record<string, string> = {
  discovery: "Decouverte",
  port_scan: "Ports",
  full: "Complet",
  custom: "Personnalise",
};

export default function ScannerPage() {
  return (
    <Suspense fallback={<div className="p-6">Chargement…</div>}>
      <ScannerContent />
    </Suspense>
  );
}

function ScannerContent() {
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentTasks, setAgentTasks] = useState<AgentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLaunch, setShowLaunch] = useState(false);
  const [filterEntrepriseId, setFilterEntrepriseId] = useState<number>(0);

  const [selectedTask, setSelectedTask] = useState<AgentTask | null>(null);
  const [showTaskDetail, setShowTaskDetail] = useState(false);

  const [agentTaskUuid, setAgentTaskUuid] = useState<string | null>(null);
  const [agentLogs, setAgentLogs] = useState<string[]>([]);
  const agentLogsRef = useRef<HTMLDivElement>(null);

  const hasRunningTasks = useMemo(
    () => agentTasks.some((t) => t.status === "running" || t.status === "pending"),
    [agentTasks]
  );

  const fetchEntreprises = useCallback(async () => {
    try {
      const res = await entreprisesApi.list(1, 100);
      setEntreprises(res.items);
    } catch { /* silent */ }
  }, []);

  const fetchAgents = useCallback(async () => {
    try { setAgents(await agentsApi.list()); } catch { /* silent */ }
  }, []);

  const fetchAgentTasks = useCallback(async () => {
    try {
      setAgentTasks(await agentsApi.listTasks("nmap"));
    } catch {
      toast.error("Erreur lors du chargement des taches agent");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEntreprises();
    fetchAgents();
    fetchAgentTasks();
  }, [fetchEntreprises, fetchAgents, fetchAgentTasks]);

  // Poll running tasks every 3s
  useEffect(() => {
    if (!hasRunningTasks) return;
    const id = setInterval(fetchAgentTasks, 3000);
    return () => clearInterval(id);
  }, [hasRunningTasks, fetchAgentTasks]);

  // WebSocket: live status/progress pour toutes les taches visibles
  useEffect(() => {
    const token = document.cookie.match(/aa_access_token=([^;]+)/)?.[1];
    if (!token) return;

    const wsBase =
      process.env.NEXT_PUBLIC_WS_URL ||
      `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.hostname}:8000`;
    const wsUrl = `${wsBase}/ws/user?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const taskUuid = msg.data?.task_uuid as string | undefined;
        if (!taskUuid) return;

        const ALLOWED_STATUSES: AgentTaskStatus[] = ["pending", "dispatched", "running", "completed", "failed", "cancelled"];
        const isStatus = (v: unknown): v is AgentTaskStatus =>
          typeof v === "string" && (ALLOWED_STATUSES as string[]).includes(v);
        const isTerminal = (s: AgentTaskStatus | undefined) =>
          s === "completed" || s === "failed" || s === "cancelled";

        if (msg.type === "task_progress") {
          const raw = msg.data.progress ?? msg.data.percent;
          const pct = typeof raw === "number" ? Math.max(0, Math.min(100, Math.round(raw))) : null;
          if (pct !== null) {
            setAgentTasks((prev) =>
              prev.map((t) =>
                t.task_uuid === taskUuid
                  ? { ...t, progress: pct, status: isTerminal(t.status) ? t.status : "running" }
                  : t
              )
            );
          }
          if (taskUuid === agentTaskUuid) {
            const lines = msg.data.output_lines as string[] | undefined;
            if (lines?.length) setAgentLogs((prev) => [...prev, ...lines]);
          }
        }

        if (msg.type === "task_status") {
          const rawStatus = msg.data.status;
          const status = isStatus(rawStatus) ? rawStatus : undefined;
          if (status) {
            setAgentTasks((prev) =>
              prev.map((t) => (t.task_uuid === taskUuid ? { ...t, status } : t))
            );
          }
          if (taskUuid === agentTaskUuid) {
            setAgentLogs((prev) => [...prev, `[STATUS] ${status ?? rawStatus}`]);
            if (status === "completed" || status === "failed") {
              setAgentLogs((prev) => [
                ...prev,
                status === "completed"
                  ? "[DONE] Scan termine avec succes"
                  : `[ERREUR] ${msg.data.error_message || "Echec du scan"}`,
              ]);
              fetchAgentTasks();
            }
          } else if (status === "completed" || status === "failed" || status === "cancelled") {
            fetchAgentTasks();
          }
        }

        if (msg.type === "task_result" && taskUuid === agentTaskUuid) {
          setAgentLogs((prev) => [...prev, "[RESULT] Resultats recus"]);
          fetchAgentTasks();
        }
      } catch { /* ignore parse errors */ }
    };

    ws.onerror = () => {
      if (agentTaskUuid) {
        setAgentLogs((prev) => [...prev, "[WS] Erreur de connexion WebSocket"]);
      }
    };

    return () => ws.close();
  }, [agentTaskUuid, fetchAgentTasks]);

  // Auto-scroll agent logs
  useEffect(() => {
    if (agentLogsRef.current) {
      agentLogsRef.current.scrollTop = agentLogsRef.current.scrollHeight;
    }
  }, [agentLogs]);

  const handleAgentDispatched = (taskUuid: string) => {
    setAgentTaskUuid(taskUuid);
    setAgentLogs(["[DISPATCH] Tache nmap envoyee a l'agent — en attente d'execution..."]);
    fetchAgentTasks();
  };

  const handleViewTask = (task: AgentTask) => {
    setSelectedTask(task);
    setShowTaskDetail(true);
  };

  const handleDeleteTask = async (taskUuid: string) => {
    try {
      await agentsApi.deleteTask(taskUuid);
      toast.success("Tache supprimee");
      fetchAgentTasks();
    } catch {
      toast.error("Erreur lors de la suppression");
    }
  };

  const getAgentName = (agentId: number) =>
    agents.find((a) => a.id === agentId)?.name || `Agent #${agentId}`;

  const filteredAgentTasks = useMemo(() => {
    if (!filterEntrepriseId) return agentTasks;
    return agentTasks.filter((t) => {
      const params = t.parameters as Record<string, unknown>;
      return params?.entreprise_id === filterEntrepriseId;
    });
  }, [agentTasks, filterEntrepriseId]);

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Radar className="size-6" />
            Scanner Reseau
          </h1>
          <p className="text-muted-foreground">
            Decouverte et inventaire automatique via Nmap — execute par un agent distant
          </p>
        </div>
        <Button onClick={() => setShowLaunch(true)}>
          <Play data-icon="inline-start" />
          Lancer un scan
        </Button>
      </div>

      {/* Agent tasks list */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Monitor className="size-4" />
                  Historique des scans agent
                  {hasRunningTasks && (
                    <Badge className="gap-1 bg-blue-500/10 text-blue-600 border-blue-200 dark:border-blue-800 dark:text-blue-400 text-xs">
                      <Loader2 className="size-3 animate-spin" />
                      {agentTasks.filter((t) => t.status === "running" || t.status === "pending").length} en cours
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>{filteredAgentTasks.length} scan(s) agent</CardDescription>
              </div>
            </div>
            {/* Filtre entreprise */}
            <div className="flex items-center gap-2">
              <Label className="text-sm whitespace-nowrap">Filtrer par entreprise :</Label>
              <Select
                value={filterEntrepriseId ? String(filterEntrepriseId) : "all"}
                onValueChange={(v) => setFilterEntrepriseId(v === "all" ? 0 : Number(v))}
              >
                <SelectTrigger className="w-[220px]">
                  <SelectValue placeholder="Toutes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="all">Toutes les entreprises</SelectItem>
                    {entreprises.map((e) => (
                      <SelectItem key={e.id} value={String(e.id)}>{e.nom}</SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <TableSkeleton rows={3} cols={8} />
          ) : filteredAgentTasks.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Monitor className="size-12 mx-auto mb-4 opacity-40" />
              <p>Aucun scan agent</p>
              <p className="text-sm">Lancez un scan pour le dispatcher vers un agent distant</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Entreprise</TableHead>
                  <TableHead>Site</TableHead>
                  <TableHead>Cible</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Progression</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAgentTasks.map((task) => {
                  const params = task.parameters as Record<string, string>;
                  return (
                    <TableRow key={task.id}>
                      <TableCell className="whitespace-nowrap">
                        {new Date(
                          task.created_at.endsWith("Z") || task.created_at.includes("+")
                            ? task.created_at
                            : task.created_at + "Z"
                        ).toLocaleDateString("fr-FR", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </TableCell>
                      <TableCell>
                        <TaskStatusBadge
                          status={task.status}
                          errorMessage={task.error_message}
                        />
                      </TableCell>
                      <TableCell>{task.entreprise_name || "—"}</TableCell>
                      <TableCell>{task.site_name || "—"}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {params?.target || "—"}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {SCAN_TYPE_LABELS[params?.scan_type || "discovery"] || params?.scan_type || "—"}
                        </Badge>
                      </TableCell>
                      <TableCell>{getAgentName(task.agent_id)}</TableCell>
                      <TableCell>
                        {task.status === "running" ? (
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-16 bg-blue-100 dark:bg-blue-900/30 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-blue-500 rounded-full transition-all"
                                style={{ width: `${task.progress}%` }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground">{task.progress}%</span>
                          </div>
                        ) : task.status === "completed" ? (
                          <span className="text-xs text-green-600">100%</span>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex gap-1 justify-end">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleViewTask(task)}
                            disabled={task.status === "pending"}
                          >
                            <Eye />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                disabled={task.status === "running"}
                              >
                                <Trash2 className="text-destructive" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Supprimer cette tache ?</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Cette tache et ses resultats seront definitivement supprimes.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Annuler</AlertDialogCancel>
                                <AlertDialogAction onClick={() => handleDeleteTask(task.task_uuid)}>
                                  Supprimer
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Launch dialog */}
      <LaunchScanDialog
        open={showLaunch}
        onOpenChange={setShowLaunch}
        onAgentDispatched={handleAgentDispatched}
      />

      {/* Agent task logs (live stream) */}
      {agentTaskUuid && agentLogs.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Terminal className="size-4" />
              Logs agent — tache nmap
              <Badge variant="outline" className="font-mono text-xs">
                {agentTaskUuid.slice(0, 8)}
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                className="ml-auto"
                onClick={() => { setAgentTaskUuid(null); setAgentLogs([]); }}
              >
                <X className="size-3" />
                Fermer
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              ref={agentLogsRef}
              className="bg-zinc-950 rounded-lg p-4 max-h-[300px] overflow-y-auto font-mono text-xs leading-relaxed"
            >
              {agentLogs.map((line, i) => (
                <div
                  key={i}
                  className={cn(
                    "whitespace-pre-wrap",
                    line.startsWith("[ERREUR]") && "text-red-400",
                    line.startsWith("[DONE]") && "text-green-400",
                    line.startsWith("[STATUS]") && "text-yellow-400",
                    line.startsWith("[DISPATCH]") && "text-blue-400",
                    !line.startsWith("[") && "text-zinc-300"
                  )}
                >
                  {line}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agent task detail */}
      <AgentTaskDetail
        task={selectedTask}
        open={showTaskDetail}
        onOpenChange={setShowTaskDetail}
        agentName={selectedTask ? getAgentName(selectedTask.agent_id) : ""}
      />
    </div>
  );
}

function TaskStatusBadge({
  status,
  errorMessage,
}: {
  status: string;
  errorMessage: string | null;
}) {
  if (status === "pending") {
    return (
      <Badge variant="outline" className="gap-1">
        <Loader2 className="size-3 animate-spin" />
        En attente
      </Badge>
    );
  }
  if (status === "running") {
    return (
      <Badge className="gap-1.5 bg-blue-500/10 text-blue-600 border-blue-200 dark:border-blue-800 dark:text-blue-400">
        <Loader2 className="size-3 animate-spin" />
        En cours
      </Badge>
    );
  }
  if (status === "failed") {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="destructive" className="gap-1 cursor-help">
              <AlertCircle className="size-3" />
              Echoue
            </Badge>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs">
            <p className="text-sm">{errorMessage || "Erreur inconnue"}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }
  return (
    <Badge variant="outline" className="gap-1 text-green-600 border-green-200 dark:border-green-800 dark:text-green-400">
      <Check className="size-3" />
      Termine
    </Badge>
  );
}
