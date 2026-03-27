"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  Bot,
  Plus,
  Loader2,
  Copy,
  Check,
  ShieldOff,
  Clock,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";
import { agentsApi } from "@/services/api";
import { getAccessToken } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { Agent, AgentCreateResponse, AgentStatus } from "@/types";

// ── Constants ──
const AVAILABLE_TOOLS = ["nmap", "oradad", "ad_collector"] as const;
const TOOL_LABELS: Record<string, string> = {
  nmap: "Nmap",
  oradad: "ORADAD",
  ad_collector: "AD Collector",
};

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.hostname}:8000`
    : "ws://localhost:8000");

// ── Helpers ──
function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return "Jamais";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return "À l'instant";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `Il y a ${diffMin} min`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `Il y a ${diffHours}h`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `Il y a ${diffDays}j`;
  const diffMonths = Math.floor(diffDays / 30);
  return `Il y a ${diffMonths} mois`;
}

function statusBadge(status: AgentStatus) {
  switch (status) {
    case "active":
      return <Badge variant="default" className="bg-emerald-600 hover:bg-emerald-700">Actif</Badge>;
    case "pending":
      return <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-700 dark:text-yellow-400">En attente</Badge>;
    case "revoked":
      return <Badge variant="destructive">Révoqué</Badge>;
    case "offline":
      return <Badge variant="outline" className="text-muted-foreground">Hors ligne</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function truncateUuid(uuid: string): string {
  return uuid.substring(0, 8) + "…";
}

// ── Page ──
export default function AgentsPage() {
  const { user } = useAuth();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  // Create dialog
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newAgentName, setNewAgentName] = useState("");
  const [selectedTools, setSelectedTools] = useState<string[]>([...AVAILABLE_TOOLS]);

  // Enrollment dialog
  const [showEnrollmentDialog, setShowEnrollmentDialog] = useState(false);
  const [enrollmentData, setEnrollmentData] = useState<AgentCreateResponse | null>(null);
  const [codeCopied, setCodeCopied] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // Revoke dialog
  const [revokeTarget, setRevokeTarget] = useState<Agent | null>(null);
  const [revoking, setRevoking] = useState(false);

  // UUID copy
  const [copiedUuid, setCopiedUuid] = useState<string | null>(null);

  // WebSocket ref
  const wsRef = useRef<WebSocket | null>(null);

  // ── Role check ──
  const hasAccess = user?.role === "admin" || user?.role === "auditeur";
  const isAdmin = user?.role === "admin";

  // ── Fetch agents ──
  const fetchAgents = useCallback(async () => {
    try {
      const data = await agentsApi.list();
      setAgents(data);
    } catch {
      toast.error("Erreur lors du chargement des agents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (hasAccess) fetchAgents();
    else setLoading(false);
  }, [hasAccess, fetchAgents]);

  // ── WebSocket for real-time status ──
  useEffect(() => {
    if (!hasAccess) return;
    const token = getAccessToken();
    if (!token) return;

    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/ws/user?token=${token}`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "agent_status") {
            const { agent_uuid, status } = msg.data;
            setAgents((prev) =>
              prev.map((a) =>
                a.agent_uuid === agent_uuid ? { ...a, status } : a
              )
            );
          }
        } catch {
          // ignore non-JSON messages
        }
      };

      ws.onclose = (event) => {
        if (event.code !== 1000) {
          // Reconnect after 5s on abnormal close
          setTimeout(connect, 5000);
        }
      };
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000);
        wsRef.current = null;
      }
    };
  }, [hasAccess]);

  // ── Countdown timer for enrollment code ──
  useEffect(() => {
    if (!showEnrollmentDialog || countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [showEnrollmentDialog, countdown]);

  // ── Create agent ──
  const handleCreate = async () => {
    if (!newAgentName.trim()) {
      toast.error("Le nom de l'agent est requis");
      return;
    }
    if (selectedTools.length === 0) {
      toast.error("Sélectionnez au moins un outil");
      return;
    }
    setCreating(true);
    try {
      const result = await agentsApi.create({
        name: newAgentName.trim(),
        allowed_tools: selectedTools,
      });
      setEnrollmentData(result);
      setShowCreateDialog(false);
      setShowEnrollmentDialog(true);
      setCodeCopied(false);
      // Calculate countdown from expires_at
      const expiresAt = new Date(result.expires_at).getTime();
      const now = Date.now();
      setCountdown(Math.max(0, Math.floor((expiresAt - now) / 1000)));
      // Refresh agent list
      await fetchAgents();
      toast.success("Agent créé avec succès");
    } catch {
      toast.error("Erreur lors de la création de l'agent");
    } finally {
      setCreating(false);
    }
  };

  // ── Copy enrollment code ──
  const handleCopyCode = async () => {
    if (!enrollmentData) return;
    try {
      await navigator.clipboard.writeText(enrollmentData.enrollment_code);
      setCodeCopied(true);
      toast.success("Code copié");
      setTimeout(() => setCodeCopied(false), 3000);
    } catch {
      toast.error("Impossible de copier le code");
    }
  };

  // ── Copy UUID ──
  const handleCopyUuid = async (uuid: string) => {
    try {
      await navigator.clipboard.writeText(uuid);
      setCopiedUuid(uuid);
      setTimeout(() => setCopiedUuid(null), 2000);
    } catch {
      toast.error("Impossible de copier l'UUID");
    }
  };

  // ── Revoke agent ──
  const handleRevoke = async () => {
    if (!revokeTarget) return;
    setRevoking(true);
    try {
      await agentsApi.revoke(revokeTarget.agent_uuid);
      setAgents((prev) =>
        prev.map((a) =>
          a.agent_uuid === revokeTarget.agent_uuid
            ? { ...a, status: "revoked" as const }
            : a
        )
      );
      toast.success("Agent révoqué");
    } catch {
      toast.error("Erreur lors de la révocation");
    } finally {
      setRevoking(false);
      setRevokeTarget(null);
    }
  };

  // ── Toggle tool selection ──
  const toggleTool = (tool: string) => {
    setSelectedTools((prev) =>
      prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool]
    );
  };

  // ── Reset create dialog ──
  const openCreateDialog = () => {
    setNewAgentName("");
    setSelectedTools([...AVAILABLE_TOOLS]);
    setShowCreateDialog(true);
  };

  // ── Format countdown ──
  const formatCountdown = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  // ── Access denied ──
  if (!hasAccess) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <Bot className="size-12 text-muted-foreground" />
        <p className="text-muted-foreground">
          Accès réservé aux administrateurs et auditeurs.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bot className="size-8 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Agents</h1>
            <p className="text-sm text-muted-foreground">
              Gérez les agents Windows déployés sur le réseau
            </p>
          </div>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus data-icon="inline-start" />
          Nouvel agent
        </Button>
      </div>

      {/* Agent list */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : agents.length === 0 ? (
            <div className="flex flex-col items-center gap-4 py-16">
              <Bot className="size-12 text-muted-foreground" />
              <p className="text-muted-foreground">Aucun agent enregistré</p>
              <Button variant="outline" onClick={openCreateDialog}>
                <Plus data-icon="inline-start" />
                Créer un agent
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  {isAdmin && <TableHead>Propriétaire</TableHead>}
                  <TableHead>UUID</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Dernier contact</TableHead>
                  <TableHead>IP</TableHead>
                  <TableHead className="hidden lg:table-cell">OS</TableHead>
                  <TableHead className="hidden lg:table-cell">Version</TableHead>
                  <TableHead>Outils</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.map((agent) => (
                  <TableRow key={agent.agent_uuid}>
                    <TableCell className="font-medium">{agent.name}</TableCell>
                    {isAdmin && (
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {agent.owner_name || "—"}
                        </span>
                      </TableCell>
                    )}
                    <TableCell>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => handleCopyUuid(agent.agent_uuid)}
                              className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-xs text-muted-foreground hover:bg-muted transition-colors"
                            >
                              {truncateUuid(agent.agent_uuid)}
                              {copiedUuid === agent.agent_uuid ? (
                                <Check className="size-3 text-emerald-500" />
                              ) : (
                                <Copy className="size-3" />
                              )}
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="font-mono text-xs">{agent.agent_uuid}</p>
                            <p className="text-xs text-muted-foreground">Cliquer pour copier</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </TableCell>
                    <TableCell>{statusBadge(agent.status)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5 text-sm">
                        {agent.status === "active" ? (
                          <Wifi className="size-3 text-emerald-500" />
                        ) : (
                          <WifiOff className="size-3 text-muted-foreground" />
                        )}
                        <span className="text-muted-foreground">
                          {formatRelativeTime(agent.last_seen)}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs text-muted-foreground">
                        {agent.last_ip || "—"}
                      </span>
                    </TableCell>
                    <TableCell className="hidden lg:table-cell">
                      <span className="text-sm text-muted-foreground">
                        {agent.os_info || "—"}
                      </span>
                    </TableCell>
                    <TableCell className="hidden lg:table-cell">
                      <span className="text-sm text-muted-foreground">
                        {agent.agent_version || "—"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {agent.allowed_tools.map((tool) => (
                          <Badge key={tool} variant="outline" className="text-xs">
                            {TOOL_LABELS[tool] || tool}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      {agent.status !== "revoked" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => setRevokeTarget(agent)}
                        >
                          <ShieldOff data-icon="inline-start" />
                          Révoquer
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

      {/* ── Create agent dialog ── */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouvel agent</DialogTitle>
            <DialogDescription>
              Créez un nouvel agent pour déployer sur une machine Windows.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="agent-name">Nom de l&apos;agent</Label>
              <Input
                id="agent-name"
                placeholder="ex : PC-Bureau-Jean"
                value={newAgentName}
                onChange={(e) => setNewAgentName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreate();
                }}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label>Outils autorisés</Label>
              <div className="flex flex-col gap-2">
                {AVAILABLE_TOOLS.map((tool) => (
                  <label
                    key={tool}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <Checkbox
                      checked={selectedTools.includes(tool)}
                      onCheckedChange={() => toggleTool(tool)}
                    />
                    <span className="text-sm">{TOOL_LABELS[tool]}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateDialog(false)}
            >
              Annuler
            </Button>
            <Button onClick={handleCreate} disabled={creating}>
              {creating && <Loader2 data-icon="inline-start" className="animate-spin" />}
              Créer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Enrollment code dialog ── */}
      <Dialog open={showEnrollmentDialog} onOpenChange={setShowEnrollmentDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Code d&apos;enrollment</DialogTitle>
            <DialogDescription>
              Saisissez ce code au premier lancement de l&apos;agent Windows.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center gap-6 py-6">
            {/* Enrollment code display */}
            <div className="flex flex-col items-center gap-2">
              <span className="select-all font-mono text-3xl font-bold tracking-widest">
                {enrollmentData?.enrollment_code}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyCode}
              >
                {codeCopied ? (
                  <Check data-icon="inline-start" className="text-emerald-500" />
                ) : (
                  <Copy data-icon="inline-start" />
                )}
                {codeCopied ? "Copié !" : "Copier le code"}
              </Button>
            </div>

            {/* Countdown */}
            <div className={cn(
              "flex items-center gap-2 text-sm",
              countdown <= 60 ? "text-destructive" : "text-muted-foreground"
            )}>
              <Clock className="size-4" />
              {countdown > 0 ? (
                <span>Valide encore {formatCountdown(countdown)}</span>
              ) : (
                <span className="font-medium">Code expiré</span>
              )}
            </div>

            <p className="text-center text-sm text-muted-foreground">
              Ce code est à usage unique et expire dans 10 minutes.
            </p>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowEnrollmentDialog(false)}>
              Fermer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Revoke confirmation ── */}
      <AlertDialog open={!!revokeTarget} onOpenChange={(open) => !open && setRevokeTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Révoquer l&apos;agent ?</AlertDialogTitle>
            <AlertDialogDescription>
              L&apos;agent <strong>{revokeTarget?.name}</strong> ne pourra plus se connecter
              ni exécuter de tâches. Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={revoking}>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRevoke}
              disabled={revoking}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {revoking && <Loader2 data-icon="inline-start" className="animate-spin" />}
              Révoquer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
