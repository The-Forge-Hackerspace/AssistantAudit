"use client";

import { Suspense, useEffect, useState, useCallback, useMemo, useRef } from "react";
import {
  Radar,
  Play,
  Trash2,
  Eye,
  Loader2,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  Download,
  Monitor,
  Shield,
  Wifi,
  Server,
  Globe,
  Terminal,
  AlertCircle,
  Router,
  Printer,
  Video,
  Cloud,
  Phone,
  Cpu,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { scansApi, sitesApi } from "@/services/api";
import type { Scan, ScanSummary, ScanHost, Site, TypeEquipement } from "@/types";
import { toast } from "sonner";
import { TableSkeleton } from "@/components/skeletons";

// ── Scan type definitions with nmap args ──
const SCAN_TYPES = [
  {
    value: "discovery",
    label: "Découverte (ping)",
    description: "Scan rapide pour détecter les hôtes actifs",
    args: "-sn",
  },
  {
    value: "port_scan",
    label: "Scan de ports (top 1000)",
    description: "Détection des services sur les 1000 ports les plus courants",
    args: "-sV --top-ports 1000",
  },
  {
    value: "full",
    label: "Scan complet",
    description: "Tous les ports + détection OS + scripts NSE",
    args: "-sV -sC -O -p-",
  },
  {
    value: "custom",
    label: "Personnalisé",
    description: "Écrivez votre propre commande Nmap",
    args: "",
  },
] as const;

const SCAN_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  SCAN_TYPES.map((t) => [t.value, t.label])
);

const DECISION_VARIANTS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "outline",
  kept: "default",
  ignored: "secondary",
};

const TYPE_ICONS: Record<string, typeof Server> = {
  serveur: Monitor,
  firewall: Shield,
  reseau: Wifi,
  equipement: Server,
  switch: Wifi,
  router: Router,
  access_point: Wifi,
  printer: Printer,
  camera: Video,
  nas: Server,
  hyperviseur: Cpu,
  telephone: Phone,
  iot: Server,
  cloud_gateway: Cloud,
};

export default function ScannerPage() {
  return (
    <Suspense fallback={<div className="p-6">Chargement…</div>}>
      <ScannerContent />
    </Suspense>
  );
}

