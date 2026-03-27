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
  Settings,
  Plus,
  Pencil,
  Trash2,
  Eye,
  EyeOff,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";
import { agentsApi, oradadApi } from "@/services/api";
import { cn } from "@/lib/utils";
import type { Agent, OradadTask, OradadConfig, AnssiReport, AnssiCheckResult, DomainEntry } from "@/types";

// ── Constants ──
const ANSSI_LEVELS: Record<number, { label: string; color: string; bg: string }> = {
  1: { label: "Critique", color: "text-red-700 dark:text-red-400", bg: "bg-red-500" },
  2: { label: "Lacunes", color: "text-orange-700 dark:text-orange-400", bg: "bg-orange-500" },
  3: { label: "Basique", color: "text-yellow-700 dark:text-yellow-400", bg: "bg-yellow-500" },
  4: { label: "Bon", color: "text-emerald-700 dark:text-emerald-400", bg: "bg-emerald-500" },
  5: { label: "État de l'art", color: "text-emerald-800 dark:text-emerald-300", bg: "bg-emerald-700" },
};

const EMPTY_DOMAIN: DomainEntry = {
  server: "",
  port: 389,
  domain_name: "",
  username: "",
  user_domain: "",
  password: "",
};

const LEVEL_LABELS: Record<string, string> = {
  "1": "Minimal",
  "2": "Standard",
  "3": "Détaillé",
  "4": "Complet",
};

