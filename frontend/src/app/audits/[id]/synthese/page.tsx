"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { auditsApi } from "@/services/api";
import { toast } from "sonner";
import type { ExecutiveSummary } from "@/types";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;
const SEVERITY_LABELS: Record<string, string> = {
  critical: "Critique",
  high: "Élevé",
  medium: "Moyen",
  low: "Faible",
  info: "Info",
};
const SEVERITY_COLORS: Record<string, string> = {
  critical: "#DC2626",
  high: "#EA580C",
  medium: "#F59E0B",
  low: "#6B7280",
  info: "#3B82F6",
};

function scoreColor(score: number): { color: string; label: string } {
  if (score >= 80) return { color: "#10B981", label: "Bon niveau" };
  if (score >= 60) return { color: "#F59E0B", label: "À améliorer" };
  return { color: "#EF4444", label: "Critique" };
}

function ScoreGauge({ score }: { score: number }) {
  const { color } = scoreColor(score);
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const arcLength = (270 / 360) * circumference;
  const filled = (score / 100) * arcLength;

  return (
    <svg viewBox="0 0 200 200" width="180" height="180">
      <circle
        cx="100"
        cy="100"
        r={radius}
        fill="none"
        stroke="#E5E7EB"
        strokeWidth="18"
        strokeDasharray={`${arcLength} ${circumference}`}
        transform="rotate(135 100 100)"
        strokeLinecap="round"
      />
      <circle
        cx="100"
        cy="100"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="18"
        strokeDasharray={`${filled} ${circumference}`}
        transform="rotate(135 100 100)"
        strokeLinecap="round"
      />
      <text
        x="100"
        y="100"
        textAnchor="middle"
        fontSize="48"
        fontWeight="bold"
        fill={color}
        dominantBaseline="middle"
      >
        {Math.round(score)}
      </text>
      <text x="100" y="135" textAnchor="middle" fontSize="12" fill="#6B7280">
        / 100
      </text>
    </svg>
  );
}

