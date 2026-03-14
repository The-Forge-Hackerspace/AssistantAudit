"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  BookOpen,
  Search,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  Download,
  RefreshCw,
  Copy,
  Shield,
  ChevronDown,
  ChevronUp,
  Eye,
  Settings,
  FileText,
  Layers,
  CheckCircle,
  Plus,
  Pencil,
  Trash2,
  GripVertical,
  Save,
  X,
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
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/contexts/auth-context";
import { frameworksApi } from "@/services/api";
import type { FrameworkSummary, Framework, FrameworkCategory, Control, FrameworkCreatePayload, CategoryCreate, ControlCreate } from "@/types";
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

// ── Main Page ──
export default function FrameworksPage() {
  const [view, setView] = useState<"list" | "detail" | "editor">("list");
  const [selectedFramework, setSelectedFramework] = useState<Framework | null>(null);
  const [editingFramework, setEditingFramework] = useState<Framework | null>(null);
  const [listKey, setListKey] = useState(0);

  const openDetail = async (fw: FrameworkSummary) => {
    try {
      const full = await frameworksApi.get(fw.id);
      setSelectedFramework(full);
      setView("detail");
    } catch {
      /* ignore */
    }
  };

  const openEditor = (fw?: Framework) => {
    setEditingFramework(fw || null);
    setView("editor");
  };

  const backToList = () => {
    setView("list");
    setSelectedFramework(null);
    setEditingFramework(null);
    setListKey((k) => k + 1);
  };

  if (view === "editor") {
    return (
      <FrameworkEditor
        framework={editingFramework}
        onBack={() => {
          if (selectedFramework && !editingFramework) {
            setView("list");
          } else if (editingFramework) {
            setView("detail");
          } else {
            setView("list");
          }
          setEditingFramework(null);
        }}
        onSaved={backToList}
      />
    );
  }

  if (view === "detail" && selectedFramework) {
    return (
      <FrameworkDetail
        framework={selectedFramework}
        onBack={() => {
          setView("list");
          setSelectedFramework(null);
        }}
        onEdit={() => openEditor(selectedFramework)}
        onDeleted={backToList}
      />
    );
  }

  return <FrameworkList key={listKey} onSelect={openDetail} onCreate={() => openEditor()} />;
}

