"use client";

import { Suspense, useEffect, useState, useCallback, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Loader2,
  Shield,
  ShieldAlert,
  AlertTriangle,
  Info,
  CheckCircle,
  AlertCircle,
  CircleDot,
  Minus,
  ChevronDown,
  ChevronUp,
  Save,
  Zap,
  Server,
  Search,
  Layers,
  FileText,
  MessageSquare,
  Wrench,
  Eye,
  Filter,
  BarChart3,
  Download,
  Trash2,
  X,
  Paperclip,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { assessmentsApi, frameworksApi, attachmentsApi } from "@/services/api";
import { toast } from "sonner";
import { AttachmentSection } from "@/components/evaluation/attachment-section";
import type {
  Assessment,
  ControlResult,
  ComplianceStatus,
  Score,
  Framework,
  Attachment,
} from "@/types";
import {
  SEVERITY_ORDER,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
  COMPLIANCE_LABELS,
  COMPLIANCE_COLORS,
  COMPLIANCE_ICONS,
  CHECK_TYPE_LABELS,
} from "@/lib/constants";

// ── Wrapper with Suspense ──
export default function EvaluationPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <EvaluationContent />
    </Suspense>
  );
}

// ── Main Component ──
function EvaluationContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const assessmentId = Number(searchParams.get("assessmentId"));

  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [framework, setFramework] = useState<Framework | null>(null);
  const [score, setScore] = useState<Score | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterSeverity, setFilterSeverity] = useState<string>("all");

  // Category expansion
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  // Currently editing control
  const [editingResultId, setEditingResultId] = useState<number | null>(null);

  const loadAssessment = useCallback(async () => {
    if (!assessmentId) return;
    setLoading(true);
    try {
      const [a, s] = await Promise.all([
        assessmentsApi.get(assessmentId),
        assessmentsApi.score(assessmentId).catch(() => null),
      ]);
      setAssessment(a);
      setScore(s);

      // Load framework for category ordering
      try {
        const fw = await frameworksApi.get(a.framework_id);
        setFramework(fw);
      } catch {
        /* framework detail not critical */
      }

      // Auto-expand all categories with results
      const catNames = new Set(a.results.map((r) => r.control_category_name || "Sans catégorie"));
      setExpandedCategories(catNames);
    } catch {
      setError("Impossible de charger l'évaluation.");
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    loadAssessment();
  }, [loadAssessment]);

  // ── Group results by category ──
  const categorizedResults = useMemo(() => {
    if (!assessment) return [];

    const catMap = new Map<string, { name: string; categoryId: number | null; results: ControlResult[] }>();

    // Use framework category order if available
    if (framework) {
      for (const cat of framework.categories) {
        catMap.set(cat.name, { name: cat.name, categoryId: cat.id, results: [] });
      }
    }

    for (const r of assessment.results) {
      const catName = r.control_category_name || "Sans catégorie";
      if (!catMap.has(catName)) {
        catMap.set(catName, { name: catName, categoryId: r.control_category_id, results: [] });
      }
      catMap.get(catName)!.results.push(r);
    }

    // Remove empty categories from framework that have no results
    return Array.from(catMap.values()).filter((cat) => cat.results.length > 0);
  }, [assessment, framework]);

  // ── Filtered results ──
  const filteredCategories = useMemo(() => {
    const q = search.toLowerCase().trim();

    return categorizedResults
      .map((cat) => ({
        ...cat,
        results: cat.results.filter((r) => {
          // Status filter
          if (filterStatus !== "all" && r.status !== filterStatus) return false;
          // Severity filter
          if (filterSeverity !== "all" && r.control_severity !== filterSeverity) return false;
          // Search filter
          if (q) {
            return (
              (r.control_ref_id || "").toLowerCase().includes(q) ||
              (r.control_title || "").toLowerCase().includes(q) ||
              (r.control_description || "").toLowerCase().includes(q)
            );
          }
          return true;
        }),
      }))
      .filter((cat) => cat.results.length > 0);
  }, [categorizedResults, search, filterStatus, filterSeverity]);

  const filteredTotal = useMemo(
    () => filteredCategories.reduce((sum, c) => sum + c.results.length, 0),
    [filteredCategories]
  );

  // ── Progress stats ──
  const progressStats = useMemo(() => {
    if (!assessment) return null;
    const total = assessment.results.length;
    const assessed = assessment.results.filter((r) => r.status !== "not_assessed").length;
    return { total, assessed, percent: total > 0 ? Math.round((assessed / total) * 100) : 0 };
  }, [assessment]);

  const toggleCategory = (name: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  if (!assessmentId) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p>Aucun identifiant d&apos;évaluation fourni.</p>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/audits")}>
          Retour aux audits
        </Button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <AlertCircle className="h-10 w-10 mx-auto mb-3 opacity-50" />
        <p>{error || "Évaluation introuvable."}</p>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/audits")}>
          Retour aux audits
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.push("/audits")} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Retour aux audits
        </Button>
        {progressStats && (
          <Badge variant="outline" className="text-xs">
            {progressStats.assessed}/{progressStats.total} évalués ({progressStats.percent}%)
          </Badge>
        )}
      </div>

      {/* Assessment header card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="rounded-lg bg-primary/10 p-3">
              <Shield className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-2xl font-bold">Évaluation</h1>
                  <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Server className="h-3.5 w-3.5" />
                      {assessment.equipement_hostname || assessment.equipement_ip || `Équipement #${assessment.equipement_id}`}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Shield className="h-3.5 w-3.5" />
                      {assessment.framework_name || `Référentiel #${assessment.framework_id}`}
                    </span>
                  </div>
                </div>
                {score && score.total_controls > 0 && (
                  <div className="text-right">
                    <p className="text-3xl font-bold">{score.compliance_score}%</p>
                    <p className="text-xs text-muted-foreground">conformité</p>
                  </div>
                )}
              </div>

              <Separator />

              {/* Score breakdown */}
              {score && score.total_controls > 0 && (
                <div className="space-y-2">
                  <Progress value={score.compliance_score} className="h-2" />
                  <div className="grid grid-cols-5 gap-2 text-xs text-center">
                    <div>
                      <div className="font-medium text-green-600">{score.compliant}</div>
                      <div className="text-muted-foreground">Conformes</div>
                    </div>
                    <div>
                      <div className="font-medium text-red-600">{score.non_compliant}</div>
                      <div className="text-muted-foreground">Non conformes</div>
                    </div>
                    <div>
                      <div className="font-medium text-yellow-600">{score.partially_compliant}</div>
                      <div className="text-muted-foreground">Partiels</div>
                    </div>
                    <div>
                      <div className="font-medium text-gray-500">{score.not_applicable}</div>
                      <div className="text-muted-foreground">N/A</div>
                    </div>
                    <div>
                      <div className="font-medium text-gray-400">{score.not_assessed}</div>
                      <div className="text-muted-foreground">Non évalués</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Progress bar */}
              {progressStats && (
                <div className="flex items-center gap-3">
                  <BarChart3 className="h-4 w-4 text-muted-foreground" />
                  <div className="flex-1">
                    <Progress value={progressStats.percent} className="h-1.5" />
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {progressStats.assessed}/{progressStats.total} évalués
                  </span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher un contrôle (réf, titre, description)…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 h-9"
              />
            </div>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[180px] h-9">
                <Filter className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les statuts</SelectItem>
                <SelectItem value="not_assessed">Non évalués</SelectItem>
                <SelectItem value="compliant">Conformes</SelectItem>
                <SelectItem value="non_compliant">Non conformes</SelectItem>
                <SelectItem value="partially_compliant">Partiels</SelectItem>
                <SelectItem value="not_applicable">N/A</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterSeverity} onValueChange={setFilterSeverity}>
              <SelectTrigger className="w-[160px] h-9">
                <ShieldAlert className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes sévérités</SelectItem>
                <SelectItem value="critical">🔴 Critique</SelectItem>
                <SelectItem value="high">🟠 Élevée</SelectItem>
                <SelectItem value="medium">🟡 Moyenne</SelectItem>
                <SelectItem value="low">🔵 Faible</SelectItem>
                <SelectItem value="info">⚪ Info</SelectItem>
              </SelectContent>
            </Select>
            {(search || filterStatus !== "all" || filterSeverity !== "all") && (
              <div className="text-xs text-muted-foreground">
                {filteredTotal} contrôle{filteredTotal !== 1 ? "s" : ""}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Expand/Collapse all */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          {filteredCategories.length} catégorie{filteredCategories.length !== 1 ? "s" : ""}
        </p>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpandedCategories(new Set(categorizedResults.map((c) => c.name)))}
            className="text-xs"
          >
            Tout déplier
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpandedCategories(new Set())}
            className="text-xs"
          >
            Tout replier
          </Button>
        </div>
      </div>

      {/* Categories with controls */}
      <div className="space-y-4">
        {filteredCategories.map((cat) => (
          <EvaluationCategoryCard
            key={cat.name}
            categoryName={cat.name}
            results={cat.results}
            expanded={expandedCategories.has(cat.name)}
            onToggle={() => toggleCategory(cat.name)}
            editingResultId={editingResultId}
            onEditResult={setEditingResultId}
            onResultSaved={() => {
              setEditingResultId(null);
              loadAssessment();
            }}
          />
        ))}
        {filteredCategories.length === 0 && (
          <Card>
            <CardContent className="text-center py-8 text-muted-foreground">
              <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>Aucun contrôle ne correspond aux filtres.</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// ── EVALUATION CATEGORY CARD
// ══════════════════════════════════════════════════════════
function EvaluationCategoryCard({
  categoryName,
  results,
  expanded,
  onToggle,
  editingResultId,
  onEditResult,
  onResultSaved,
}: {
  categoryName: string;
  results: ControlResult[];
  expanded: boolean;
  onToggle: () => void;
  editingResultId: number | null;
  onEditResult: (id: number | null) => void;
  onResultSaved: () => void;
}) {
  // Category stats
  const stats = useMemo(() => {
    const total = results.length;
    const assessed = results.filter((r) => r.status !== "not_assessed").length;
    const compliant = results.filter((r) => r.status === "compliant").length;
    const nonCompliant = results.filter((r) => r.status === "non_compliant").length;
    return { total, assessed, compliant, nonCompliant, percent: total > 0 ? Math.round((assessed / total) * 100) : 0 };
  }, [results]);

  // Severity counts
  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of results) {
      const sev = r.control_severity || "info";
      counts[sev] = (counts[sev] || 0) + 1;
    }
    return counts;
  }, [results]);

  return (
    <Card className="overflow-hidden">
      {/* Category header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/30 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <Layers className="h-4 w-4 text-muted-foreground shrink-0" />
          <div className="min-w-0">
            <p className="font-medium truncate">{categoryName}</p>
            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
              <span>{stats.assessed}/{stats.total} évalués</span>
              {stats.compliant > 0 && <span className="text-green-600">{stats.compliant} ✓</span>}
              {stats.nonCompliant > 0 && <span className="text-red-600">{stats.nonCompliant} ✗</span>}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* Progress */}
          <div className="hidden sm:flex items-center gap-2">
            <Progress value={stats.percent} className="h-1.5 w-16" />
            <span className="text-xs text-muted-foreground w-8">{stats.percent}%</span>
          </div>
          {/* Severity mini-badges */}
          <div className="hidden md:flex items-center gap-1">
            {SEVERITY_ORDER.map((sev) => {
              const count = severityCounts[sev];
              if (!count) return null;
              return (
                <span
                  key={sev}
                  className={`inline-flex items-center rounded-full border px-1.5 py-0 text-[10px] font-medium ${SEVERITY_COLORS[sev]}`}
                >
                  {count}
                </span>
              );
            })}
          </div>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Expanded: control results */}
      {expanded && (
        <div className="border-t divide-y">
          {results.map((r) => (
            <EvaluationControlRow
              key={r.id}
              result={r}
              isEditing={editingResultId === r.id}
              onEdit={() => onEditResult(editingResultId === r.id ? null : r.id)}
              onSaved={onResultSaved}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

// ══════════════════════════════════════════════════════════
// ── EVALUATION CONTROL ROW
// ══════════════════════════════════════════════════════════
function EvaluationControlRow({
  result: r,
  isEditing,
  onEdit,
  onSaved,
}: {
  result: ControlResult;
  isEditing: boolean;
  onEdit: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    status: r.status as string,
    evidence: r.evidence || "",
    comment: r.comment || "",
    remediation_note: r.remediation_note || "",
  });
  const [saving, setSaving] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  // Attachments state
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [attachmentsLoaded, setAttachmentsLoaded] = useState(false);

  // Load attachments when editing or viewing details
  const loadAttachments = useCallback(async () => {
    try {
      const data = await attachmentsApi.list(r.id);
      setAttachments(data);
      setAttachmentsLoaded(true);
    } catch {
      /* ignore */
    }
  }, [r.id]);

  useEffect(() => {
    if ((isEditing || showDetails) && !attachmentsLoaded) {
      loadAttachments();
    }
  }, [isEditing, showDetails, attachmentsLoaded, loadAttachments]);

  // Sync form when opening edit
  useEffect(() => {
    if (isEditing) {
      setForm({
        status: r.status,
        evidence: r.evidence || "",
        comment: r.comment || "",
        remediation_note: r.remediation_note || "",
      });
    }
  }, [isEditing, r]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await assessmentsApi.updateResult(r.id, {
        status: form.status as ComplianceStatus,
        evidence: form.evidence || undefined,
        comment: form.comment || undefined,
        remediation_note: form.remediation_note || undefined,
      });
      onSaved();
      toast.success("Contrôle mis à jour");
    } catch {
      toast.error("Erreur lors de la sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  // Quick status change (inline dropdown)
  const handleQuickStatus = async (newStatus: string) => {
    try {
      await assessmentsApi.updateResult(r.id, {
        status: newStatus as ComplianceStatus,
      });
      onSaved();
      toast.success("Statut mis à jour");
    } catch {
      toast.error("Erreur lors de la mise à jour");
    }
  };

  const StatusIcon = COMPLIANCE_ICONS[r.status] || CircleDot;

  return (
    <div className={`${isEditing ? "bg-muted/20" : "hover:bg-muted/10"} transition-colors`}>
      {/* Main row */}
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Status icon */}
        <StatusIcon
          className={`h-5 w-5 shrink-0 ${
            r.status === "compliant"
              ? "text-green-600"
              : r.status === "non_compliant"
              ? "text-red-600"
              : r.status === "partially_compliant"
              ? "text-yellow-600"
              : r.status === "not_applicable"
              ? "text-gray-400"
              : "text-gray-300"
          }`}
        />

        {/* Control info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono shrink-0">
              {r.control_ref_id || `C${r.control_id}`}
            </code>
            <p className="text-sm truncate">{r.control_title || `Contrôle #${r.control_id}`}</p>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            {r.control_severity && (
              <span
                className={`inline-flex items-center rounded-full border px-1.5 py-0 text-[10px] font-medium ${SEVERITY_COLORS[r.control_severity]}`}
              >
                {SEVERITY_LABELS[r.control_severity]}
              </span>
            )}
            {r.control_check_type && (
              <span className="text-[10px] text-muted-foreground">
                {CHECK_TYPE_LABELS[r.control_check_type] || r.control_check_type}
              </span>
            )}
            {r.is_auto_assessed && (
              <Badge variant="outline" className="text-[10px] px-1 py-0">
                <Zap className="h-2.5 w-2.5 mr-0.5" />auto
              </Badge>
            )}
            {/* Indicators for evidence/comment/attachments */}
            {r.evidence && (
              <span title="Preuve renseignée"><Eye className="h-3 w-3 text-blue-500" /></span>
            )}
            {r.comment && (
              <span title="Commentaire"><MessageSquare className="h-3 w-3 text-blue-500" /></span>
            )}
            {r.remediation_note && (
              <span title="Note de remédiation"><Wrench className="h-3 w-3 text-orange-500" /></span>
            )}
            {attachments.length > 0 && (
              <span title={`${attachments.length} pièce(s) jointe(s)`}>
                <Paperclip className="h-3 w-3 text-purple-500" />
              </span>
            )}
          </div>
        </div>

        {/* Right side: quick status + actions */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Inline status dropdown */}
          <Select value={r.status} onValueChange={handleQuickStatus}>
            <SelectTrigger className="h-8 w-[170px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="not_assessed">
                <span className="flex items-center gap-1.5">
                  <CircleDot className="h-3 w-3 text-gray-300" /> Non évalué
                </span>
              </SelectItem>
              <SelectItem value="compliant">
                <span className="flex items-center gap-1.5">
                  <CheckCircle className="h-3 w-3 text-green-600" /> Conforme
                </span>
              </SelectItem>
              <SelectItem value="non_compliant">
                <span className="flex items-center gap-1.5">
                  <AlertCircle className="h-3 w-3 text-red-600" /> Non conforme
                </span>
              </SelectItem>
              <SelectItem value="partially_compliant">
                <span className="flex items-center gap-1.5">
                  <CircleDot className="h-3 w-3 text-yellow-600" /> Partiel
                </span>
              </SelectItem>
              <SelectItem value="not_applicable">
                <span className="flex items-center gap-1.5">
                  <Minus className="h-3 w-3 text-gray-400" /> N/A
                </span>
              </SelectItem>
            </SelectContent>
          </Select>

          {/* Show description */}
          {(r.control_description || r.control_remediation) && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setShowDetails(!showDetails)}
            >
              <Info className="h-3.5 w-3.5" />
            </Button>
          )}

          {/* Edit button */}
          <Button
            variant={isEditing ? "secondary" : "ghost"}
            size="sm"
            className="h-7 w-7 p-0"
            onClick={onEdit}
          >
            <FileText className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Control description / remediation reference (from framework) */}
      {showDetails && !isEditing && (
        <div className="px-4 pb-3 ml-8 space-y-3">
          {r.control_description && (
            <div className="bg-muted/30 rounded-md p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Description du contrôle</p>
              <p className="text-sm">{r.control_description}</p>
            </div>
          )}
          {r.control_remediation && (
            <div className="bg-orange-50 dark:bg-orange-950/20 rounded-md p-3">
              <p className="text-xs font-medium text-orange-700 dark:text-orange-400 mb-1">Remédiation recommandée</p>
              <p className="text-sm text-orange-800 dark:text-orange-300">{r.control_remediation}</p>
            </div>
          )}
          {r.evidence && (
            <div className="bg-muted/30 rounded-md p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Preuve / Évidence</p>
              <p className="text-sm whitespace-pre-wrap">{r.evidence}</p>
            </div>
          )}
          {attachments.length > 0 && (
            <AttachmentSection
              controlResultId={r.id}
              attachments={attachments}
              onChanged={loadAttachments}
              readOnly
            />
          )}
          {r.comment && (
            <div className="bg-muted/30 rounded-md p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Commentaire</p>
              <p className="text-sm whitespace-pre-wrap">{r.comment}</p>
            </div>
          )}
          {r.remediation_note && (
            <div className="bg-muted/30 rounded-md p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Note de remédiation</p>
              <p className="text-sm whitespace-pre-wrap">{r.remediation_note}</p>
            </div>
          )}
        </div>
      )}

      {/* Editing panel */}
      {isEditing && (
        <div className="px-4 pb-4 ml-8 space-y-4 border-t pt-4">
          {/* Status selector (larger in edit mode) */}
          <div className="space-y-2">
            <Label className="text-xs font-medium">Statut de conformité</Label>
            <div className="grid grid-cols-5 gap-2">
              {(["compliant", "non_compliant", "partially_compliant", "not_applicable", "not_assessed"] as ComplianceStatus[]).map(
                (s) => {
                  const Icon = COMPLIANCE_ICONS[s];
                  return (
                    <button
                      key={s}
                      type="button"
                      className={`flex flex-col items-center gap-1 rounded-md border p-2 text-xs transition-colors ${
                        form.status === s
                          ? `${COMPLIANCE_COLORS[s]} ring-2 ring-offset-1 ring-primary/30`
                          : "border-gray-200 hover:bg-muted/50"
                      }`}
                      onClick={() => setForm({ ...form, status: s })}
                    >
                      <Icon className="h-4 w-4" />
                      <span className="text-[10px] font-medium leading-tight text-center">
                        {COMPLIANCE_LABELS[s]}
                      </span>
                    </button>
                  );
                }
              )}
            </div>
          </div>

          {/* Control description for reference */}
          {r.control_description && (
            <div className="bg-muted/30 rounded-md p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Description du contrôle</p>
              <p className="text-sm">{r.control_description}</p>
            </div>
          )}

          {/* Evidence text */}
          <div className="space-y-2">
            <Label className="text-xs font-medium flex items-center gap-1.5">
              <Eye className="h-3.5 w-3.5" />
              Preuve / Évidence (texte)
            </Label>
            <Textarea
              value={form.evidence}
              onChange={(e) => setForm({ ...form, evidence: e.target.value })}
              placeholder="Commandes exécutées, résultats observés…"
              className="text-sm min-h-[80px]"
            />
          </div>

          {/* Attachments (file upload) */}
          <AttachmentSection
            controlResultId={r.id}
            attachments={attachments}
            onChanged={loadAttachments}
          />

          {/* Comment */}
          <div className="space-y-2">
            <Label className="text-xs font-medium flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5" />
              Commentaire
            </Label>
            <Textarea
              value={form.comment}
              onChange={(e) => setForm({ ...form, comment: e.target.value })}
              placeholder="Observations de l'auditeur…"
              className="text-sm min-h-[60px]"
            />
          </div>

          {/* Remediation */}
          <div className="space-y-2">
            <Label className="text-xs font-medium flex items-center gap-1.5">
              <Wrench className="h-3.5 w-3.5" />
              Note de remédiation
            </Label>
            {r.control_remediation && (
              <div className="bg-orange-50 dark:bg-orange-950/20 rounded-md p-2 mb-1">
                <p className="text-[10px] font-medium text-orange-700 dark:text-orange-400 mb-0.5">Remédiation de référence</p>
                <p className="text-xs text-orange-800 dark:text-orange-300">{r.control_remediation}</p>
              </div>
            )}
            <Textarea
              value={form.remediation_note}
              onChange={(e) => setForm({ ...form, remediation_note: e.target.value })}
              placeholder="Actions recommandées pour la mise en conformité…"
              className="text-sm min-h-[60px]"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-1">
            <Button variant="outline" size="sm" onClick={onEdit}>
              Annuler
            </Button>
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving ? (
                <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-1.5" />
              )}
              Sauvegarder
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
