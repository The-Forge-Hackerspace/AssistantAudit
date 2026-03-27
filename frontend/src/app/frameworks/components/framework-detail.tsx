"use client";

import { useEffect, useState, useMemo } from "react";
import {
  Search,
  Loader2,
  ArrowLeft,
  Download,
  Copy,
  Shield,
  ChevronDown,
  ChevronUp,
  Eye,
  Settings,
  FileText,
  Layers,
  CheckCircle,
  Pencil,
  Trash2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/contexts/auth-context";
import { frameworksApi } from "@/services/api";
import type { Framework, FrameworkCategory, Control } from "@/types";
import { toast } from "sonner";
import {
  SEVERITY_ORDER,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
  SEVERITY_ICONS,
  ENGINE_LABELS,
  CHECK_TYPE_LABELS,
  getFrameworkIcon,
} from "@/lib/constants";

// ── Props ──

export interface FrameworkDetailProps {
  framework: Framework;
  onBack: () => void;
  onEdit: () => void;
  onDeleted: () => void;
}

// ══════════════════════════════════════════════════════════
// ──  DETAIL VIEW
// ══════════════════════════════════════════════════════════
export function FrameworkDetail({
  framework,
  onBack,
  onEdit,
  onDeleted,
}: FrameworkDetailProps) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [search, setSearch] = useState("");
  const [expandedCategory, setExpandedCategory] = useState<number | null>(null);
  const [cloneOpen, setCloneOpen] = useState(false);
  const [cloneVersion, setCloneVersion] = useState("");
  const [cloneName, setCloneName] = useState("");
  const [cloning, setCloning] = useState(false);
  const [cloneError, setCloneError] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const icon = getFrameworkIcon(framework.ref_id);

  // Severity counts across all controls
  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const cat of framework.categories) {
      for (const ctrl of cat.controls) {
        counts[ctrl.severity] = (counts[ctrl.severity] || 0) + 1;
      }
    }
    return counts;
  }, [framework]);

  // Total controls
  const totalControls = useMemo(
    () => framework.categories.reduce((sum, cat) => sum + cat.controls.length, 0),
    [framework]
  );

  // Filter categories/controls by search
  const filteredCategories = useMemo(() => {
    if (!search.trim()) return framework.categories;
    const q = search.toLowerCase();
    return framework.categories
      .map((cat) => ({
        ...cat,
        controls: cat.controls.filter(
          (c) =>
            c.ref_id.toLowerCase().includes(q) ||
            c.title.toLowerCase().includes(q) ||
            (c.description || "").toLowerCase().includes(q) ||
            c.severity.toLowerCase().includes(q)
        ),
      }))
      .filter((cat) => cat.controls.length > 0 || cat.name.toLowerCase().includes(q));
  }, [framework, search]);

  const filteredControlCount = useMemo(
    () => filteredCategories.reduce((sum, cat) => sum + cat.controls.length, 0),
    [filteredCategories]
  );

  // Export YAML
  const handleExport = async () => {
    try {
      const blob = await frameworksApi.exportYaml(framework.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${framework.ref_id}_v${framework.version}.yaml`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Erreur lors de l'export du référentiel");
    }
  };

  // Clone
  const handleClone = async () => {
    if (!cloneVersion.trim()) {
      setCloneError("La version est obligatoire");
      return;
    }
    setCloning(true);
    setCloneError("");
    try {
      await frameworksApi.clone(framework.id, cloneVersion, cloneName || undefined);
      setCloneOpen(false);
      onBack(); // go back to list to see the new version
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setCloneError(err.response?.data?.detail || "Erreur lors du clonage");
    } finally {
      setCloning(false);
    }
  };

  // Auto-expand all when searching
  useEffect(() => {
    if (search.trim()) {
      setExpandedCategory(-1); // -1 = all expanded
    }
  }, [search]);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await frameworksApi.delete(framework.id);
      toast.success("Référentiel supprimé");
      onDeleted();
    } catch {
      toast.error("Erreur lors de la suppression");
    } finally {
      setDeleting(false);
      setDeleteOpen(false);
    }
  };

  const isExpanded = (catId: number) =>
    expandedCategory === -1 || expandedCategory === catId;

  const toggleCategory = (catId: number) => {
    if (expandedCategory === -1) {
      setExpandedCategory(catId);
    } else {
      setExpandedCategory(expandedCategory === catId ? null : catId);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Back + actions */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={onBack} className="gap-2">
          <ArrowLeft />
          Retour aux référentiels
        </Button>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <>
              <Button variant="outline" size="sm" onClick={onEdit}>
                <Pencil data-icon="inline-start" />
                Modifier
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 data-icon="inline-start" />
                Supprimer
              </Button>
            </>
          )}
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download data-icon="inline-start" />
            Exporter YAML
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setCloneError("");
              setCloneVersion("");
              setCloneName("");
              setCloneOpen(true);
            }}
          >
            <Copy data-icon="inline-start" />
            Cloner
          </Button>
        </div>
      </div>

      {/* Framework header card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <span className="text-4xl">{icon}</span>
            <div className="flex-1 flex flex-col gap-3">
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-2xl font-bold">{framework.name}</h1>
                  <p className="text-sm text-muted-foreground font-mono mt-0.5">
                    {framework.ref_id} — v{framework.version}
                  </p>
                </div>
                <Badge variant="secondary">
                  {ENGINE_LABELS[framework.engine || "manual"] || framework.engine}
                </Badge>
              </div>
              {framework.description && (
                <p className="text-sm text-muted-foreground">{framework.description}</p>
              )}
              {(framework.source || framework.author) && (
                <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
                  {framework.source && (
                    <span><span className="font-medium text-foreground">Source :</span> {framework.source}</span>
                  )}
                  {framework.author && (
                    <span><span className="font-medium text-foreground">Auteur :</span> {framework.author}</span>
                  )}
                </div>
              )}

              <Separator />

              {/* Stats */}
              <div className="flex flex-wrap gap-6">
                <div className="text-center">
                  <p className="text-2xl font-bold">{totalControls}</p>
                  <p className="text-xs text-muted-foreground">Contrôles</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold">{framework.categories.length}</p>
                  <p className="text-xs text-muted-foreground">Catégories</p>
                </div>
                <Separator orientation="vertical" className="h-12" />
                {SEVERITY_ORDER.map((sev) => {
                  const count = severityCounts[sev] || 0;
                  if (count === 0) return null;
                  const SevIcon = SEVERITY_ICONS[sev];
                  return (
                    <div key={sev} className="text-center">
                      <div className="flex items-center justify-center gap-1">
                        <SevIcon className="h-3.5 w-3.5" />
                        <p className="text-lg font-bold">{count}</p>
                      </div>
                      <p className="text-[10px] text-muted-foreground">{SEVERITY_LABELS[sev]}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search controls */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          placeholder="Rechercher un contrôle (ref, titre, description, sévérité)\u2026"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
        {search && (
          <p className="text-xs text-muted-foreground mt-1.5 ml-1">
            {filteredControlCount} contrôle{filteredControlCount !== 1 ? "s" : ""} trouvé
            {filteredControlCount !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      {/* Expand/Collapse all */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          {framework.categories.length} catégorie{framework.categories.length !== 1 ? "s" : ""}
        </p>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpandedCategory(-1)}
            className="text-xs"
          >
            Tout déplier
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpandedCategory(null)}
            className="text-xs"
          >
            Tout replier
          </Button>
        </div>
      </div>

      {/* Categories */}
      <div className="flex flex-col gap-3">
        {filteredCategories.map((cat) => (
          <CategoryCard
            key={cat.id}
            category={cat}
            expanded={isExpanded(cat.id)}
            onToggle={() => toggleCategory(cat.id)}
            searchQuery={search}
          />
        ))}
        {filteredCategories.length === 0 && search && (
          <Card>
            <CardContent className="text-center py-8 text-muted-foreground">
              <Search className="size-8 mx-auto mb-2 opacity-50" />
              <p>Aucun contrôle ne correspond à &quot;{search}&quot;</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Clone dialog */}
      <Dialog open={cloneOpen} onOpenChange={setCloneOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Cloner le référentiel</DialogTitle>
            <DialogDescription>
              Créer une nouvelle version à partir de &quot;{framework.name}&quot; v{framework.version}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label>Nouvelle version *</Label>
              <Input
                placeholder="Ex : 2.0"
                value={cloneVersion}
                onChange={(e) => setCloneVersion(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label>Nouveau nom (optionnel)</Label>
              <Input
                placeholder={framework.name}
                value={cloneName}
                onChange={(e) => setCloneName(e.target.value)}
              />
            </div>
            {cloneError && (
              <p className="text-sm text-destructive">{cloneError}</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloneOpen(false)}>
              Annuler
            </Button>
            <Button onClick={handleClone} disabled={cloning}>
              {cloning && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Cloner
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer le référentiel</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer &quot;{framework.name}&quot; v{framework.version} ?
              Cette action est irréversible et supprimera toutes les catégories et contrôles associés.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteOpen(false)}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Supprimer définitivement
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ── Category Card ──
function CategoryCard({
  category,
  expanded,
  onToggle,
  searchQuery,
}: {
  category: FrameworkCategory;
  expanded: boolean;
  onToggle: () => void;
  searchQuery: string;
}) {
  // Severity distribution for this category
  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const ctrl of category.controls) {
      counts[ctrl.severity] = (counts[ctrl.severity] || 0) + 1;
    }
    return counts;
  }, [category]);
  return (
    <Card className="overflow-hidden">
      {/* Category header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/30 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <Layers className="size-4 text-muted-foreground shrink-0" />
          <div className="min-w-0">
            <p className="font-medium truncate">{category.name}</p>
            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
              <span>{category.controls.length} contrôle{category.controls.length !== 1 ? "s" : ""}</span>
              {category.description && (
                <span className="truncate max-w-xs hidden sm:inline">— {category.description}</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Severity mini-badges */}
          <div className="hidden sm:flex items-center gap-1">
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
            <ChevronUp className="size-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="size-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Controls table */}
      {expanded && (
        <div className="border-t">
          <div className="max-h-[500px] overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[90px]">Réf.</TableHead>
                  <TableHead>Contrôle</TableHead>
                  <TableHead className="w-[90px]">Sévérité</TableHead>
                  <TableHead className="w-[100px]">Type</TableHead>
                  <TableHead className="w-[80px] text-center">Preuve</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {category.controls.map((ctrl) => (
                  <ControlRow
                    key={ctrl.id}
                    control={ctrl}
                    searchQuery={searchQuery}
                  />
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </Card>
  );
}

// ── Control Row ──
function ControlRow({
  control: ctrl,
  searchQuery,
}: {
  control: Control;
  searchQuery: string;
}) {
  const [showDetails, setShowDetails] = useState(false);

  const checkTypeIcon = (type: string | null) => {
    switch (type) {
      case "automatic":
        return <Settings className="size-3 mr-1" />;
      case "semi-automatic":
        return <Settings className="size-3 mr-1" />;
      default:
        return <FileText className="size-3 mr-1" />;
    }
  };

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        onClick={() => setShowDetails(!showDetails)}
      >
        <TableCell>
          <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">
            {ctrl.ref_id}
          </code>
        </TableCell>
        <TableCell>
          <p className="text-sm">{ctrl.title}</p>
        </TableCell>
        <TableCell>
          <span
            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${SEVERITY_COLORS[ctrl.severity]}`}
          >
            {SEVERITY_LABELS[ctrl.severity]}
          </span>
        </TableCell>
        <TableCell>
          <span className="flex items-center text-xs text-muted-foreground">
            {checkTypeIcon(ctrl.check_type)}
            {CHECK_TYPE_LABELS[ctrl.check_type || ""] || ctrl.check_type || "\u2014"}
          </span>
        </TableCell>
        <TableCell className="text-center">
          {ctrl.check_type === "manual" ||
          ctrl.check_type === "semi-automatic" ? (
            <CheckCircle className="h-3.5 w-3.5 text-muted-foreground mx-auto" />
          ) : (
            <span className="text-xs text-muted-foreground">\u2014</span>
          )}
        </TableCell>
      </TableRow>

      {/* Expanded detail row */}
      {showDetails && (
        <TableRow className="bg-muted/20">
          <TableCell colSpan={5}>
            <div className="py-2 px-1 flex flex-col gap-2 text-sm">
              {ctrl.description && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-0.5">Description</p>
                  <p>{ctrl.description}</p>
                </div>
              )}
              {ctrl.remediation && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-0.5">Remédiation</p>
                  <p className="text-muted-foreground">{ctrl.remediation}</p>
                </div>
              )}
              {ctrl.engine_rule_id && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-0.5">Règle moteur</p>
                  <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{ctrl.engine_rule_id}</code>
                </div>
              )}
              {!ctrl.description && !ctrl.remediation && !ctrl.engine_rule_id && (
                <p className="text-muted-foreground italic">Aucun détail supplémentaire.</p>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
