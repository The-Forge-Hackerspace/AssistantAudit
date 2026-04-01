"use client";

import { useMemo } from "react";
import {
  ShieldCheck,
  FileSearch,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { OradadTask, AnssiReport, AnssiCheckResult } from "@/types";

// ── Constants ──
const ANSSI_LEVELS: Record<number, { label: string; color: string; bg: string }> = {
  1: { label: "Critique", color: "text-red-700 dark:text-red-400", bg: "bg-red-500" },
  2: { label: "Lacunes", color: "text-orange-700 dark:text-orange-400", bg: "bg-orange-500" },
  3: { label: "Basique", color: "text-yellow-700 dark:text-yellow-400", bg: "bg-yellow-500" },
  4: { label: "Bon", color: "text-emerald-700 dark:text-emerald-400", bg: "bg-emerald-500" },
  5: { label: "État de l'art", color: "text-emerald-800 dark:text-emerald-300", bg: "bg-emerald-700" },
};

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

// ── Props ──
export interface AnssiReportSectionProps {
  selectedTask: OradadTask;
  report: AnssiReport | null;
  loadingReport: boolean;
  analyzing: boolean;
  handleAnalyze: () => void;
}

export function AnssiReportSection({
  selectedTask,
  report,
  loadingReport,
  analyzing,
  handleAnalyze,
}: AnssiReportSectionProps) {
  // Group findings by category
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
                              {failCount} echoue(s)
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
  );
}