function ScannerContent() {
  // ── State ──
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedScan, setSelectedScan] = useState<Scan | null>(null);
  const [loading, setLoading] = useState(true);
  const [showLaunch, setShowLaunch] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Launch form
  const [nom, setNom] = useState("");
  const [siteId, setSiteId] = useState<number>(0);
  const [target, setTarget] = useState("");
  const [scanType, setScanType] = useState<string>("discovery");
  const [customArgs, setCustomArgs] = useState("");
  const [notes, setNotes] = useState("");

  // ── Computed nmap command preview ──
  const commandPreview = useMemo(() => {
    const t = target || "<cible>";
    if (scanType === "custom") {
      const args = customArgs.trim() || "<arguments>";
      return `nmap ${args} ${t}`;
    }
    const scanDef = SCAN_TYPES.find((s) => s.value === scanType);
    return `nmap ${scanDef?.args || "-sn"} ${t}`;
  }, [target, scanType, customArgs]);

  // ── Has running scans? ──
  const hasRunningScans = useMemo(
    () => scans.some((s) => s.statut === "running"),
    [scans]
  );

  // ── Fetch ──
  const fetchScans = useCallback(async () => {
    try {
      const res = await scansApi.list({ page: 1, page_size: 50 });
      setScans(res.items);
    } catch {
      toast.error("Erreur lors du chargement des scans");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSites = useCallback(async () => {
    try {
      const res = await sitesApi.list(1, 100);
      setSites(res.items);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    fetchScans();
    fetchSites();
  }, [fetchScans, fetchSites]);

  // ── Polling: refresh every 3s while scans are running ──
  useEffect(() => {
    if (hasRunningScans) {
      pollingRef.current = setInterval(() => {
        fetchScans();
      }, 3000);
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [hasRunningScans, fetchScans]);

  // ── Launch scan (async — returns immediately) ──
  const handleLaunch = async () => {
    if (!siteId || !target) {
      toast.error("Veuillez sélectionner un site et saisir une cible");
      return;
    }
    if (scanType === "custom" && !customArgs.trim()) {
      toast.error("Veuillez saisir les arguments Nmap personnalisés");
      return;
    }
    // Close dialog immediately
    setShowLaunch(false);
    try {
      await scansApi.launch({
        nom: nom.trim() || undefined,
        site_id: siteId,
        target,
        scan_type: scanType as "discovery" | "port_scan" | "full" | "custom",
        custom_args: scanType === "custom" ? customArgs.trim() : undefined,
        notes: notes || undefined,
      });
      toast.success("Scan lancé — il s'exécute en arrière-plan");
      resetForm();
      fetchScans();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg =
        axiosErr?.response?.data?.detail ||
        (err instanceof Error ? err.message : "Erreur lors du lancement du scan");
      toast.error(msg);
    }
  };

  const resetForm = () => {
    setNom("");
    setTarget("");
    setCustomArgs("");
    setNotes("");
    setScanType("discovery");
  };

  // ── View detail ──
  const handleViewScan = async (id: number) => {
    try {
      const scan = await scansApi.get(id);
      setSelectedScan(scan);
      setShowDetail(true);
    } catch {
      toast.error("Erreur lors du chargement du scan");
    }
  };

  // ── Delete ──
  const handleDelete = async (id: number) => {
    if (!confirm("Supprimer ce scan et tous ses résultats ?")) return;
    try {
      await scansApi.delete(id);
      toast.success("Scan supprimé");
      fetchScans();
    } catch {
      toast.error("Erreur lors de la suppression");
    }
  };

  // ── Host decision ──
  const handleDecision = async (
    hostId: number,
    decision: "kept" | "ignored",
    chosenType?: TypeEquipement
  ) => {
    try {
      await scansApi.updateHostDecision(hostId, {
        decision,
        chosen_type: chosenType,
        create_equipement: decision === "kept",
      });
      toast.success(
        decision === "kept"
          ? "Hôte conservé — équipement créé"
          : "Hôte ignoré"
      );
      if (selectedScan) {
        const updated = await scansApi.get(selectedScan.id);
        setSelectedScan(updated);
      }
    } catch {
      toast.error("Erreur lors de la mise à jour");
    }
  };

  // ── Import all ──
  const handleImportAll = async (scanId: number) => {
    try {
      const res = await scansApi.importAllKept(scanId);
      toast.success(
        `${(res as { created: number }).created || 0} équipement(s) importé(s)`
      );
      if (selectedScan) {
        const updated = await scansApi.get(selectedScan.id);
        setSelectedScan(updated);
      }
    } catch {
      toast.error("Erreur lors de l'import");
    }
  };

  const getSiteName = (id: number) =>
    sites.find((s) => s.id === id)?.nom || `Site #${id}`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Radar className="h-6 w-6" />
            Scanner Réseau
          </h1>
          <p className="text-muted-foreground">
            Découverte et inventaire automatique des équipements réseau via Nmap
          </p>
        </div>
        <Button onClick={() => setShowLaunch(true)}>
          <Play className="h-4 w-4 mr-2" />
          Lancer un scan
        </Button>
      </div>

      {/* Scan list */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Historique des scans
            {hasRunningScans && (
              <Badge className="gap-1 bg-blue-500/10 text-blue-600 border-blue-200 dark:border-blue-800 dark:text-blue-400 text-xs">
                <Loader2 className="h-3 w-3 animate-spin" />
                {scans.filter((s) => s.statut === "running").length} en cours
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            {scans.length} scan(s) enregistré(s)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <TableSkeleton rows={3} cols={7} />
          ) : scans.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Radar className="h-12 w-12 mx-auto mb-4 opacity-40" />
              <p>Aucun scan réalisé</p>
              <p className="text-sm">
                Lancez un scan pour découvrir les équipements du réseau
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Site</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Commande</TableHead>
                  <TableHead className="text-center">Hôtes</TableHead>
                  <TableHead className="text-center">Ports</TableHead>
                  <TableHead className="text-center">Durée</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {scans.map((scan) => (
                  <TableRow key={scan.id} className={scan.statut === "running" ? "bg-primary/5" : ""}>
                    <TableCell className="font-medium max-w-[160px] truncate">
                      {scan.nom || (
                        <span className="text-muted-foreground italic">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <ScanStatusBadge statut={scan.statut} errorMessage={scan.error_message} />
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {new Date(scan.date_scan).toLocaleDateString("fr-FR", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </TableCell>
                    <TableCell>{getSiteName(scan.site_id)}</TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {SCAN_TYPE_LABELS[scan.type_scan || "discovery"] ||
                          scan.type_scan}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[200px]">
                      {scan.nmap_command ? (
                        <code className="text-xs bg-muted px-2 py-1 rounded font-mono block truncate">
                          {scan.nmap_command}
                        </code>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center font-semibold">
                      {scan.nombre_hosts_trouves}
                    </TableCell>
                    <TableCell className="text-center">
                      {scan.nombre_ports_ouverts}
                    </TableCell>
                    <TableCell className="text-center text-muted-foreground">
                      {scan.duree_scan_secondes
                        ? `${scan.duree_scan_secondes}s`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-1 justify-end">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleViewScan(scan.id)}
                          disabled={scan.statut === "running"}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(scan.id)}
                          disabled={scan.statut === "running"}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Launch dialog */}
      <Dialog open={showLaunch} onOpenChange={setShowLaunch}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Lancer un scan réseau</DialogTitle>
            <DialogDescription>
              Configurez les paramètres du scan Nmap
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Nom du scan */}
            <div>
              <Label>Nom du scan (optionnel)</Label>
              <Input
                value={nom}
                onChange={(e) => setNom(e.target.value)}
                placeholder="Ex : VLAN 10 - MGT, DMZ Serveurs…"
              />
            </div>

            {/* Site */}
            <div>
              <Label>Site *</Label>
              <Select
                value={siteId ? String(siteId) : ""}
                onValueChange={(v) => setSiteId(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un site" />
                </SelectTrigger>
                <SelectContent>
                  {sites.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Cible */}
            <div>
              <Label>Cible (IP, plage CIDR) *</Label>
              <Input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="192.168.1.0/24"
              />
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
                    className={`text-left p-3 rounded-lg border-2 transition-colors ${
                      scanType === type.value
                        ? "border-primary bg-primary/5"
                        : "border-muted hover:border-muted-foreground/30"
                    }`}
                  >
                    <div className="font-medium text-sm">{type.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {type.description}
                    </div>
                    {type.args && (
                      <code className="text-[10px] text-muted-foreground font-mono mt-1 block">
                        {type.args}
                      </code>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom args (only shown for custom type) */}
            {scanType === "custom" && (
              <div>
                <Label>Arguments Nmap personnalisés *</Label>
                <Input
                  value={customArgs}
                  onChange={(e) => setCustomArgs(e.target.value)}
                  placeholder="-sV -p 22,80,443 --script vuln"
                  className="font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Saisissez les arguments nmap sans la cible (elle sera ajoutée automatiquement)
                </p>
              </div>
            )}

            {/* Nmap command preview */}
            <div className="rounded-lg bg-zinc-950 p-3 mt-2">
              <div className="flex items-center gap-2 text-zinc-400 text-xs mb-1">
                <Terminal className="h-3 w-3" />
                Commande qui sera exécutée
              </div>
              <code className="text-green-400 text-sm font-mono break-all">
                $ {commandPreview}
              </code>
            </div>

            {/* Notes */}
            <div>
              <Label>Notes (optionnel)</Label>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Notes sur ce scan…"
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLaunch(false)}>
              Annuler
            </Button>
            <Button onClick={handleLaunch}>
              <Play className="h-4 w-4 mr-2" />
              Lancer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail dialog */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-[50vw] w-full max-h-[90vh] overflow-y-auto">
          {selectedScan && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Radar className="h-5 w-5" />
                  {selectedScan.nom
                    ? `${selectedScan.nom} — ${getSiteName(selectedScan.site_id)}`
                    : `Résultats du scan — ${getSiteName(selectedScan.site_id)}`}
                </DialogTitle>
                <DialogDescription>
                  {new Date(selectedScan.date_scan).toLocaleString("fr-FR")} —{" "}
                  {selectedScan.nombre_hosts_trouves} hôte(s),{" "}
                  {selectedScan.nombre_ports_ouverts} port(s) ouvert(s)
                  {selectedScan.notes && ` — ${selectedScan.notes}`}
                </DialogDescription>
              </DialogHeader>

              {/* Nmap command display */}
              {selectedScan.nmap_command && (
                <div className="rounded-lg bg-zinc-950 p-3">
                  <div className="flex items-center gap-2 text-zinc-400 text-xs mb-1">
                    <Terminal className="h-3 w-3" />
                    Commande exécutée
                  </div>
                  <code className="text-green-400 text-sm font-mono">
                    $ {selectedScan.nmap_command}
                  </code>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 mb-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleImportAll(selectedScan.id)}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Importer tous les &quot;pending&quot;
                </Button>
              </div>

              {/* Hosts table */}
              <div className="space-y-3">
                {selectedScan.hosts.map((host) => (
                  <HostRow
                    key={host.id}
                    host={host}
                    onDecision={handleDecision}
                  />
                ))}
                {selectedScan.hosts.length === 0 && (
                  <p className="text-center py-6 text-muted-foreground">
                    Aucun hôte découvert
                  </p>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Scan Status Badge component ──
function ScanStatusBadge({
  statut,
  errorMessage,
}: {
  statut: string;
  errorMessage: string | null;
}) {
  if (statut === "running") {
    return (
      <div className="space-y-1.5 min-w-[100px]">
        <Badge className="gap-1.5 bg-blue-500/10 text-blue-600 border-blue-200 dark:border-blue-800 dark:text-blue-400">
          <Loader2 className="h-3 w-3 animate-spin" />
          En cours
        </Badge>
        <div className="h-1.5 w-full bg-blue-100 dark:bg-blue-900/30 rounded-full overflow-hidden">
          <div className="h-full w-1/3 bg-blue-500 rounded-full animate-[indeterminate_1.5s_ease-in-out_infinite]" />
        </div>
      </div>
    );
  }
  if (statut === "failed") {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="destructive" className="gap-1 cursor-help">
              <AlertCircle className="h-3 w-3" />
              Échoué
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
      <Check className="h-3 w-3" />
      Terminé
    </Badge>
  );
}

// ── Host Row component ──
function HostRow({
  host,
  onDecision,
}: {
  host: ScanHost;
  onDecision: (
    id: number,
    decision: "kept" | "ignored",
    type?: TypeEquipement
  ) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [chosenType, setChosenType] = useState<TypeEquipement>(
    host.chosen_type || "serveur"
  );

  const TypeIcon = TYPE_ICONS[host.chosen_type || "serveur"] || Server;

  return (
    <Card>
      <div
        className="flex items-center gap-4 p-4 cursor-pointer hover:bg-muted/50"
        onClick={() => setExpanded(!expanded)}
      >
        <TypeIcon className="h-5 w-5 text-muted-foreground" />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono font-semibold">{host.ip_address}</span>
            {host.hostname && (
              <span className="text-muted-foreground text-sm">
                ({host.hostname})
              </span>
            )}
          </div>
          <div className="flex gap-2 text-sm text-muted-foreground">
            {host.vendor && <span>{host.vendor}</span>}
            {host.os_guess && <span>• {host.os_guess}</span>}
            {host.mac_address && <span>• {host.mac_address}</span>}
          </div>
        </div>

        <Badge variant="outline">{host.ports_open_count} ports</Badge>

        <Badge variant={DECISION_VARIANTS[host.decision] || "outline"}>
          {host.decision === "kept"
            ? "Conservé"
            : host.decision === "ignored"
            ? "Ignoré"
            : "En attente"}
        </Badge>

        {host.equipement_id && (
          <Badge variant="default" className="gap-1">
            <Globe className="h-3 w-3" />
            Éq. #{host.equipement_id}
          </Badge>
        )}

        {expanded ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </div>

      {expanded && (
        <CardContent className="border-t pt-4 space-y-4">
          {/* Ports */}
          {host.ports.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold mb-2">Ports ouverts</h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Port</TableHead>
                    <TableHead>Proto</TableHead>
                    <TableHead>État</TableHead>
                    <TableHead>Service</TableHead>
                    <TableHead>Produit</TableHead>
                    <TableHead>Version</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {host.ports.map((port) => (
                    <TableRow key={port.id}>
                      <TableCell className="font-mono">
                        {port.port_number}
                      </TableCell>
                      <TableCell>{port.protocol}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            port.state === "open" ? "default" : "secondary"
                          }
                        >
                          {port.state}
                        </Badge>
                      </TableCell>
                      <TableCell>{port.service_name || "—"}</TableCell>
                      <TableCell>{port.product || "—"}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {port.version || "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Decision actions */}
          {host.decision === "pending" && (
            <div className="flex items-center gap-4 pt-2 border-t">
              <div className="flex items-center gap-2">
                <Label className="text-sm whitespace-nowrap">
                  Type d&apos;équipement :
                </Label>
                <Select
                  value={chosenType}
                  onValueChange={(v) => setChosenType(v as TypeEquipement)}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="serveur">Serveur</SelectItem>
                    <SelectItem value="reseau">Réseau</SelectItem>
                    <SelectItem value="switch">Switch</SelectItem>
                    <SelectItem value="router">Router</SelectItem>
                    <SelectItem value="access_point">Access Point</SelectItem>
                    <SelectItem value="firewall">Firewall</SelectItem>
                    <SelectItem value="printer">Printer</SelectItem>
                    <SelectItem value="camera">Camera</SelectItem>
                    <SelectItem value="nas">NAS</SelectItem>
                    <SelectItem value="hyperviseur">Hyperviseur</SelectItem>
                    <SelectItem value="telephone">Téléphone</SelectItem>
                    <SelectItem value="iot">IoT</SelectItem>
                    <SelectItem value="cloud_gateway">Cloud Gateway</SelectItem>
                    <SelectItem value="equipement">Autre</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onDecision(host.id, "kept", chosenType);
                }}
              >
                <Check className="h-4 w-4 mr-1" />
                Conserver
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onDecision(host.id, "ignored");
                }}
              >
                <X className="h-4 w-4 mr-1" />
                Ignorer
              </Button>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
