"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  ShieldCheck,
  FileSearch,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";
import { agentsApi, oradadApi } from "@/services/api";
import { cn } from "@/lib/utils";
import type { Agent, OradadTask, OradadConfig, AnssiReport, DomainEntry } from "@/types";

import { ConfigProfiles } from "./components/config-profiles";
import { CollectForm } from "./components/collect-form";
import { AnssiReportSection } from "./components/anssi-report";

// ── Constants ──
const EMPTY_DOMAIN: DomainEntry = {
  server: "",
  port: 389,
  domain_name: "",
  username: "",
  user_domain: "",
  password: "",
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
      setSelectedTask(prev => prev ? { ...prev, has_report: true } : prev);
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
      <ConfigProfiles
        configs={configs}
        loadingConfigs={loadingConfigs}
        showConfigDialog={showConfigDialog}
        setShowConfigDialog={setShowConfigDialog}
        editingConfig={editingConfig}
        deleteConfigTarget={deleteConfigTarget}
        setDeleteConfigTarget={setDeleteConfigTarget}
        savingConfig={savingConfig}
        cfgName={cfgName}
        setCfgName={setCfgName}
        cfgAutoGetDomain={cfgAutoGetDomain}
        setCfgAutoGetDomain={setCfgAutoGetDomain}
        cfgAutoGetTrusts={cfgAutoGetTrusts}
        setCfgAutoGetTrusts={setCfgAutoGetTrusts}
        cfgLevel={cfgLevel}
        setCfgLevel={setCfgLevel}
        cfgConfidential={cfgConfidential}
        setCfgConfidential={setCfgConfidential}
        cfgProcessSysvol={cfgProcessSysvol}
        setCfgProcessSysvol={setCfgProcessSysvol}
        cfgSysvolFilter={cfgSysvolFilter}
        setCfgSysvolFilter={setCfgSysvolFilter}
        cfgOutputFiles={cfgOutputFiles}
        setCfgOutputFiles={setCfgOutputFiles}
        cfgOutputMla={cfgOutputMla}
        setCfgOutputMla={setCfgOutputMla}
        cfgSleepTime={cfgSleepTime}
        setCfgSleepTime={setCfgSleepTime}
        cfgShowAdvanced={cfgShowAdvanced}
        setCfgShowAdvanced={setCfgShowAdvanced}
        cfgDomains={cfgDomains}
        openNewConfig={openNewConfig}
        openEditConfig={openEditConfig}
        handleSaveConfig={handleSaveConfig}
        handleDeleteConfig={handleDeleteConfig}
        handleDomainChange={handleDomainChange}
        handleAddDomain={handleAddDomain}
        handleRemoveDomain={handleRemoveDomain}
      />

      {/* ── Launch section ── */}
      <CollectForm
        oradadAgents={oradadAgents}
        loadingAgents={loadingAgents}
        configs={configs}
        selectedAgentUuid={selectedAgentUuid}
        setSelectedAgentUuid={setSelectedAgentUuid}
        selectedConfigId={selectedConfigId}
        setSelectedConfigId={setSelectedConfigId}
        domainOverride={domainOverride}
        setDomainOverride={setDomainOverride}
        launching={launching}
        handleLaunch={handleLaunch}
      />

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
        <AnssiReportSection
          selectedTask={selectedTask}
          report={report}
          loadingReport={loadingReport}
          analyzing={analyzing}
          handleAnalyze={handleAnalyze}
        />
      )}
    </div>
  );
}
