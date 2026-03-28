"use client";

import { useEffect, useState } from "react";
import { Download, Monitor, Globe, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { agentsApi, equipementsApi } from "@/services/api";
import type { AgentTask, TaskArtifact, TypeEquipement } from "@/types";
import { toast } from "sonner";

/** Structure retournee par l'agent nmap — champs courts (ip, mac, os)
 *  avec fallback vers les noms longs du serveur local (ip_address, mac_address, os_guess). */
interface NmapHostRaw {
  ip?: string;
  ip_address?: string;
  hostname?: string;
  mac?: string;
  mac_address?: string;
  vendor?: string;
  os?: string;
  os_guess?: string;
  status?: string;
  ports?: Array<{
    port?: number;
    port_number?: number;
    protocol?: string;
    proto?: string;
    state?: string;
    service?: string;
    service_name?: string;
  }>;
}

interface NmapHost {
  ip: string;
  hostname: string;
  mac: string;
  vendor: string;
  os: string;
  ports: Array<{ port: number; protocol: string; service: string }>;
}

function normalizeHost(raw: NmapHostRaw): NmapHost {
  return {
    ip: raw.ip || raw.ip_address || "",
    hostname: raw.hostname || "",
    mac: raw.mac || raw.mac_address || "",
    vendor: raw.vendor || "",
    os: raw.os || raw.os_guess || "",
    ports: (raw.ports || []).map((p) => ({
      port: p.port ?? p.port_number ?? 0,
      protocol: p.proto || p.protocol || "tcp",
      service: p.service || p.service_name || "",
    })),
  };
}

interface AgentTaskDetailProps {
  task: AgentTask | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentName: string;
}

export function AgentTaskDetail({ task, open, onOpenChange, agentName }: AgentTaskDetailProps) {
  const [artifacts, setArtifacts] = useState<TaskArtifact[]>([]);
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    if (!task || !open) { setArtifacts([]); return; }
    agentsApi.getTaskArtifacts(task.task_uuid).then(setArtifacts).catch(() => setArtifacts([]));
  }, [task, open]);

  if (!task) return null;

  const params = task.parameters as Record<string, unknown>;
  const summary = task.result_summary as Record<string, unknown> | null;
  const rawHosts = (summary?.hosts as NmapHostRaw[]) || [];
  const hosts = rawHosts.map(normalizeHost);
  const siteId = params?.site_id as number | undefined;

  const totalPorts = hosts.reduce((sum, h) => sum + h.ports.length, 0);

  // Deviner le type d'equipement depuis les ports ouverts
  const guessType = (host: NmapHost): TypeEquipement => {
    const ports = host.ports.map((p) => p.port);
    if (ports.includes(515) || ports.includes(631) || ports.includes(9100)) return "printer";
    if (ports.includes(554) || ports.includes(8554)) return "camera";
    if (ports.includes(161) && !ports.includes(22) && !ports.includes(80)) return "reseau";
    if (ports.includes(443) && ports.includes(22)) return "firewall";
    return "serveur";
  };

  const handleImportEquipments = async () => {
    if (!siteId || hosts.length === 0) {
      toast.error("Aucun hote a importer ou site non defini");
      return;
    }
    setImporting(true);
    let created = 0;
    let skipped = 0;
    for (const host of hosts) {
      if (!host.ip) continue;
      try {
        await equipementsApi.create({
          site_id: siteId,
          hostname: host.hostname || host.ip,
          ip_address: host.ip,
          type_equipement: guessType(host),
          os_detected: host.os || undefined,
          fabricant: host.vendor || undefined,
          mac_address: host.mac || undefined,
          status_audit: "A_AUDITER",
        });
        created++;
      } catch (err: unknown) {
        const axErr = err as { response?: { status?: number } };
        if (axErr?.response?.status === 409 || axErr?.response?.status === 400) {
          skipped++;
        } else {
          skipped++;
        }
      }
    }
    setImporting(false);
    toast.success(`${created} equipement(s) importe(s), ${skipped} ignore(s) (doublons ou erreurs)`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[90vw] w-full lg:max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Monitor className="size-5" />
            Scan agent — {(params?.target as string) || "—"}
          </DialogTitle>
          <DialogDescription>
            Agent : {agentName} — Statut : {task.status}
            {task.error_message && (
              <span className="text-destructive block mt-1">{task.error_message}</span>
            )}
          </DialogDescription>
        </DialogHeader>

        {/* Summary badges */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="flex flex-col items-center p-3 rounded-lg bg-muted min-w-[80px]">
            <span className="text-2xl font-bold">{hosts.length}</span>
            <span className="text-xs text-muted-foreground">Hotes</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded-lg bg-muted min-w-[80px]">
            <span className="text-2xl font-bold">{totalPorts}</span>
            <span className="text-xs text-muted-foreground">Ports ouverts</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded-lg bg-muted min-w-[80px]">
            <span className="text-sm font-mono">{(params?.target as string) || "—"}</span>
            <span className="text-xs text-muted-foreground">Cible</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded-lg bg-muted min-w-[80px]">
            <span className="text-sm">{agentName}</span>
            <span className="text-xs text-muted-foreground">Agent</span>
          </div>
        </div>

        {/* Hosts table */}
        {hosts.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold">Hotes decouverts</h4>
              {siteId && task.status === "completed" && (
                <Button size="sm" variant="outline" onClick={handleImportEquipments} disabled={importing}>
                  <Upload data-icon="inline-start" />
                  {importing ? "Import..." : "Importer les equipements"}
                </Button>
              )}
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>IP</TableHead>
                  <TableHead>Hostname</TableHead>
                  <TableHead>MAC</TableHead>
                  <TableHead>Vendor</TableHead>
                  <TableHead>OS</TableHead>
                  <TableHead>Ports ouverts</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {hosts.map((host, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-mono font-semibold whitespace-nowrap">{host.ip || "—"}</TableCell>
                    <TableCell className="whitespace-nowrap">{host.hostname || "—"}</TableCell>
                    <TableCell className="font-mono text-xs whitespace-nowrap">{host.mac || "—"}</TableCell>
                    <TableCell className="whitespace-nowrap">{host.vendor || "—"}</TableCell>
                    <TableCell className="text-sm max-w-[200px] truncate">{host.os || "—"}</TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap max-w-[300px]">
                        {host.ports.slice(0, 8).map((p, j) => (
                          <Badge key={j} variant="outline" className="text-[10px] font-mono">
                            {p.port}/{p.service || p.protocol}
                          </Badge>
                        ))}
                        {host.ports.length > 8 && (
                          <Badge variant="secondary" className="text-[10px]">
                            +{host.ports.length - 8}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {hosts.length === 0 && summary && (
          <div className="rounded-lg bg-zinc-950 p-3 max-h-[200px] overflow-y-auto">
            <div className="text-zinc-400 text-xs mb-1">Resultat brut</div>
            <pre className="text-zinc-300 text-xs font-mono whitespace-pre-wrap">
              {JSON.stringify(summary, null, 2)}
            </pre>
          </div>
        )}

        {/* Artifacts */}
        {artifacts.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Fichiers resultat ({artifacts.length})</h4>
            <div className="flex flex-col gap-2">
              {artifacts.map((a) => (
                <div key={a.id} className="flex items-center justify-between p-2 rounded border bg-muted/50">
                  <div className="flex items-center gap-2 min-w-0">
                    <Download className="size-4 text-muted-foreground shrink-0" />
                    <span className="text-sm font-mono truncate">{a.original_filename}</span>
                    <span className="text-xs text-muted-foreground">({Math.round(a.file_size / 1024)} Ko)</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(
                      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}${a.download_url}`,
                      "_blank"
                    )}
                  >
                    <Download className="size-3" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