// ══════════════════════════════════════════════════════════
// ──  LIST VIEW
// ══════════════════════════════════════════════════════════
function FrameworkList({ onSelect, onCreate }: { onSelect: (fw: FrameworkSummary) => void; onCreate: () => void }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [frameworks, setFrameworks] = useState<FrameworkSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const pageSize = 20;

  const loadFrameworks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await frameworksApi.list(page, pageSize);
      setFrameworks(res.items);
      setTotal(res.total);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadFrameworks();
  }, [loadFrameworks]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await frameworksApi.sync();
      loadFrameworks();
    } catch {
      /* ignore */
    } finally {
      setSyncing(false);
    }
  };

  const filtered = useMemo(() => {
    if (!search.trim()) return frameworks;
    const q = search.toLowerCase();
    return frameworks.filter(
      (fw) =>
        fw.name.toLowerCase().includes(q) ||
        fw.ref_id.toLowerCase().includes(q) ||
        (fw.engine || "").toLowerCase().includes(q)
    );
  }, [frameworks, search]);

  const pages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Référentiels</h1>
          <p className="text-muted-foreground">
            {total} référentiel{total !== 1 ? "s" : ""} d&apos;audit disponibles
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <Button onClick={onCreate}>
              <Plus className="h-4 w-4 mr-2" />
              Nouveau référentiel
            </Button>
          )}
          <Button variant="outline" onClick={handleSync} disabled={syncing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Synchronisation…" : "Synchroniser"}
          </Button>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher un référentiel…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* Frameworks Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">
            <BookOpen className="h-10 w-10 mx-auto mb-3 opacity-50" />
            <p className="font-medium">Aucun référentiel trouvé</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((fw) => (
            <FrameworkCard key={fw.id} framework={fw} onClick={() => onSelect(fw)} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} / {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}

// ── Framework Card ──
function FrameworkCard({
  framework: fw,
  onClick,
}: {
  framework: FrameworkSummary;
  onClick: () => void;
}) {
  const icon = getFrameworkIcon(fw.ref_id);

  return (
    <Card
      className="cursor-pointer hover:shadow-md hover:border-primary/30 transition-all group"
      onClick={onClick}
    >
      <CardContent className="pt-6 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <span className="text-2xl shrink-0">{icon}</span>
            <div className="min-w-0">
              <p className="font-semibold truncate group-hover:text-primary transition-colors">
                {fw.name}
              </p>
              <p className="text-xs text-muted-foreground font-mono">{fw.ref_id}</p>
            </div>
          </div>
          <Badge variant="outline" className="text-[10px] shrink-0 ml-2">
            v{fw.version}
          </Badge>
        </div>

        {/* Stats row */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Shield className="h-3.5 w-3.5" />
            <span>{fw.total_controls} contrôles</span>
          </div>
          <Badge
            variant="secondary"
            className="text-[10px]"
          >
            {ENGINE_LABELS[fw.engine || "manual"] || fw.engine}
          </Badge>
        </div>

        {/* Footer: view button hint */}
        <div className="flex items-center justify-end text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
          <Eye className="h-3 w-3 mr-1" />
          Voir le détail
        </div>
      </CardContent>
    </Card>
  );
}

// ══════════════════════════════════════════════════════════
// ──  DETAIL VIEW
// ══════════════════════════════════════════════════════════
function FrameworkDetail({
  framework,
  onBack,
  onEdit,
  onDeleted,
}: {
  framework: Framework;
  onBack: () => void;
  onEdit: () => void;
  onDeleted: () => void;
}) {
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
      /* ignore */
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
    <div className="space-y-6">
      {/* Back + actions */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={onBack} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Retour aux référentiels
        </Button>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <>
              <Button variant="outline" size="sm" onClick={onEdit}>
                <Pencil className="h-4 w-4 mr-2" />
                Modifier
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Supprimer
              </Button>
            </>
          )}
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
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
            <Copy className="h-4 w-4 mr-2" />
            Cloner
          </Button>
        </div>
      </div>

      {/* Framework header card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <span className="text-4xl">{icon}</span>
            <div className="flex-1 space-y-3">
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
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Rechercher un contrôle (ref, titre, description, sévérité)…"
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
      <div className="space-y-3">
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
              <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
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
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Nouvelle version *</Label>
              <Input
                placeholder="Ex : 2.0"
                value={cloneVersion}
                onChange={(e) => setCloneVersion(e.target.value)}
              />
            </div>
            <div className="space-y-2">
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
              {cloning && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Cloner
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Supprimer le référentiel</DialogTitle>
            <DialogDescription>
              Êtes-vous sûr de vouloir supprimer &quot;{framework.name}&quot; v{framework.version} ?
              Cette action est irréversible et supprimera toutes les catégories et contrôles associés.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Annuler
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Supprimer définitivement
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
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
          <Layers className="h-4 w-4 text-muted-foreground shrink-0" />
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
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
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
        return <Settings className="h-3 w-3 mr-1" />;
      case "semi-automatic":
        return <Settings className="h-3 w-3 mr-1" />;
      default:
        return <FileText className="h-3 w-3 mr-1" />;
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
            {CHECK_TYPE_LABELS[ctrl.check_type || ""] || ctrl.check_type || "—"}
          </span>
        </TableCell>
        <TableCell className="text-center">
          {ctrl.check_type === "manual" ||
          ctrl.check_type === "semi-automatic" ? (
            <CheckCircle className="h-3.5 w-3.5 text-muted-foreground mx-auto" />
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          )}
        </TableCell>
      </TableRow>

      {/* Expanded detail row */}
      {showDetails && (
        <TableRow className="bg-muted/20">
          <TableCell colSpan={5}>
            <div className="py-2 px-1 space-y-2 text-sm">
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

// ══════════════════════════════════════════════════════════
// ──  FRAMEWORK EDITOR / CREATOR
// ══════════════════════════════════════════════════════════

interface EditorCategory {
  _key: string;
  name: string;
  description: string;
  controls: EditorControl[];
}

interface EditorControl {
  _key: string;
  ref_id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  check_type: string;
  remediation: string;
  engine_rule_id: string;
  cis_reference: string;
  evidence_required: boolean;
}

function makeControlKey(): string {
  return `ctrl_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function makeCategoryKey(): string {
  return `cat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function newEmptyControl(): EditorControl {
  return {
    _key: makeControlKey(),
    ref_id: "",
    title: "",
    description: "",
    severity: "medium",
    check_type: "manual",
    remediation: "",
    engine_rule_id: "",
    cis_reference: "",
    evidence_required: false,
  };
}

function newEmptyCategory(): EditorCategory {
  return {
    _key: makeCategoryKey(),
    name: "",
    description: "",
    controls: [newEmptyControl()],
  };
}

function frameworkToEditor(fw: Framework): { meta: EditorMeta; categories: EditorCategory[] } {
  return {
    meta: {
      ref_id: fw.ref_id,
      name: fw.name,
      description: fw.description || "",
      version: fw.version,
      engine: fw.engine || "manual",
      engine_config: fw.engine_config ? JSON.stringify(fw.engine_config, null, 2) : "",
      source: fw.source || "",
      author: fw.author || "",
    },
    categories: fw.categories.map((cat) => ({
      _key: makeCategoryKey(),
      name: cat.name,
      description: cat.description || "",
      controls: cat.controls.map((ctrl) => ({
        _key: makeControlKey(),
        ref_id: ctrl.ref_id,
        title: ctrl.title,
        description: ctrl.description || "",
        severity: ctrl.severity as EditorControl["severity"],
        check_type: ctrl.check_type || "manual",
        remediation: ctrl.remediation || "",
        engine_rule_id: ctrl.engine_rule_id || "",
        cis_reference: ctrl.cis_reference || "",
        evidence_required: ctrl.evidence_required || false,
      })),
    })),
  };
}

interface EditorMeta {
  ref_id: string;
  name: string;
  description: string;
  version: string;
  engine: string;
  engine_config: string;
  source: string;
  author: string;
}

function FrameworkEditor({
  framework,
  onBack,
  onSaved,
}: {
  framework: Framework | null;
  onBack: () => void;
  onSaved: () => void;
}) {
  const isEditMode = !!framework;

  // Initialize state from existing framework or empty
  const initial = framework
    ? frameworkToEditor(framework)
    : {
        meta: { ref_id: "", name: "", description: "", version: "1.0", engine: "manual", engine_config: "", source: "", author: "" },
        categories: [newEmptyCategory()],
      };

  const [meta, setMeta] = useState<EditorMeta>(initial.meta);
  const [categories, setCategories] = useState<EditorCategory[]>(initial.categories);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    () => new Set(initial.categories.map((c) => c._key))
  );
  const [confirmBack, setConfirmBack] = useState(false);

  // ── Meta handlers ──
  const updateMeta = (field: keyof EditorMeta, value: string) => {
    setMeta((prev) => ({ ...prev, [field]: value }));
  };

  // ── Category handlers ──
  const addCategory = () => {
    const cat = newEmptyCategory();
    setCategories((prev) => [...prev, cat]);
    setExpandedCategories((prev) => new Set([...prev, cat._key]));
  };

  const removeCategory = (key: string) => {
    setCategories((prev) => prev.filter((c) => c._key !== key));
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
  };

  const updateCategory = (key: string, field: "name" | "description", value: string) => {
    setCategories((prev) =>
      prev.map((c) => (c._key === key ? { ...c, [field]: value } : c))
    );
  };

  const toggleCategoryExpand = (key: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // ── Control handlers ──
  const addControl = (catKey: string) => {
    setCategories((prev) =>
      prev.map((c) =>
        c._key === catKey ? { ...c, controls: [...c.controls, newEmptyControl()] } : c
      )
    );
  };

  const removeControl = (catKey: string, ctrlKey: string) => {
    setCategories((prev) =>
      prev.map((c) =>
        c._key === catKey
          ? { ...c, controls: c.controls.filter((ctrl) => ctrl._key !== ctrlKey) }
          : c
      )
    );
  };

  const updateControl = (catKey: string, ctrlKey: string, field: keyof EditorControl, value: string | boolean) => {
    setCategories((prev) =>
      prev.map((c) =>
        c._key === catKey
          ? {
              ...c,
              controls: c.controls.map((ctrl) =>
                ctrl._key === ctrlKey ? { ...ctrl, [field]: value } : ctrl
              ),
            }
          : c
      )
    );
  };

  const duplicateControl = (catKey: string, ctrlKey: string) => {
    setCategories((prev) =>
      prev.map((c) => {
        if (c._key !== catKey) return c;
        const idx = c.controls.findIndex((ctrl) => ctrl._key === ctrlKey);
        if (idx === -1) return c;
        const source = c.controls[idx];
        const dup: EditorControl = { ...source, _key: makeControlKey(), ref_id: source.ref_id + "_copy" };
        const newControls = [...c.controls];
        newControls.splice(idx + 1, 0, dup);
        return { ...c, controls: newControls };
      })
    );
  };

  // ── Validation ──
  const validate = (): string | null => {
    if (!meta.ref_id.trim()) return "L'identifiant (ref_id) est obligatoire.";
    if (!meta.name.trim()) return "Le nom est obligatoire.";
    if (!meta.version.trim()) return "La version est obligatoire.";
    if (categories.length === 0) return "Au moins une catégorie est requise.";
    for (let i = 0; i < categories.length; i++) {
      const cat = categories[i];
      if (!cat.name.trim()) return `La catégorie ${i + 1} n'a pas de nom.`;
      if (cat.controls.length === 0)
        return `La catégorie "${cat.name}" doit contenir au moins un contrôle.`;
      for (let j = 0; j < cat.controls.length; j++) {
        const ctrl = cat.controls[j];
        if (!ctrl.ref_id.trim())
          return `Le contrôle ${j + 1} de "${cat.name}" n'a pas d'identifiant.`;
        if (!ctrl.title.trim())
          return `Le contrôle ${j + 1} de "${cat.name}" n'a pas de titre.`;
      }
    }
    if (meta.engine_config.trim()) {
      try {
        JSON.parse(meta.engine_config);
      } catch {
        return "La configuration moteur n'est pas un JSON valide.";
      }
    }
    return null;
  };

  // ── Save ──
  const handleSave = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError("");
    setSaving(true);

    const payload: FrameworkCreatePayload = {
      ref_id: meta.ref_id.trim(),
      name: meta.name.trim(),
      description: meta.description.trim() || undefined,
      version: meta.version.trim(),
      engine: meta.engine || undefined,
      engine_config: meta.engine_config.trim() ? JSON.parse(meta.engine_config) : undefined,
      source: meta.source.trim() || undefined,
      author: meta.author.trim() || undefined,
      categories: categories.map((cat) => ({
        name: cat.name.trim(),
        description: cat.description.trim() || undefined,
        controls: cat.controls.map((ctrl) => ({
          ref_id: ctrl.ref_id.trim(),
          title: ctrl.title.trim(),
          description: ctrl.description.trim() || undefined,
          severity: ctrl.severity,
          check_type: ctrl.check_type,
          remediation: ctrl.remediation.trim() || undefined,
          engine_rule_id: ctrl.engine_rule_id.trim() || undefined,
          cis_reference: ctrl.cis_reference.trim() || undefined,
          evidence_required: ctrl.evidence_required,
        })),
      })),
    };

    try {
      if (isEditMode) {
        await frameworksApi.update(framework.id, payload);
        toast.success("Référentiel mis à jour");
      } else {
        await frameworksApi.create(payload);
        toast.success("Référentiel créé");
      }
      onSaved();
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr.response?.data?.detail || "Erreur lors de l'enregistrement.");
      toast.error("Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  };

  // ── Stats ──
  const totalControls = categories.reduce((sum, c) => sum + c.controls.length, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => setConfirmBack(true)} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Retour
        </Button>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {categories.length} catégorie{categories.length !== 1 ? "s" : ""} · {totalControls} contrôle{totalControls !== 1 ? "s" : ""}
          </Badge>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            {isEditMode ? "Enregistrer" : "Créer le référentiel"}
          </Button>
        </div>
      </div>

      <h1 className="text-2xl font-bold">
        {isEditMode ? "Modifier le référentiel" : "Nouveau référentiel"}
      </h1>

      {error && (
        <Card className="border-destructive bg-destructive/5">
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-destructive font-medium">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* ── Metadata Card ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Informations générales</CardTitle>
          <CardDescription>Identifiant, nom, version et moteur du référentiel</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ref_id">Identifiant (ref_id) *</Label>
              <Input
                id="ref_id"
                placeholder="Ex : firewall_audit"
                value={meta.ref_id}
                onChange={(e) => updateMeta("ref_id", e.target.value)}
                disabled={isEditMode}
              />
              {isEditMode && (
                <p className="text-[11px] text-muted-foreground">Non modifiable en édition</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Nom *</Label>
              <Input
                id="name"
                placeholder="Ex : Audit Firewall"
                value={meta.name}
                onChange={(e) => updateMeta("name", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="version">Version *</Label>
              <Input
                id="version"
                placeholder="Ex : 1.0"
                value={meta.version}
                onChange={(e) => updateMeta("version", e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Description du référentiel…"
              value={meta.description}
              onChange={(e) => updateMeta("description", e.target.value)}
              className="min-h-[60px]"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="source">Source</Label>
              <Input
                id="source"
                placeholder="Ex : CIS Benchmarks, ANSSI, NIST…"
                value={meta.source}
                onChange={(e) => updateMeta("source", e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">Recommandations sur lesquelles se base ce référentiel</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="author">Auteur</Label>
              <Input
                id="author"
                placeholder="Ex : Équipe sécurité, John Doe…"
                value={meta.author}
                onChange={(e) => updateMeta("author", e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">Créateur de ce référentiel</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Moteur</Label>
              <Select value={meta.engine} onValueChange={(v) => updateMeta("engine", v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="manual">Manuel</SelectItem>
                  <SelectItem value="monkey365">Monkey365</SelectItem>
                  <SelectItem value="nmap">Nmap</SelectItem>
                  <SelectItem value="automatic">Automatique</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {meta.engine !== "manual" && (
              <div className="space-y-2">
                <Label htmlFor="engine_config">Configuration moteur (JSON)</Label>
                <Textarea
                  id="engine_config"
                  placeholder='{ "key": "value" }'
                  value={meta.engine_config}
                  onChange={(e) => updateMeta("engine_config", e.target.value)}
                  className="font-mono text-xs min-h-[60px]"
                />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ── Categories ── */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Catégories</h2>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setExpandedCategories(new Set(categories.map((c) => c._key)))}>
            Tout déplier
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setExpandedCategories(new Set())}>
            Tout replier
          </Button>
          <Button variant="outline" size="sm" onClick={addCategory}>
            <Plus className="h-4 w-4 mr-1" />
            Catégorie
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        {categories.map((cat, catIdx) => (
          <EditorCategoryCard
            key={cat._key}
            category={cat}
            catIndex={catIdx}
            expanded={expandedCategories.has(cat._key)}
            onToggle={() => toggleCategoryExpand(cat._key)}
            onUpdate={(field, val) => updateCategory(cat._key, field, val)}
            onRemove={() => removeCategory(cat._key)}
            onAddControl={() => addControl(cat._key)}
            onRemoveControl={(ctrlKey) => removeControl(cat._key, ctrlKey)}
            onUpdateControl={(ctrlKey, field, val) => updateControl(cat._key, ctrlKey, field, val)}
            onDuplicateControl={(ctrlKey) => duplicateControl(cat._key, ctrlKey)}
            canDelete={categories.length > 1}
          />
        ))}
      </div>

      {/* Bottom save */}
      <div className="flex justify-end gap-2 pt-4 border-t">
        <Button variant="outline" onClick={() => setConfirmBack(true)}>
          Annuler
        </Button>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          {isEditMode ? "Enregistrer les modifications" : "Créer le référentiel"}
        </Button>
      </div>

      {/* Confirm back dialog */}
      <Dialog open={confirmBack} onOpenChange={setConfirmBack}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Quitter l&apos;éditeur ?</DialogTitle>
            <DialogDescription>
              Les modifications non sauvegardées seront perdues.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmBack(false)}>
              Continuer l&apos;édition
            </Button>
            <Button variant="destructive" onClick={onBack}>
              Quitter sans sauvegarder
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Editor Category Card ──
function EditorCategoryCard({
  category,
  catIndex,
  expanded,
  onToggle,
  onUpdate,
  onRemove,
  onAddControl,
  onRemoveControl,
  onUpdateControl,
  onDuplicateControl,
  canDelete,
}: {
  category: EditorCategory;
  catIndex: number;
  expanded: boolean;
  onToggle: () => void;
  onUpdate: (field: "name" | "description", value: string) => void;
  onRemove: () => void;
  onAddControl: () => void;
  onRemoveControl: (ctrlKey: string) => void;
  onUpdateControl: (ctrlKey: string, field: keyof EditorControl, value: string | boolean) => void;
  onDuplicateControl: (ctrlKey: string) => void;
  canDelete: boolean;
}) {
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
            <p className="font-medium">
              {category.name || <span className="italic text-muted-foreground">Catégorie {catIndex + 1} (sans nom)</span>}
            </p>
            <p className="text-xs text-muted-foreground">
              {category.controls.length} contrôle{category.controls.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {canDelete && (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive h-7 w-7 p-0"
              onClick={(e) => {
                e.stopPropagation();
                onRemove();
              }}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          )}
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t p-4 space-y-4">
          {/* Category fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Nom de la catégorie *</Label>
              <Input
                placeholder="Ex : Configuration réseau"
                value={category.name}
                onChange={(e) => onUpdate("name", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                placeholder="Description de la catégorie…"
                value={category.description}
                onChange={(e) => onUpdate("description", e.target.value)}
              />
            </div>
          </div>

          <Separator />

          {/* Controls */}
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">Contrôles</p>
            <Button variant="outline" size="sm" onClick={onAddControl}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              Contrôle
            </Button>
          </div>

          <div className="space-y-3">
            {category.controls.map((ctrl, ctrlIdx) => (
              <EditorControlCard
                key={ctrl._key}
                control={ctrl}
                ctrlIndex={ctrlIdx}
                onUpdate={(field, val) => onUpdateControl(ctrl._key, field, val)}
                onRemove={() => onRemoveControl(ctrl._key)}
                onDuplicate={() => onDuplicateControl(ctrl._key)}
                canDelete={category.controls.length > 1}
              />
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

// ── Editor Control Card ──
function EditorControlCard({
  control,
  ctrlIndex,
  onUpdate,
  onRemove,
  onDuplicate,
  canDelete,
}: {
  control: EditorControl;
  ctrlIndex: number;
  onUpdate: (field: keyof EditorControl, value: string | boolean) => void;
  onRemove: () => void;
  onDuplicate: () => void;
  canDelete: boolean;
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <Card className="border-dashed">
      <CardContent className="pt-4 pb-4 space-y-3">
        {/* Row 1: ref_id, title, actions */}
        <div className="flex items-start gap-3">
          <span className="text-xs text-muted-foreground mt-2 shrink-0 w-6 text-center font-mono">
            {ctrlIndex + 1}
          </span>
          <div className="flex-1 grid grid-cols-1 md:grid-cols-[140px_1fr] gap-3">
            <div className="space-y-1">
              <Label className="text-[11px]">Réf. *</Label>
              <Input
                placeholder="FW-01"
                value={control.ref_id}
                onChange={(e) => onUpdate("ref_id", e.target.value)}
                className="font-mono text-xs h-8"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-[11px]">Titre *</Label>
              <Input
                placeholder="Vérifier les règles de filtrage"
                value={control.title}
                onChange={(e) => onUpdate("title", e.target.value)}
                className="h-8"
              />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-5">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={onDuplicate}
              title="Dupliquer"
            >
              <Copy className="h-3.5 w-3.5" />
            </Button>
            {canDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                onClick={onRemove}
                title="Supprimer"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>

        {/* Row 2: severity, check_type */}
        <div className="ml-9 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="space-y-1">
            <Label className="text-[11px]">Sévérité</Label>
            <Select value={control.severity} onValueChange={(v) => onUpdate("severity", v)}>
              <SelectTrigger className="w-full h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="critical">🔴 Critique</SelectItem>
                <SelectItem value="high">🟠 Élevée</SelectItem>
                <SelectItem value="medium">🟡 Moyenne</SelectItem>
                <SelectItem value="low">🔵 Faible</SelectItem>
                <SelectItem value="info">⚪ Info</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Type de vérification</Label>
            <Select value={control.check_type} onValueChange={(v) => onUpdate("check_type", v)}>
              <SelectTrigger className="w-full h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="manual">Manuel</SelectItem>
                <SelectItem value="automatic">Automatique</SelectItem>
                <SelectItem value="semi-automatic">Semi-auto</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2 flex items-end">
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-8"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? <ChevronUp className="h-3 w-3 mr-1" /> : <ChevronDown className="h-3 w-3 mr-1" />}
              {showAdvanced ? "Masquer détails" : "Plus de détails"}
            </Button>
          </div>
        </div>

        {/* Row 3: advanced fields */}
        {showAdvanced && (
          <div className="ml-9 space-y-3 border-t pt-3">
            <div className="space-y-1">
              <Label className="text-[11px]">Description</Label>
              <Textarea
                placeholder="Description détaillée du contrôle…"
                value={control.description}
                onChange={(e) => onUpdate("description", e.target.value)}
                className="text-xs min-h-[50px]"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-[11px]">Remédiation</Label>
              <Textarea
                placeholder="Instructions de remédiation…"
                value={control.remediation}
                onChange={(e) => onUpdate("remediation", e.target.value)}
                className="text-xs min-h-[50px]"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label className="text-[11px]">Règle moteur</Label>
                <Input
                  placeholder="rule_id"
                  value={control.engine_rule_id}
                  onChange={(e) => onUpdate("engine_rule_id", e.target.value)}
                  className="font-mono text-xs h-8"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[11px]">Référence CIS</Label>
                <Input
                  placeholder="CIS 1.2.3"
                  value={control.cis_reference}
                  onChange={(e) => onUpdate("cis_reference", e.target.value)}
                  className="text-xs h-8"
                />
              </div>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={control.evidence_required}
                    onChange={(e) => onUpdate("evidence_required", e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-xs">Preuve requise</span>
                </label>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
