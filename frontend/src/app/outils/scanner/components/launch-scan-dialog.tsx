"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Play, Server, Monitor, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { entreprisesApi, sitesApi, agentsApi, scansApi } from "@/services/api";
import type { Agent, Entreprise, Site } from "@/types";
import { toast } from "sonner";

const SCAN_TYPES = [
  { value: "discovery", label: "Decouverte (ping)", description: "Scan rapide pour detecter les hotes actifs", args: "-sn" },
  { value: "port_scan", label: "Scan de ports (top 1000)", description: "Detection des services sur les 1000 ports les plus courants", args: "-sV --top-ports 1000" },
  { value: "full", label: "Scan complet", description: "Tous les ports + detection OS + scripts NSE", args: "-sV -sC -O -p-" },
  { value: "custom", label: "Personnalise", description: "Ecrivez votre propre commande Nmap", args: "" },
] as const;

interface LaunchScanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLaunched: () => void;
  onAgentDispatched: (taskUuid: string) => void;
}

export function LaunchScanDialog({ open, onOpenChange, onLaunched, onAgentDispatched }: LaunchScanDialogProps) {
  // Mode
  const [scanMode, setScanMode] = useState<"local" | "agent">("local");

  // Selects
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [entrepriseId, setEntrepriseId] = useState<number>(0);
  const [siteId, setSiteId] = useState<number>(0);
  const [selectedAgentUuid, setSelectedAgentUuid] = useState("");

  // Form
  const [nom, setNom] = useState("");
  const [target, setTarget] = useState("");
  const [scanType, setScanType] = useState<string>("discovery");
  const [customArgs, setCustomArgs] = useState("");
  const [notes, setNotes] = useState("");
  const [launching, setLaunching] = useState(false);

  // Fetch entreprises + agents on open
  useEffect(() => {
    if (!open) return;
    entreprisesApi.list(1, 100).then((r) => setEntreprises(r.items)).catch(() => {});
    agentsApi.list().then(setAgents).catch(() => {});
  }, [open]);

  // Fetch sites when entreprise changes
  useEffect(() => {
    if (!entrepriseId) { setSites([]); return; }
    sitesApi.list(1, 100, entrepriseId).then((r) => setSites(r.items)).catch(() => {});
    setSiteId(0); // reset site selection
  }, [entrepriseId]);

  const nmapAgents = useMemo(
    () => agents.filter((a) => a.status === "active" && a.allowed_tools.includes("nmap")),
    [agents]
  );

  const filteredSites = useMemo(
    () => sites.filter((s) => !entrepriseId || s.entreprise_id === entrepriseId),
    [sites, entrepriseId]
  );

  const commandPreview = useMemo(() => {
    const t = target || "<cible>";
    if (scanType === "custom") return `nmap ${customArgs.trim() || "<arguments>"} ${t}`;
    const def = SCAN_TYPES.find((s) => s.value === scanType);
    return `nmap ${def?.args || "-sn"} ${t}`;
  }, [target, scanType, customArgs]);

  const reset = useCallback(() => {
    setNom(""); setTarget(""); setCustomArgs(""); setNotes("");
    setScanType("discovery"); setScanMode("local");
    setEntrepriseId(0); setSiteId(0); setSelectedAgentUuid("");
  }, []);

  const handleLaunch = async () => {
    if (!siteId || !target) {
      toast.error("Veuillez selectionner un site et saisir une cible");
      return;
    }
    if (scanType === "custom" && !customArgs.trim()) {
      toast.error("Veuillez saisir les arguments Nmap personnalises");
      return;
    }

    setLaunching(true);
    try {
      if (scanMode === "agent") {
        if (!selectedAgentUuid) { toast.error("Veuillez selectionner un agent"); return; }
        const res = await agentsApi.dispatch({
          agent_uuid: selectedAgentUuid,
          tool: "nmap",
          parameters: {
            target,
            scan_type: scanType,
            custom_args: scanType === "custom" ? customArgs.trim() : undefined,
            site_id: siteId,
            entreprise_id: entrepriseId,
            nom: nom.trim() || undefined,
          },
        });
        const taskUuid = (res as { task_uuid?: string }).task_uuid;
        if (taskUuid) onAgentDispatched(taskUuid);
        toast.success("Scan dispatche vers l'agent distant");
      } else {
        await scansApi.launch({
          nom: nom.trim() || undefined,
          site_id: siteId,
          target,
          scan_type: scanType as "discovery" | "port_scan" | "full" | "custom",
          custom_args: scanType === "custom" ? customArgs.trim() : undefined,
          notes: notes || undefined,
        });
        toast.success("Scan lance en arriere-plan");
        onLaunched();
      }
      onOpenChange(false);
      reset();
    } catch (err: unknown) {
      const axErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axErr?.response?.data?.detail || "Erreur lors du lancement");
    } finally {
      setLaunching(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Lancer un scan reseau</DialogTitle>
          <DialogDescription>Configurez les parametres du scan Nmap</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          {/* Mode Local / Agent */}
          <div>
            <Label className="mb-1.5 block">Execution</Label>
            <Tabs value={scanMode} onValueChange={(v) => setScanMode(v as "local" | "agent")}>
              <TabsList className="w-full">
                <TabsTrigger value="local" className="flex-1 gap-1.5">
                  <Server className="size-3.5" />
                  Local (serveur)
                </TabsTrigger>
                <TabsTrigger value="agent" className="flex-1 gap-1.5" disabled={nmapAgents.length === 0}>
                  <Monitor className="size-3.5" />
                  Agent distant
                  {nmapAgents.length > 0 && (
                    <Badge variant="secondary" className="ml-1 text-[10px] px-1 py-0">{nmapAgents.length}</Badge>
                  )}
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Entreprise */}
          <div>
            <Label>Entreprise *</Label>
            <Select value={entrepriseId ? String(entrepriseId) : ""} onValueChange={(v) => setEntrepriseId(Number(v))}>
              <SelectTrigger><SelectValue placeholder="Selectionner une entreprise" /></SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {entreprises.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>{e.nom}</SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>

          {/* Site (filtered by entreprise) */}
          <div>
            <Label>Site *</Label>
            <Select
              value={siteId ? String(siteId) : ""}
              onValueChange={(v) => setSiteId(Number(v))}
              disabled={!entrepriseId}
            >
              <SelectTrigger><SelectValue placeholder={entrepriseId ? "Selectionner un site" : "Choisir une entreprise d'abord"} /></SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {filteredSites.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>{s.nom}</SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>

          {/* Agent (only in agent mode) */}
          {scanMode === "agent" && nmapAgents.length > 0 && (
            <div>
              <Label>Agent *</Label>
              <Select value={selectedAgentUuid} onValueChange={setSelectedAgentUuid}>
                <SelectTrigger><SelectValue placeholder="Selectionner un agent" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {nmapAgents.map((a) => (
                      <SelectItem key={a.agent_uuid} value={a.agent_uuid}>
                        {a.name} {a.last_ip ? `(${a.last_ip})` : ""}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Nom */}
          <div>
            <Label>Nom du scan (optionnel)</Label>
            <Input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Ex : VLAN 10 - MGT" />
          </div>

          {/* Cible */}
          <div>
            <Label>Cible (IP, plage CIDR) *</Label>
            <Input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="192.168.1.0/24" />
          </div>

          {/* Type de scan */}
          <div>
            <Label>Type de scan</Label>
            <div className="grid grid-cols-2 gap-2 mt-1">
              {SCAN_TYPES.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setScanType(type.value)}
                  className={cn(
                    "text-left p-3 rounded-lg border-2 transition-colors cursor-pointer",
                    scanType === type.value ? "border-primary bg-primary/5" : "border-muted hover:border-muted-foreground/30"
                  )}
                >
                  <div className="font-medium text-sm">{type.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{type.description}</div>
                  {type.args && <code className="text-[10px] text-muted-foreground font-mono mt-1 block">{type.args}</code>}
                </button>
              ))}
            </div>
          </div>

          {scanType === "custom" && (
            <div>
              <Label>Arguments Nmap personnalises *</Label>
              <Input value={customArgs} onChange={(e) => setCustomArgs(e.target.value)} placeholder="-sV -p 22,80,443" className="font-mono text-sm" />
            </div>
          )}

          {/* Preview */}
          <div className="rounded-lg bg-zinc-950 p-3 mt-2">
            <div className="flex items-center gap-2 text-zinc-400 text-xs mb-1">
              <Terminal className="size-3" /> Commande
            </div>
            <code className="text-green-400 text-sm font-mono break-all">$ {commandPreview}</code>
          </div>

          {/* Notes */}
          <div>
            <Label>Notes (optionnel)</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Notes sur ce scan..." rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={handleLaunch} disabled={launching}>
            <Play data-icon="inline-start" />
            {launching ? "Lancement..." : "Lancer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
