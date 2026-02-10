"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
} from "lucide-react";
import { entreprisesApi, auditsApi, sitesApi, equipementsApi, frameworksApi, campaignsApi } from "@/services/api";
import type { Audit, FrameworkSummary, Campaign, Score } from "@/types";

interface DashboardStats {
  entreprises: number;
  audits: number;
  sites: number;
  equipements: number;
  frameworks: number;
  campaigns: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentAudits, setRecentAudits] = useState<Audit[]>([]);
  const [frameworks, setFrameworks] = useState<FrameworkSummary[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignScores, setCampaignScores] = useState<Record<number, Score>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [entRes, audRes, sitRes, eqRes, fwRes, campRes] = await Promise.all([
          entreprisesApi.list(1, 1),
          auditsApi.list(1, 5),
          sitesApi.list(1, 1),
          equipementsApi.list(1, 1),
          frameworksApi.list(1, 100),
          campaignsApi.list(1, 5),
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
        setCampaigns(campRes.items);

        // Load scores for active campaigns
        const scores: Record<number, Score> = {};
        for (const camp of campRes.items) {
          if (camp.status === "in_progress" || camp.status === "completed" || camp.status === "review") {
            try {
              scores[camp.id] = await campaignsApi.score(camp.id);
            } catch {
              // no score yet
            }
          }
        }
        setCampaignScores(scores);
      } catch (error) {
        console.error("Failed to load dashboard:", error);
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    NOUVEAU: "bg-blue-500/10 text-blue-700",
    EN_COURS: "bg-yellow-500/10 text-yellow-700",
    TERMINE: "bg-green-500/10 text-green-700",
    ARCHIVE: "bg-gray-500/10 text-gray-700",
    draft: "bg-gray-500/10 text-gray-700",
    in_progress: "bg-yellow-500/10 text-yellow-700",
    review: "bg-orange-500/10 text-orange-700",
    completed: "bg-green-500/10 text-green-700",
    archived: "bg-gray-500/10 text-gray-500",
  };

  const statusLabels: Record<string, string> = {
    NOUVEAU: "Nouveau",
    EN_COURS: "En cours",
    TERMINE: "Terminé",
    ARCHIVE: "Archivé",
    draft: "Brouillon",
    in_progress: "En cours",
    review: "En revue",
    completed: "Terminée",
    archived: "Archivée",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Vue d&apos;ensemble de votre plateforme d&apos;audit
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard
          title="Entreprises"
          value={stats?.entreprises ?? 0}
          icon={Building2}
          color="text-blue-600"
        />
        <StatCard
          title="Audits"
          value={stats?.audits ?? 0}
          icon={ClipboardCheck}
          color="text-violet-600"
        />
        <StatCard
          title="Sites"
          value={stats?.sites ?? 0}
          icon={MapPin}
          color="text-emerald-600"
        />
        <StatCard
          title="Équipements"
          value={stats?.equipements ?? 0}
          icon={Server}
          color="text-orange-600"
        />
        <StatCard
          title="Référentiels"
          value={stats?.frameworks ?? 0}
          icon={BookOpen}
          color="text-cyan-600"
        />
        <StatCard
          title="Campagnes"
          value={stats?.campaigns ?? 0}
          icon={Activity}
          color="text-pink-600"
        />
      </div>

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
                        {new Date(audit.created_at).toLocaleDateString("fr-FR")}
                      </p>
                    </div>
                    <Badge
                      variant="outline"
                      className={statusColors[audit.status] || ""}
                    >
                      {statusLabels[audit.status] || audit.status}
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
                          className={statusColors[camp.status] || ""}
                        >
                          {statusLabels[camp.status] || camp.status}
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
}: {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <Card>
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
