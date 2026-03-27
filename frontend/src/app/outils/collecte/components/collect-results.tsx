"use client";

import {
  Terminal,
  Server,
  Monitor,
  Loader2,
  Trash2,
  Eye,
  CheckCircle2,
  XCircle,
  Shield,
  Activity,
  ClipboardCheck,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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

import type { CollectResultSummary } from "@/types";

// ── Constantes ──────────────────────────────────────────────
const STATUS_LABELS: Record<string, string> = {
  running: "En cours",
  success: "Succès",
  failed: "Échec",
};

const STATUS_COLORS: Record<string, string> = {
  running: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  success: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

const METHOD_LABELS: Record<string, string> = {
  ssh: "SSH (Linux)",
  winrm: "WinRM (Windows)",
};

const PROFILE_OPTIONS: { value: string; label: string }[] = [
  { value: "linux_server", label: "Serveur Linux" },
  { value: "opnsense", label: "OPNsense" },
  { value: "stormshield", label: "Stormshield (SNS)" },
  { value: "fortigate", label: "FortiGate (FortiOS)" },
];

// ── Props ──
export interface CollectResultsProps {
  collects: CollectResultSummary[];
  loadingCollects: boolean;
  onViewDetail: (collectId: number) => void;
  onDelete: (collectId: number) => void;
  onPrefill: (collectId: number) => void;
}

export function CollectResults({
  collects,
  loadingCollects,
  onViewDetail,
  onDelete,
  onPrefill,
}: CollectResultsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="size-5" />
          Historique des collectes
          {collects.length > 0 && (
            <Badge variant="secondary">{collects.length}</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loadingCollects ? (
          <div className="flex flex-col gap-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : collects.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Terminal className="size-10 mx-auto mb-2 opacity-30" />
            <p>Aucune collecte effectuée</p>
            <p className="text-sm">Lancez une collecte SSH ou WinRM pour commencer</p>
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[60px]">#</TableHead>
                  <TableHead>Méthode</TableHead>
                  <TableHead>Cible</TableHead>
                  <TableHead>Hostname</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Durée</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {collects.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-mono text-sm">{c.id}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="gap-1">
                        {c.method === "ssh" ? (
                          c.device_profile && c.device_profile !== "linux_server" ? (
                            <Shield className="size-3" />
                          ) : (
                            <Server className="size-3" />
                          )
                        ) : (
                          <Monitor className="size-3" />
                        )}
                        {c.method === "ssh"
                          ? (PROFILE_OPTIONS.find((p) => p.value === c.device_profile)?.label ?? "SSH (Linux)")
                          : (METHOD_LABELS[c.method] || c.method)}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {c.target_host}:{c.target_port}
                    </TableCell>
                    <TableCell className="text-sm">
                      {c.hostname_collected || "—"}
                    </TableCell>
                    <TableCell>
                      {c.status === "running" ? (
                        <Badge className={STATUS_COLORS.running}>
                          <Loader2 className="size-3 animate-spin" />
                          {STATUS_LABELS.running}
                        </Badge>
                      ) : (
                        <Badge className={STATUS_COLORS[c.status]}>
                          {c.status === "success" ? (
                            <CheckCircle2 className="size-3" />
                          ) : (
                            <XCircle className="size-3" />
                          )}
                          {STATUS_LABELS[c.status]}
                        </Badge>
                      )}
                      {c.error_message && (
                        <p className="text-xs text-red-500 mt-1 max-w-[200px] truncate">
                          {c.error_message}
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      {c.summary ? (
                        c.summary.compliance_score != null ? (
                          <div className="flex items-center gap-1">
                            <span className="text-sm font-medium">
                              {c.summary.compliance_score}%
                            </span>
                            <Progress
                              value={c.summary.compliance_score}
                              className="w-16 h-2"
                            />
                          </div>
                        ) : c.summary.firewall_rules_count != null ? (
                          <span className="text-sm text-muted-foreground">
                            {c.summary.firewall_rules_count} règles
                          </span>
                        ) : (
                          "—"
                        )
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {c.duration_seconds != null ? `${c.duration_seconds}s` : "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(c.created_at).toLocaleDateString("fr-FR", {
                        day: "2-digit",
                        month: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {c.status === "success" && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => onViewDetail(c.id)}
                              title="Voir le détail"
                            >
                              <Eye />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => onPrefill(c.id)}
                              title="Pré-remplir un audit"
                            >
                              <ClipboardCheck />
                            </Button>
                          </>
                        )}
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500 hover:text-red-700"
                              title="Supprimer"
                            >
                              <Trash2 />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Supprimer cette collecte ?</AlertDialogTitle>
                              <AlertDialogDescription>
                                Cette action est irréversible. Les données collectées seront définitivement supprimées.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Annuler</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => onDelete(c.id)}
                                className="bg-red-600 hover:bg-red-700"
                              >
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
          </div>
        )}
      </CardContent>
    </Card>
  );
}