export default function ExecutiveSummaryPage() {
  const params = useParams();
  const router = useRouter();
  const auditId = Number(params.id);
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await auditsApi.getExecutiveSummary(auditId);
      setSummary(data);
    } catch {
      toast.error("Impossible de charger la synthèse exécutive.");
    } finally {
      setLoading(false);
    }
  }, [auditId]);

  useEffect(() => {
    if (auditId) load();
  }, [auditId, load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="container mx-auto py-8">
        <p className="text-muted-foreground">Synthèse indisponible.</p>
      </div>
    );
  }

  const score = summary.global_score ?? 0;
  const { color: gaugeColor, label: scoreLabel } = scoreColor(score);
  const maxNc = Math.max(
    1,
    ...SEVERITY_ORDER.map((sev) => summary.by_severity[sev]?.non_compliant ?? 0),
  );

  return (
    <div className="container mx-auto py-6 print:py-0">
      {/* Toolbar — masquée à l'impression */}
      <div className="mb-6 flex items-center justify-between print:hidden">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Retour
        </Button>
        <Button variant="default" size="sm" onClick={() => window.print()}>
          <Printer className="mr-2 h-4 w-4" />
          Imprimer
        </Button>
      </div>

      {/* En-tête */}
      <header className="mb-8 border-b border-border pb-6">
        <p className="text-sm uppercase tracking-wider text-muted-foreground">
          Synthèse exécutive
        </p>
        <h1 className="mt-1 text-3xl font-bold text-foreground">{summary.audit_name}</h1>
        {summary.entreprise_name && (
          <p className="mt-1 text-lg text-muted-foreground">{summary.entreprise_name}</p>
        )}
        <p className="mt-3 text-sm text-muted-foreground">
          Généré le {new Date(summary.generated_at).toLocaleDateString("fr-FR", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </p>
      </header>

      {!summary.has_data ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center">
          <p className="text-muted-foreground">
            Synthèse indisponible — complétez au moins une évaluation.
          </p>
        </div>
      ) : (
        <>
          {/* Intro */}
          <p className="mb-8 rounded-md border-l-4 border-blue-500 bg-muted/30 p-4 text-sm leading-relaxed">
            Cette synthèse consolide les résultats de l&apos;audit
            {summary.entreprise_name && (
              <>
                {" "}
                réalisé pour <strong>{summary.entreprise_name}</strong>
              </>
            )}
            . Elle agrège <strong>{summary.total_evaluations}</strong> évaluation(s) sur{" "}
            <strong>{summary.total_equipements}</strong> équipement(s), soit{" "}
            <strong>{summary.total_controls_assessed}</strong> contrôles examinés.
          </p>

          {/* Hero : score + KPIs */}
          <div className="mb-10 grid grid-cols-1 gap-6 rounded-xl bg-gradient-to-br from-muted/40 to-muted/10 p-8 md:grid-cols-[auto_1fr] md:gap-10 print:break-inside-avoid">
            <div className="flex flex-col items-center justify-center">
              <ScoreGauge score={score} />
              <p
                className="mt-2 text-sm font-bold uppercase tracking-wider"
                style={{ color: gaugeColor }}
              >
                {scoreLabel}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <KpiCard
                value={summary.by_status.compliant}
                label="Conformes"
                color="#10B981"
              />
              <KpiCard
                value={summary.by_status.non_compliant}
                label="Non conformes"
                color="#EF4444"
              />
              <KpiCard
                value={summary.by_status.partially_compliant}
                label="Partiels"
                color="#F59E0B"
              />
              <KpiCard
                value={summary.by_status.not_applicable}
                label="Non applicables"
                color="#6B7280"
              />
            </div>
          </div>

          {/* Sévérité bar chart */}
          <section className="mb-10">
            <h2 className="mb-4 text-xl font-bold">Non-conformités par criticité</h2>
            <div className="space-y-3">
              {SEVERITY_ORDER.filter((sev) => (summary.by_severity[sev]?.total ?? 0) > 0).map(
                (sev) => {
                  const bd = summary.by_severity[sev];
                  const widthPct = bd.non_compliant > 0 ? (bd.non_compliant / maxNc) * 100 : 0;
                  return (
                    <div key={sev} className="flex items-center gap-3">
                      <span className="w-24 text-sm font-bold">{SEVERITY_LABELS[sev]}</span>
                      <div className="relative flex-1 overflow-hidden rounded-md bg-muted">
                        <div
                          className="flex h-7 items-center justify-end rounded-md px-2"
                          style={{
                            width: `${widthPct}%`,
                            background: SEVERITY_COLORS[sev],
                            minWidth: bd.non_compliant > 0 ? "16px" : "0",
                          }}
                        >
                          {bd.non_compliant > 0 && (
                            <span className="text-xs font-bold text-white">
                              {bd.non_compliant}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="w-20 text-right text-xs text-muted-foreground">
                        {bd.non_compliant} / {bd.total}
                      </span>
                    </div>
                  );
                },
              )}
            </div>
          </section>

          {/* Top non-conformités */}
          {summary.top_non_compliances.length > 0 && (
            <section className="mb-10">
              <h2 className="mb-4 text-xl font-bold">
                Top {summary.top_non_compliances.length} non-conformités identifiées
              </h2>
              <div className="overflow-hidden rounded-lg border border-border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-bold uppercase tracking-wider">
                        Sév.
                      </th>
                      <th className="px-3 py-2 text-left text-xs font-bold uppercase tracking-wider">
                        Référence
                      </th>
                      <th className="px-3 py-2 text-left text-xs font-bold uppercase tracking-wider">
                        Contrôle
                      </th>
                      <th className="px-3 py-2 text-center text-xs font-bold uppercase tracking-wider">
                        Occur.
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.top_non_compliances.map((nc, i) => (
                      <tr key={i} className="border-t border-border">
                        <td className="px-3 py-2">
                          <SeverityBadge severity={nc.severity} />
                        </td>
                        <td className="px-3 py-2">
                          <code className="rounded bg-muted px-2 py-0.5 text-xs text-blue-700 dark:text-blue-400">
                            {nc.control_ref}
                          </code>
                        </td>
                        <td className="px-3 py-2">{nc.title}</td>
                        <td className="px-3 py-2 text-center font-bold">{nc.occurrences}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Recommandations */}
          {summary.recommendations.length > 0 && (
            <section className="mb-10">
              <h2 className="mb-4 text-xl font-bold">Recommandations prioritaires</h2>
              <div className="space-y-4">
                {summary.recommendations.map((reco, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-border bg-card p-5 shadow-sm print:break-inside-avoid"
                    style={{
                      borderLeft: `4px solid ${SEVERITY_COLORS[reco.severity] ?? "#6B7280"}`,
                    }}
                  >
                    <div className="mb-2 flex items-center gap-3">
                      <SeverityBadge severity={reco.severity} />
                      <span className="font-bold">{reco.title}</span>
                    </div>
                    <p
                      className={`text-sm leading-relaxed ${
                        reco.remediation ? "text-foreground" : "italic text-muted-foreground"
                      }`}
                    >
                      {reco.remediation ?? "Action de remédiation à définir avec le client."}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function KpiCard({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 text-center">
      <span className="block text-3xl font-bold leading-none" style={{ color }}>
        {value}
      </span>
      <span className="mt-1 block text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className="inline-block rounded px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-white"
      style={{ background: SEVERITY_COLORS[severity] ?? "#6B7280" }}
    >
      {SEVERITY_LABELS[severity] ?? severity}
    </span>
  );
}
