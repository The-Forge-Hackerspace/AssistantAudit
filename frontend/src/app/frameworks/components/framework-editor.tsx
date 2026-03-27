"use client";

import { useState } from "react";
import {
  Loader2,
  ArrowLeft,
  Copy,
  ChevronDown,
  ChevronUp,
  Layers,
  Plus,
  Pencil,
  Trash2,
  Save,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { frameworksApi } from "@/services/api";
import type { Framework, FrameworkCreatePayload } from "@/types";
import { toast } from "sonner";

// ── Props ──

export interface FrameworkEditorProps {
  framework: Framework | null;
  onBack: () => void;
  onSaved: () => void;
}

// ── Internal types ──

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

// ── Helpers ──

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

// ══════════════════════════════════════════════════════════
// ──  FRAMEWORK EDITOR / CREATOR
// ══════════════════════════════════════════════════════════
export function FrameworkEditor({
  framework,
  onBack,
  onSaved,
}: FrameworkEditorProps) {
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
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => setConfirmBack(true)} className="gap-2">
          <ArrowLeft />
          Retour
        </Button>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {categories.length} catégorie{categories.length !== 1 ? "s" : ""} · {totalControls} contrôle{totalControls !== 1 ? "s" : ""}
          </Badge>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <Loader2 className="animate-spin" data-icon="inline-start" />
            ) : (
              <Save data-icon="inline-start" />
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
        <CardContent className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col gap-2">
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
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Nom *</Label>
              <Input
                id="name"
                placeholder="Ex : Audit Firewall"
                value={meta.name}
                onChange={(e) => updateMeta("name", e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="version">Version *</Label>
              <Input
                id="version"
                placeholder="Ex : 1.0"
                value={meta.version}
                onChange={(e) => updateMeta("version", e.target.value)}
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Description du référentiel\u2026"
              value={meta.description}
              onChange={(e) => updateMeta("description", e.target.value)}
              className="min-h-[60px]"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="source">Source</Label>
              <Input
                id="source"
                placeholder="Ex : CIS Benchmarks, ANSSI, NIST\u2026"
                value={meta.source}
                onChange={(e) => updateMeta("source", e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">Recommandations sur lesquelles se base ce référentiel</p>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="author">Auteur</Label>
              <Input
                id="author"
                placeholder="Ex : Équipe sécurité, John Doe\u2026"
                value={meta.author}
                onChange={(e) => updateMeta("author", e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">Créateur de ce référentiel</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Label>Moteur</Label>
              <Select value={meta.engine} onValueChange={(v) => updateMeta("engine", v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="manual">Manuel</SelectItem>
                    <SelectItem value="monkey365">Monkey365</SelectItem>
                    <SelectItem value="nmap">Nmap</SelectItem>
                    <SelectItem value="automatic">Automatique</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            {meta.engine !== "manual" && (
              <div className="flex flex-col gap-2">
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
            <Plus data-icon="inline-start" />
            Catégorie
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-4">
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
            <Loader2 className="animate-spin" data-icon="inline-start" />
          ) : (
            <Save data-icon="inline-start" />
          )}
          {isEditMode ? "Enregistrer les modifications" : "Créer le référentiel"}
        </Button>
      </div>

      {/* Confirm back dialog */}
      <AlertDialog open={confirmBack} onOpenChange={setConfirmBack}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle>Quitter l&apos;éditeur ?</AlertDialogTitle>
            <AlertDialogDescription>
              Les modifications non sauvegardées seront perdues.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setConfirmBack(false)}>
              Continuer l&apos;édition
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={onBack}
            >
              Quitter sans sauvegarder
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
          <Layers className="size-4 text-muted-foreground shrink-0" />
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
              className="text-destructive hover:text-destructive size-7 p-0"
              onClick={(e) => {
                e.stopPropagation();
                onRemove();
              }}
            >
              <Trash2 />
            </Button>
          )}
          {expanded ? (
            <ChevronUp className="size-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="size-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t p-4 flex flex-col gap-4">
          {/* Category fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Label>Nom de la catégorie *</Label>
              <Input
                placeholder="Ex : Configuration réseau"
                value={category.name}
                onChange={(e) => onUpdate("name", e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label>Description</Label>
              <Input
                placeholder="Description de la catégorie\u2026"
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
              <Plus data-icon="inline-start" />
              Contrôle
            </Button>
          </div>

          <div className="flex flex-col gap-3">
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
      <CardContent className="pt-4 pb-4 flex flex-col gap-3">
        {/* Row 1: ref_id, title, actions */}
        <div className="flex items-start gap-3">
          <span className="text-xs text-muted-foreground mt-2 shrink-0 w-6 text-center font-mono">
            {ctrlIndex + 1}
          </span>
          <div className="flex-1 grid grid-cols-1 md:grid-cols-[140px_1fr] gap-3">
            <div className="flex flex-col gap-1">
              <Label className="text-[11px]">Réf. *</Label>
              <Input
                placeholder="FW-01"
                value={control.ref_id}
                onChange={(e) => onUpdate("ref_id", e.target.value)}
                className="font-mono text-xs h-8"
              />
            </div>
            <div className="flex flex-col gap-1">
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
              className="size-7 p-0"
              onClick={onDuplicate}
              title="Dupliquer"
            >
              <Copy />
            </Button>
            {canDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="size-7 p-0 text-destructive hover:text-destructive"
                onClick={onRemove}
                title="Supprimer"
              >
                <Trash2 />
              </Button>
            )}
          </div>
        </div>

        {/* Row 2: severity, check_type */}
        <div className="ml-9 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="flex flex-col gap-1">
            <Label className="text-[11px]">Sévérité</Label>
            <Select value={control.severity} onValueChange={(v) => onUpdate("severity", v)}>
              <SelectTrigger className="w-full h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="critical">🔴 Critique</SelectItem>
                  <SelectItem value="high">🟠 Élevée</SelectItem>
                  <SelectItem value="medium">🟡 Moyenne</SelectItem>
                  <SelectItem value="low">🔵 Faible</SelectItem>
                  <SelectItem value="info">⚪ Info</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-[11px]">Type de vérification</Label>
            <Select value={control.check_type} onValueChange={(v) => onUpdate("check_type", v)}>
              <SelectTrigger className="w-full h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="manual">Manuel</SelectItem>
                  <SelectItem value="automatic">Automatique</SelectItem>
                  <SelectItem value="semi-automatic">Semi-auto</SelectItem>
                </SelectGroup>
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
              {showAdvanced ? <ChevronUp data-icon="inline-start" /> : <ChevronDown data-icon="inline-start" />}
              {showAdvanced ? "Masquer détails" : "Plus de détails"}
            </Button>
          </div>
        </div>

        {/* Row 3: advanced fields */}
        {showAdvanced && (
          <div className="ml-9 flex flex-col gap-3 border-t pt-3">
            <div className="flex flex-col gap-1">
              <Label className="text-[11px]">Description</Label>
              <Textarea
                placeholder="Description détaillée du contrôle\u2026"
                value={control.description}
                onChange={(e) => onUpdate("description", e.target.value)}
                className="text-xs min-h-[50px]"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-[11px]">Remédiation</Label>
              <Textarea
                placeholder="Instructions de remédiation\u2026"
                value={control.remediation}
                onChange={(e) => onUpdate("remediation", e.target.value)}
                className="text-xs min-h-[50px]"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="flex flex-col gap-1">
                <Label className="text-[11px]">Règle moteur</Label>
                <Input
                  placeholder="rule_id"
                  value={control.engine_rule_id}
                  onChange={(e) => onUpdate("engine_rule_id", e.target.value)}
                  className="font-mono text-xs h-8"
                />
              </div>
              <div className="flex flex-col gap-1">
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