const CONFIDENTIAL_LABELS: Record<string, string> = {
  "0": "Ne pas collecter",
  "1": "Avec limites",
  "2": "Sans limites",
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

// ── Domain row component ──
function DomainRow({
  domain,
  index,
  onChange,
  onRemove,
  canRemove,
}: {
  domain: DomainEntry;
  index: number;
  onChange: (index: number, field: keyof DomainEntry, value: string | number) => void;
  onRemove: (index: number) => void;
  canRemove: boolean;
}) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="rounded-lg border p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Domaine {index + 1}</span>
        {canRemove && (
          <Button variant="ghost" size="sm" className="text-destructive" onClick={() => onRemove(index)}>
            <Trash2 data-icon="inline-start" />
            Retirer
          </Button>
        )}
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="flex flex-col gap-1">
          <Label htmlFor={`domain-server-${index}`} className="text-xs">Serveur / IP du DC *</Label>
          <Input
            id={`domain-server-${index}`}
            placeholder="192.168.1.10 ou dc01.client.local"
            value={domain.server}
            onChange={(e) => onChange(index, "server", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor={`domain-port-${index}`} className="text-xs">Port LDAP</Label>
          <Input
            id={`domain-port-${index}`}
            type="number"
            min={1}
            max={65535}
            placeholder="389"
            value={domain.port}
            onChange={(e) => onChange(index, "port", Number(e.target.value) || 389)}
          />
        </div>
        <div className="flex flex-col gap-1 md:col-span-2">
          <Label htmlFor={`domain-name-${index}`} className="text-xs">Nom du domaine *</Label>
          <Input
            id={`domain-name-${index}`}
            placeholder="client.local"
            value={domain.domain_name}
            onChange={(e) => onChange(index, "domain_name", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor={`domain-username-${index}`} className="text-xs">Nom d&apos;utilisateur *</Label>
          <Input
            id={`domain-username-${index}`}
            placeholder="auditeur"
            value={domain.username}
            onChange={(e) => onChange(index, "username", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor={`domain-userdomain-${index}`} className="text-xs">Domaine utilisateur *</Label>
          <Input
            id={`domain-userdomain-${index}`}
            placeholder="CLIENT"
            value={domain.user_domain}
            onChange={(e) => onChange(index, "user_domain", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1 md:col-span-2">
          <Label htmlFor={`domain-password-${index}`} className="text-xs">Mot de passe *</Label>
          <div className="flex gap-2">
            <Input
              id={`domain-password-${index}`}
              type={showPassword ? "text" : "password"}
              placeholder="••••••"
              value={domain.password}
              onChange={(e) => onChange(index, "password", e.target.value)}
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
            >
              {showPassword ? <EyeOff data-icon /> : <Eye data-icon />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Page ──
export default function OradadPage() {
  const { user } = useAuth();

  // Agents
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(true);

  // Tasks
  const [tasks, setTasks] = useState<OradadTask[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(true);

  // Configs
  const [configs, setConfigs] = useState<OradadConfig[]>([]);
  const [loadingConfigs, setLoadingConfigs] = useState(true);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [editingConfig, setEditingConfig] = useState<OradadConfig | null>(null);
  const [deleteConfigTarget, setDeleteConfigTarget] = useState<OradadConfig | null>(null);
  const [savingConfig, setSavingConfig] = useState(false);

  // Config form fields
  const [cfgName, setCfgName] = useState("");
  const [cfgAutoGetDomain, setCfgAutoGetDomain] = useState(false);
  const [cfgAutoGetTrusts, setCfgAutoGetTrusts] = useState(false);
  const [cfgLevel, setCfgLevel] = useState("4");
  const [cfgConfidential, setCfgConfidential] = useState("0");
  const [cfgProcessSysvol, setCfgProcessSysvol] = useState(true);
  const [cfgSysvolFilter, setCfgSysvolFilter] = useState("");
  const [cfgOutputFiles, setCfgOutputFiles] = useState(false);
  const [cfgOutputMla, setCfgOutputMla] = useState(true);
  const [cfgSleepTime, setCfgSleepTime] = useState("0");
  const [cfgShowAdvanced, setCfgShowAdvanced] = useState(false);
  const [cfgDomains, setCfgDomains] = useState<(DomainEntry & { _key: number })[]>([{ ...EMPTY_DOMAIN, _key: 0 }]);
  const [domainKeyCounter, setDomainKeyCounter] = useState(1);

  // Launch form — simplified: agent + config (required) + domain override
  const [selectedAgentUuid, setSelectedAgentUuid] = useState<string>("");
  const [selectedConfigId, setSelectedConfigId] = useState<string>("");
  const [domainOverride, setDomainOverride] = useState("");
  const [launching, setLaunching] = useState(false);

  // Report view
  const [selectedTask, setSelectedTask] = useState<OradadTask | null>(null);
  const [report, setReport] = useState<AnssiReport | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  // Filter agents to show those with "oradad" or "config-oradad" tools
  const oradadAgents = useMemo(
    () => agents.filter(
      (a) => a.status === "active" && (a.allowed_tools.includes("oradad") || a.allowed_tools.includes("config-oradad"))
    ),
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

  const fetchConfigs = useCallback(async () => {
    try {
      const data = await oradadApi.listConfigs();
      setConfigs(data);
    } catch {
      // non-blocking
    } finally {
      setLoadingConfigs(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchTasks();
    fetchConfigs();
  }, [fetchAgents, fetchTasks, fetchConfigs]);

  // Poll running tasks
  useEffect(() => {
    const hasRunning = tasks.some((t) => t.status === "running" || t.status === "pending" || t.status === "dispatched");
    if (!hasRunning) return;
    const interval = setInterval(fetchTasks, 5000);
    return () => clearInterval(interval);
  }, [tasks, fetchTasks]);

  // ── Launch collect ──
  const handleLaunch = async () => {
    if (!selectedAgentUuid || !selectedConfigId) {
      toast.error("Veuillez sélectionner un agent et un profil de configuration");
      return;
    }
    setLaunching(true);
    try {
      await agentsApi.dispatch({
        agent_uuid: selectedAgentUuid,
        tool: "oradad",
        parameters: {
          config_id: Number(selectedConfigId),
          domain: domainOverride || undefined,
        },
      });
      toast.success("Collecte ORADAD lancée");
      setDomainOverride("");
      setTimeout(fetchTasks, 1000);
    } catch {
      toast.error("Erreur lors du lancement de la collecte");
    } finally {
      setLaunching(false);
    }
  };

  // ── Domain management in config dialog ──
  const handleDomainChange = (index: number, field: keyof DomainEntry, value: string | number) => {
    setCfgDomains((prev) =>
      prev.map((d, i) => (i === index ? { ...d, [field]: value } : d))
    );
  };

  const handleAddDomain = () => {
    setCfgDomains((prev) => [...prev, { ...EMPTY_DOMAIN, _key: domainKeyCounter }]);
    setDomainKeyCounter((c) => c + 1);
  };

  const handleRemoveDomain = (index: number) => {
    setCfgDomains((prev) => prev.filter((_, i) => i !== index));
  };

  // ── Config CRUD ──
  const openNewConfig = () => {
    setEditingConfig(null);
    setCfgName("");
    setCfgAutoGetDomain(false);
    setCfgAutoGetTrusts(false);
    setCfgLevel("4");
    setCfgConfidential("0");
    setCfgProcessSysvol(true);
    setCfgSysvolFilter("");
    setCfgOutputFiles(false);
    setCfgOutputMla(true);
    setCfgSleepTime("0");
    setCfgShowAdvanced(false);
    setCfgDomains([{ ...EMPTY_DOMAIN, _key: 0 }]);
    setDomainKeyCounter(1);
    setShowConfigDialog(true);
  };

  const openEditConfig = (config: OradadConfig) => {
    setEditingConfig(config);
    setCfgName(config.name);
    setCfgAutoGetDomain(config.auto_get_domain);
    setCfgAutoGetTrusts(config.auto_get_trusts);
    setCfgLevel(String(config.level));
    setCfgConfidential(String(config.confidential));
    setCfgProcessSysvol(config.process_sysvol);
    setCfgSysvolFilter(config.sysvol_filter || "");
    setCfgOutputFiles(config.output_files);
    setCfgOutputMla(config.output_mla);
    setCfgSleepTime(String(config.sleep_time));
    setCfgShowAdvanced(false);
    const domains = config.explicit_domains && config.explicit_domains.length > 0
      ? config.explicit_domains.map((d, i) => ({ ...d, _key: i }))
      : [{ ...EMPTY_DOMAIN, _key: 0 }];
    setCfgDomains(domains);
    setDomainKeyCounter(domains.length);
    setShowConfigDialog(true);
  };

  const handleSaveConfig = async () => {
    if (!cfgName.trim()) {
      toast.error("Le nom du profil est requis");
      return;
    }

    // Validate domains if auto-detect is off
    if (!cfgAutoGetDomain) {
      const validDomains = cfgDomains.filter(
        (d) => d.server.trim() && d.domain_name.trim()
      );
      if (validDomains.length === 0) {
        toast.error("Au moins un domaine cible est requis quand la détection automatique est désactivée");
        return;
      }
      // Check all required fields
      for (const d of validDomains) {
        if (!d.username.trim() || !d.user_domain.trim() || !d.password.trim()) {
          toast.error("Tous les champs d'identification sont requis pour chaque domaine");
          return;
        }
      }
    }

    setSavingConfig(true);

    // Build domains list — only include non-empty rows
    const domainsToSend = cfgAutoGetDomain
      ? null
      : cfgDomains
          .filter((d) => d.server.trim() && d.domain_name.trim())
          .map((d) => ({
            server: d.server.trim(),
            port: d.port || 389,
            domain_name: d.domain_name.trim(),
            username: d.username.trim(),
            user_domain: d.user_domain.trim(),
            password: d.password,
          }));

    const payload = {
      name: cfgName.trim(),
      auto_get_domain: cfgAutoGetDomain,
      auto_get_trusts: cfgAutoGetTrusts,
      level: Number(cfgLevel),
      confidential: Number(cfgConfidential),
      process_sysvol: cfgProcessSysvol,
      sysvol_filter: cfgSysvolFilter || null,
      output_files: cfgOutputFiles,
      output_mla: cfgOutputMla,
      sleep_time: Number(cfgSleepTime),
      explicit_domains: domainsToSend,
    };
    try {
      if (editingConfig) {
        await oradadApi.updateConfig(editingConfig.id, payload);
        toast.success("Profil mis à jour");
      } else {
        await oradadApi.createConfig(payload);
        toast.success("Profil créé");
      }
      setShowConfigDialog(false);
      await fetchConfigs();
    } catch {
      toast.error("Erreur lors de la sauvegarde du profil");
    } finally {
      setSavingConfig(false);
    }
  };

  const handleDeleteConfig = async () => {
    if (!deleteConfigTarget) return;
    try {
      await oradadApi.deleteConfig(deleteConfigTarget.id);
      toast.success("Profil supprimé");
      if (selectedConfigId === String(deleteConfigTarget.id)) {
        setSelectedConfigId("");
      }
      await fetchConfigs();
    } catch {
      toast.error("Erreur lors de la suppression");
    } finally {
      setDeleteConfigTarget(null);
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

      {/* ── Config profiles section ── */}
      <Accordion type="single" collapsible>
        <AccordionItem value="configs" className="rounded-lg border">
          <AccordionTrigger className="px-6 hover:no-underline">
            <div className="flex items-center gap-2">
              <Settings className="size-5" />
              <span className="font-semibold">Profils de configuration</span>
              <Badge variant="secondary" className="text-xs">{configs.length}</Badge>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-4">
            {loadingConfigs ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <div className="flex flex-col gap-3">
                <div className="flex justify-end">
                  <Button size="sm" onClick={openNewConfig}>
                    <Plus data-icon="inline-start" />
                    Nouveau profil
                  </Button>
                </div>
                {configs.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Aucun profil. Créez un profil de configuration avant de lancer une collecte.
                  </p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Nom</TableHead>
                        <TableHead>Niveau</TableHead>
                        <TableHead>Confidentiel</TableHead>
                        <TableHead>Domaines</TableHead>
                        <TableHead>SYSVOL</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {configs.map((cfg) => (
                        <TableRow key={cfg.id}>
                          <TableCell className="font-medium">{cfg.name}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{LEVEL_LABELS[String(cfg.level)] || cfg.level}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{CONFIDENTIAL_LABELS[String(cfg.confidential)] || cfg.confidential}</Badge>
                          </TableCell>
                          <TableCell>
                            {cfg.auto_get_domain ? (
                              <Badge variant="secondary">Auto</Badge>
                            ) : cfg.explicit_domains ? (
                              <Badge variant="outline">{cfg.explicit_domains.length} domaine(s)</Badge>
                            ) : (
                              <span className="text-sm text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell>{cfg.process_sysvol ? "Oui" : "Non"}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Button variant="ghost" size="sm" onClick={() => openEditConfig(cfg)}>
                                <Pencil data-icon="inline-start" />
                                Modifier
                              </Button>
                              <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setDeleteConfigTarget(cfg)}>
                                <Trash2 data-icon="inline-start" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            )}
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* ── Launch section ── */}
      <Card>
        <CardHeader>
          <CardTitle>Lancer une collecte</CardTitle>
          <CardDescription>
            Sélectionnez un agent et un profil de configuration pour collecter les données AD.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="flex flex-col gap-2">
                <Label htmlFor="launch-agent">Agent *</Label>
                {loadingAgents ? (
                  <Skeleton className="h-10 w-full" />
                ) : oradadAgents.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Aucun agent actif avec l&apos;outil ORADAD
                  </p>
                ) : (
                  <Select value={selectedAgentUuid} onValueChange={setSelectedAgentUuid}>
                    <SelectTrigger id="launch-agent">
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
                <Label htmlFor="launch-config">Profil de configuration *</Label>
                <Select value={selectedConfigId} onValueChange={setSelectedConfigId}>
                  <SelectTrigger id="launch-config">
                    <SelectValue placeholder="Sélectionner un profil" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {configs.map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.name} (Niv. {c.level})
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
                {configs.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    Créez d&apos;abord un profil dans la section ci-dessus.
                  </p>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="oradad-domain-override">Domaine override (optionnel)</Label>
                <Input
                  id="oradad-domain-override"
                  placeholder="Override ponctuel"
                  value={domainOverride}
                  onChange={(e) => setDomainOverride(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleLaunch}
                disabled={launching || !selectedAgentUuid || !selectedConfigId}
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

      {/* ── Config dialog ── */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingConfig ? "Modifier le profil" : "Nouveau profil"}</DialogTitle>
            <DialogDescription>
              Configurez les paramètres de collecte ORADAD.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="cfg-name">Nom du profil *</Label>
              <Input id="cfg-name" value={cfgName} onChange={(e) => setCfgName(e.target.value)} placeholder="ex : Audit Client X" />
            </div>

            <Separator />

            {/* Auto-detect toggles */}
            <div className="flex items-center justify-between">
              <div className="flex flex-col gap-0.5">
                <Label htmlFor="cfg-auto-domain">Détection automatique du domaine</Label>
                <span className="text-xs text-muted-foreground">
                  Activer uniquement si l&apos;agent est joint au domaine cible
                </span>
              </div>
              <Switch id="cfg-auto-domain" checked={cfgAutoGetDomain} onCheckedChange={setCfgAutoGetDomain} />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex flex-col gap-0.5">
                <Label htmlFor="cfg-auto-trusts">Détection automatique des trusts</Label>
                <span className="text-xs text-muted-foreground">
                  Activer uniquement si l&apos;agent est joint au domaine cible
                </span>
              </div>
              <Switch id="cfg-auto-trusts" checked={cfgAutoGetTrusts} onCheckedChange={setCfgAutoGetTrusts} />
            </div>

            {/* ── Target domains — central section, shown when auto-detect is OFF ── */}
            {!cfgAutoGetDomain && (
              <>
                <Separator />
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label className="text-base font-semibold">Domaines cibles *</Label>
                      <p className="text-xs text-muted-foreground">
                        Renseignez les contrôleurs de domaine et les identifiants de connexion.
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleAddDomain}>
                      <Plus data-icon="inline-start" />
                      Ajouter un domaine
                    </Button>
                  </div>
                  {cfgDomains.map((d, i) => (
                    <DomainRow
                      key={d._key}
                      domain={d}
                      index={i}
                      onChange={handleDomainChange}
                      onRemove={handleRemoveDomain}
                      canRemove={cfgDomains.length > 1}
                    />
                  ))}
                </div>
              </>
            )}

            <Separator />

            {/* Collection parameters */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="cfg-level">Niveau de collecte</Label>
              <Select value={cfgLevel} onValueChange={setCfgLevel}>
                <SelectTrigger id="cfg-level"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="1">1 — Minimal</SelectItem>
                    <SelectItem value="2">2 — Standard</SelectItem>
                    <SelectItem value="3">3 — Détaillé</SelectItem>
                    <SelectItem value="4">4 — Complet</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="cfg-confidential">Attributs confidentiels</Label>
              <Select value={cfgConfidential} onValueChange={setCfgConfidential}>
                <SelectTrigger id="cfg-confidential"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="0">Ne pas collecter</SelectItem>
                    <SelectItem value="1">Avec limites</SelectItem>
                    <SelectItem value="2">Sans limites</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="cfg-sysvol">Collecter le SYSVOL</Label>
              <Switch id="cfg-sysvol" checked={cfgProcessSysvol} onCheckedChange={setCfgProcessSysvol} />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="cfg-output-files">Sortie fichiers texte</Label>
              <Switch id="cfg-output-files" checked={cfgOutputFiles} onCheckedChange={setCfgOutputFiles} />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="cfg-output-mla">Sortie archive MLA</Label>
              <Switch id="cfg-output-mla" checked={cfgOutputMla} onCheckedChange={setCfgOutputMla} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="cfg-sleep">Délai entre requêtes (secondes)</Label>
              <Input id="cfg-sleep" type="number" min="0" value={cfgSleepTime} onChange={(e) => setCfgSleepTime(e.target.value)} />
            </div>

            {/* Advanced */}
            <Button variant="ghost" size="sm" className="self-start" onClick={() => setCfgShowAdvanced(!cfgShowAdvanced)}>
              <ChevronDown data-icon="inline-start" className={cn("transition-transform", cfgShowAdvanced && "rotate-180")} />
              Avancé
            </Button>
            {cfgShowAdvanced && (
              <div className="flex flex-col gap-2">
                <Label>Filtre SYSVOL</Label>
                <Textarea
                  rows={4}
                  value={cfgSysvolFilter}
                  onChange={(e) => setCfgSysvolFilter(e.target.value)}
                  placeholder="*.bat;*.vbs;*.ps1;..."
                  className="font-mono text-xs"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>Annuler</Button>
            <Button onClick={handleSaveConfig} disabled={savingConfig}>
              {savingConfig && <Loader2 data-icon="inline-start" className="animate-spin" />}
              {editingConfig ? "Enregistrer" : "Créer"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete config confirmation ── */}
      <AlertDialog open={!!deleteConfigTarget} onOpenChange={(open) => !open && setDeleteConfigTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer le profil ?</AlertDialogTitle>
            <AlertDialogDescription>
              Le profil « {deleteConfigTarget?.name} » sera supprimé définitivement.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfig}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
