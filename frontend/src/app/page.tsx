"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Building2,
  ClipboardCheck,
  Server,
  BookOpen,
  MapPin,
  ShieldAlert,
  ShieldCheck,
  Activity,
  Loader2,
  Filter,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { entreprisesApi, auditsApi, sitesApi, equipementsApi, frameworksApi, campaignsApi } from "@/services/api";
import type { Audit, Entreprise, FrameworkSummary, CampaignSummary, Score } from "@/types";
import { STATUS_COLORS, STATUS_LABELS, SEVERITY_LABELS } from "@/lib/constants";
import { toast } from "sonner";
import { DashboardSkeleton } from "@/components/skeletons";

interface DashboardStats {
  entreprises: number;
  audits: number;
  sites: number;
  equipements: number;
  frameworks: number;
  campaigns: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentAudits, setRecentAudits] = useState<Audit[]>([]);
  const [frameworks, setFrameworks] = useState<FrameworkSummary[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [campaignScores, setCampaignScores] = useState<Record<number, Score>>({});
  const [loading, setLoading] = useState(true);

  // Enterprise filter
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [selectedEntreprise, setSelectedEntreprise] = useState<string>("all");

  // Load entreprises on mount
  useEffect(() => {
    entreprisesApi.list(1, 200).then((res) => setEntreprises(res.items)).catch(() => {});
  }, []);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const entFilter = selectedEntreprise !== "all" ? Number(selectedEntreprise) : undefined;

      const [entRes, audRes, sitRes, eqRes, fwRes, campRes] = await Promise.all([
        entreprisesApi.list(1, 1),
        auditsApi.list(1, 5, entFilter),
        sitesApi.list(1, 1, entFilter),
        equipementsApi.list(1, 1),
        frameworksApi.list(1, 100),
        campaignsApi.list(1, 100),
      ]);

      setStats({
        entreprises: entRes.total,
        audits: audRes.total,
        sites: sitRes.total,
        equipements: eqRes.total,
        frameworks: fwRes.total,
        campaigns: campRes.total,
      });

      setRecentAudits(audRes.items);
      setFrameworks(fwRes.items);

      // Filter campaigns by entreprise if needed
      let filteredCampaigns = campRes.items;
      if (entFilter) {
        // Get all audit IDs for this entreprise
        const allAudits = await auditsApi.list(1, 200, entFilter);
        const auditIds = new Set(allAudits.items.map((a) => a.id));
        filteredCampaigns = campRes.items.filter((c) => auditIds.has(c.audit_id));
      }
      setCampaigns(filteredCampaigns);

      // Load scores for relevant campaigns (parallel)
      const scores: Record<number, Score> = {};
      const scorableCampaigns = filteredCampaigns.filter(
        (c) => c.status === "in_progress" || c.status === "completed" || c.status === "review"
      );
      const scoreResults = await Promise.allSettled(
        scorableCampaigns.map((camp) =>
          campaignsApi.score(camp.id).then((s) => ({ id: camp.id, score: s }))
        )
      );
      for (const r of scoreResults) {
        if (r.status === "fulfilled") {
          scores[r.value.id] = r.value.score;
        }
      }
      setCampaignScores(scores);
    } catch {
      toast.error("Impossible de charger le tableau de bord");
    } finally {
      setLoading(false);
    }
  }, [selectedEntreprise]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Vue d&apos;ensemble de votre plateforme d&apos;audit
          </p>
        </div>
        {/* Enterprise filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={selectedEntreprise} onValueChange={setSelectedEntreprise}>
            <SelectTrigger className="w-[220px]">
              <SelectValue placeholder="Toutes les entreprises" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Toutes les entreprises</SelectItem>
              {entreprises.map((e) => (
                <SelectItem key={e.id} value={String(e.id)}>
                  {e.nom}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard
          title="Entreprises"
          value={stats?.entreprises ?? 0}
          icon={Building2}
          color="text-blue-600"
          onClick={() => router.push("/entreprises")}
        />
        <StatCard
          title="Audits"
          value={stats?.audits ?? 0}
          icon={ClipboardCheck}
          color="text-violet-600"
          onClick={() => router.push("/audits")}
        />
        <StatCard
          title="Sites"
          value={stats?.sites ?? 0}
          icon={MapPin}
          color="text-emerald-600"
          onClick={() => router.push("/sites")}
        />
        <StatCard
          title="Équipements"
          value={stats?.equipements ?? 0}
          icon={Server}
          color="text-orange-600"
          onClick={() => router.push("/equipements")}
        />
        <StatCard
          title="Référentiels"
          value={stats?.frameworks ?? 0}
          icon={BookOpen}
          color="text-cyan-600"
          onClick={() => router.push("/frameworks")}
        />
        <StatCard
          title="Campagnes"
          value={stats?.campaigns ?? 0}
          icon={Activity}
          color="text-pink-600"
          onClick={() => router.push("/audits")}
        />
      </div>

      {/* Charts section — only shown when data exists */}
      {Object.keys(campaignScores).length > 0 && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Compliance distribution pie chart */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Répartition de la conformité</CardTitle>
              <CardDescription>Synthèse globale des contrôles</CardDescription>
            </CardHeader>
            <CardContent>
              {(() => {
                const agg = Object.values(campaignScores).reduce(
                  (acc, s) => ({
                    compliant: acc.compliant + s.compliant,
                    non_compliant: acc.non_compliant + s.non_compliant,
                    partially_compliant: acc.partially_compliant + (s.partially_compliant ?? 0),
                    not_applicable: acc.not_applicable + (s.not_applicable ?? 0),
                    not_assessed: acc.not_assessed + (s.not_assessed ?? 0),
                  }),
                  { compliant: 0, non_compliant: 0, partially_compliant: 0, not_applicable: 0, not_assessed: 0 }
                );
                const pieData = [
                  { name: "Conforme", value: agg.compliant, color: "#22c55e" },
                  { name: "Non conforme", value: agg.non_compliant, color: "#ef4444" },
                  { name: "Partiel", value: agg.partially_compliant, color: "#f59e0b" },
                  { name: "N/A", value: agg.not_applicable, color: "#94a3b8" },
                  { name: "Non évalué", value: agg.not_assessed, color: "#cbd5e1" },
                ].filter((d) => d.value > 0);
                return (
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                        fontSize={11}
                      >
                        {pieData.map((d, i) => (
                          <Cell key={i} fill={d.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                );
              })()}
            </CardContent>
          </Card>

          {/* Campaign scores bar chart */}
          <Card className="lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Score par campagne</CardTitle>
              <CardDescription>Conformité et contrôles évalués</CardDescription>
            </CardHeader>
            <CardContent>
              {(() => {
                const barData = campaigns
                  .filter((c) => campaignScores[c.id])
                  .map((c) => {
                    const s = campaignScores[c.id];
                    return {
                      name: c.name.length > 18 ? c.name.substring(0, 18) + "…" : c.name,
                      score: s.compliance_score ?? 0,
                      conforme: s.compliant,
                      non_conforme: s.non_compliant,
                    };
                  });
                if (barData.length === 0) return <p className="text-sm text-muted-foreground text-center py-8">Pas encore de données</p>;
                return (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" domain={[0, "dataMax"]} />
                      <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="conforme" name="Conforme" fill="#22c55e" stackId="a" />
                      <Bar dataKey="non_conforme" name="Non conforme" fill="#ef4444" stackId="a" />
                    </BarChart>
                  </ResponsiveContainer>
                );
              })()}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Severity radar — shown if any campaign has by_severity data */}
      {Object.values(campaignScores).some((s) => s.by_severity && Object.keys(s.by_severity).length > 0) && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Radar par sévérité</CardTitle>
              <CardDescription>Contrôles par niveau de sévérité</CardDescription>
            </CardHeader>
            <CardContent>
              {(() => {
                const sevAgg: Record<string, { total: number; compliant: number }> = {};
                Object.values(campaignScores).forEach((s) => {
                  if (!s.by_severity) return;
                  Object.entries(s.by_severity).forEach(([sev, data]) => {
                    const d = data as Record<string, number>;
                    if (!sevAgg[sev]) sevAgg[sev] = { total: 0, compliant: 0 };
                    sevAgg[sev].total += d.total || 0;
                    sevAgg[sev].compliant += d.compliant || 0;
                  });
                });
                const sevLabels: Record<string, string> = {
                  critical: "Critique",
                  high: "Élevé",
                  medium: "Moyen",
                  low: "Faible",
                  info: "Info",
                };
                const radarData = Object.entries(sevAgg).map(([sev, d]) => ({
                  severity: SEVERITY_LABELS[sev] || sev,
                  total: d.total,
                  conforme: d.compliant,
                }));
                if (radarData.length === 0) return null;
                return (
                  <ResponsiveContainer width="100%" height={260}>
                    <RadarChart data={radarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="severity" tick={{ fontSize: 12 }} />
                      <PolarRadiusAxis />
                      <Radar name="Total" dataKey="total" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.2} />
                      <Radar name="Conforme" dataKey="conforme" stroke="#22c55e" fill="#22c55e" fillOpacity={0.4} />
                      <Legend />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                );
              })()}
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent audits */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardCheck className="h-5 w-5" />
              Projets d&apos;audit récents
            </CardTitle>
            <CardDescription>Les derniers projets créés</CardDescription>
          </CardHeader>
          <CardContent>
            {recentAudits.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                Aucun audit pour le moment
              </p>
            ) : (
              <div className="space-y-3">
                {recentAudits.map((audit) => (
                  <div
                    key={audit.id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div className="space-y-1">
                      <p className="text-sm font-medium leading-none">
                        {audit.nom_projet}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(audit.date_debut).toLocaleDateString("fr-FR")}
                      </p>
                    </div>
                    <Badge
                      variant="outline"
                      className={STATUS_COLORS[audit.status] || ""}
                    >
                      {STATUS_LABELS[audit.status] || audit.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Campaigns with scores */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Campagnes d&apos;évaluation
            </CardTitle>
            <CardDescription>Suivi de conformité</CardDescription>
          </CardHeader>
          <CardContent>
            {campaigns.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                Aucune campagne pour le moment
              </p>
            ) : (
              <div className="space-y-4">
                {campaigns.map((camp) => {
                  const score = campaignScores[camp.id];
                  return (
                    <div key={camp.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium">{camp.name}</p>
                        <Badge
                          variant="outline"
                          className={STATUS_COLORS[camp.status] || ""}
                        >
                          {STATUS_LABELS[camp.status] || camp.status}
                        </Badge>
                      </div>
                      {score ? (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>
                              {score.assessed_controls}/{score.total_controls}{" "}
                              contrôles évalués
                            </span>
                            <span className="font-semibold text-foreground">
                              {(score.compliance_score ?? 0).toFixed(1)}%
                            </span>
                          </div>
                          <Progress
                            value={score.compliance_score ?? 0}
                            className="h-2"
                          />
                          <div className="flex gap-3 text-xs">
                            <span className="flex items-center gap-1">
                              <ShieldCheck className="h-3 w-3 text-green-600" />
                              {score.compliant}
                            </span>
                            <span className="flex items-center gap-1">
                              <ShieldAlert className="h-3 w-3 text-red-600" />
                              {score.non_compliant}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground">
                          Pas encore de score
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Frameworks */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Référentiels disponibles
          </CardTitle>
          <CardDescription>
            {frameworks.length} référentiel(s) actif(s)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {frameworks.map((fw) => (
              <div
                key={fw.id}
                className="rounded-lg border p-3 space-y-2 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <p className="text-sm font-medium leading-tight">
                    {fw.name}
                  </p>
                  <Badge variant="outline" className="text-[10px] shrink-0 ml-2">
                    v{fw.version}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{fw.total_controls} contrôles</span>
                  {fw.engine && (
                    <Badge variant="secondary" className="text-[10px]">
                      {fw.engine}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  onClick,
}: {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  onClick?: () => void;
}) {
  return (
    <Card
      className={onClick ? "cursor-pointer hover:bg-accent/50 transition-colors" : ""}
      onClick={onClick}
    >
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">
              {title}
            </p>
            <p className="text-2xl font-bold mt-1">{value}</p>
          </div>
          <div className={`rounded-full p-2 bg-muted ${color}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
