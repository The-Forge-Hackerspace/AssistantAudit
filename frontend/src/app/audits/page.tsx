"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Plus,
  Pencil,
  Trash2,
  Eye,
  ChevronLeft,
  ChevronRight,
  Search,
  Loader2,
  ClipboardCheck,
  Building2,
  Calendar,
  BarChart3,
  CheckCircle,
  FileText,
  ArrowLeft,
  Target,
  Shield,
  ChevronDown,
  ChevronUp,
  Server,
  Zap,
  AlertCircle,
  CircleDot,
  Minus,
} from "lucide-react";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import {
  auditsApi,
  entreprisesApi,
  campaignsApi,
  assessmentsApi,
  frameworksApi,
  sitesApi,
  equipementsApi,
} from "@/services/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type {
  Audit,
  AuditCreate,
  AuditStatus,
  Entreprise,
  CampaignSummary,
  CampaignStatus,
  Campaign,
  Assessment,
  FrameworkSummary,
  Site,
  Equipement,
  Score,
  ComplianceStatus,
} from "@/types";
import {
  AUDIT_STATUS_LABELS as STATUS_LABELS,
  AUDIT_STATUS_VARIANTS as STATUS_VARIANTS,
  AUDIT_STATUS_ICONS as STATUS_ICONS,
  CAMPAIGN_STATUS_LABELS as CAMPAIGN_LABELS,
  COMPLIANCE_LABELS_SHORT as COMPLIANCE_LABELS,
  COMPLIANCE_COLORS as COMPLIANCE_CLASSES,
  SEVERITY_VARIANTS,
} from "@/lib/constants";

export default function AuditsPage() {
  return (
    <Suspense fallback={<div className="p-6">Chargement…</div>}>
      <AuditsContent />
    </Suspense>
  );
}

function AuditsContent() {
  const searchParams = useSearchParams();
  const initialEntreprise = searchParams.get("entreprise") || "all";

  // ── Global State ──
  const [view, setView] = useState<"list" | "detail">("list");
  const [selectedAudit, setSelectedAudit] = useState<Audit | null>(null);

  // ── Shared Data ──
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [entrepriseMap, setEntrepriseMap] = useState<Record<number, string>>({});

  // Load entreprises once
  useEffect(() => {
    const load = async () => {
      try {
        const res = await entreprisesApi.list(1, 100);
        setEntreprises(res.items);
        const map: Record<number, string> = {};
        res.items.forEach((e) => (map[e.id] = e.nom));
        setEntrepriseMap(map);
      } catch { /* ignore */ }
    };
    load();
  }, []);

  const openDetail = useCallback(async (audit: Audit) => {
    try {
      const detail = await auditsApi.get(audit.id);
      setSelectedAudit(detail);
      setView("detail");
    } catch {
      setSelectedAudit(audit);
      setView("detail");
    }
  }, []);

  const backToList = () => {
    setView("list");
    setSelectedAudit(null);
  };

  if (view === "detail" && selectedAudit) {
    return (
      <AuditDetailView
        audit={selectedAudit}
        entrepriseMap={entrepriseMap}
        onBack={backToList}
        onAuditUpdated={(a) => setSelectedAudit(a)}
      />
    );
  }

  return (
    <AuditListView
      entreprises={entreprises}
      entrepriseMap={entrepriseMap}
      initialEntreprise={initialEntreprise}
      onOpenDetail={openDetail}
    />
  );
}

// ════════════════════════════════════════════════════════
// ── LIST VIEW ──
// ════════════════════════════════════════════════════════

function AuditListView({
  entreprises,
  entrepriseMap,
  initialEntreprise,
  onOpenDetail,
}: {
  entreprises: Entreprise[];
  entrepriseMap: Record<number, string>;
  initialEntreprise: string;
  onOpenDetail: (a: Audit) => void;
}) {
  const [audits, setAudits] = useState<Audit[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");

  const [entrepriseFilter, setEntrepriseFilter] = useState<string>(initialEntreprise);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Create / Edit / Delete dialogs
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selected, setSelected] = useState<Audit | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const [form, setForm] = useState<AuditCreate & { status?: AuditStatus }>({
    nom_projet: "",
    entreprise_id: 0,
    objectifs: "",
    limites: "",
    hypotheses: "",
    risques_initiaux: "",
  });

  const PAGE_SIZE = 10;

  const loadAudits = useCallback(async () => {
    setLoading(true);
    try {
      const entrepriseId = entrepriseFilter !== "all" ? Number(entrepriseFilter) : undefined;
      const res = await auditsApi.list(page, PAGE_SIZE, entrepriseId);
      setAudits(res.items);
      setPages(res.pages);
      setTotal(res.total);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [page, entrepriseFilter]);

  useEffect(() => { loadAudits(); }, [loadAudits]);

  useEffect(() => { setPage(1); }, [entrepriseFilter, statusFilter]);

  const filtered = audits.filter((a) => {
    if (statusFilter !== "all" && a.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        a.nom_projet.toLowerCase().includes(q) ||
        (entrepriseMap[a.entreprise_id] || "").toLowerCase().includes(q) ||
        (a.objectifs || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const resetForm = () => {
    setForm({ nom_projet: "", entreprise_id: 0, objectifs: "", limites: "", hypotheses: "", risques_initiaux: "" });
    setFormError("");
  };

  const openCreate = () => {
    resetForm();
    if (entrepriseFilter !== "all") setForm((f) => ({ ...f, entreprise_id: Number(entrepriseFilter) }));
    setCreateOpen(true);
  };

  const openEdit = (a: Audit) => {
    setSelected(a);
    setForm({
      nom_projet: a.nom_projet,
      entreprise_id: a.entreprise_id,
      objectifs: a.objectifs || "",
      limites: a.limites || "",
      hypotheses: a.hypotheses || "",
      risques_initiaux: a.risques_initiaux || "",
      status: a.status,
    });
    setFormError("");
    setEditOpen(true);
  };

  const openDelete = (a: Audit) => {
    setSelected(a);
    setFormError("");
    setDeleteOpen(true);
  };

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
    } catch { return "—"; }
  };

  const handleCreate = async () => {
    if (!form.nom_projet.trim()) { setFormError("Le nom du projet est obligatoire"); return; }
    if (!form.entreprise_id) { setFormError("Veuillez sélectionner une entreprise"); return; }
    setSaving(true); setFormError("");
    try {
      const { status, ...createPayload } = form;
      void status;
      await auditsApi.create(createPayload);
      setCreateOpen(false); resetForm(); loadAudits();
      toast.success("Projet d'audit créé avec succès");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
      toast.error("Erreur lors de la création");
    } finally { setSaving(false); }
  };

  const handleUpdate = async () => {
    if (!selected || !form.nom_projet.trim()) { setFormError("Le nom du projet est obligatoire"); return; }
    setSaving(true); setFormError("");
    try {
      await auditsApi.update(selected.id, {
        nom_projet: form.nom_projet,
        objectifs: form.objectifs || undefined,
        limites: form.limites || undefined,
        hypotheses: form.hypotheses || undefined,
        risques_initiaux: form.risques_initiaux || undefined,
        status: form.status,
      });
      setEditOpen(false); resetForm(); loadAudits();
      toast.success("Projet d'audit mis à jour");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la mise à jour");
      toast.error("Erreur lors de la mise à jour");
    } finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!selected) return;
    setSaving(true); setFormError("");
    try {
      await auditsApi.delete(selected.id);
      setDeleteOpen(false); loadAudits();
      toast.success("Projet d'audit supprimé");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la suppression");
      toast.error("Erreur lors de la suppression");
    } finally { setSaving(false); }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projets d&apos;audit</h1>
          <p className="text-muted-foreground">{total} projet{total !== 1 ? "s" : ""} d&apos;audit</p>
        </div>
        <Button onClick={openCreate}>
          <Plus data-icon="inline-start" />
          Nouveau projet
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input className="pl-9" placeholder="Rechercher par nom, entreprise ou objectifs..." value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <Select value={entrepriseFilter} onValueChange={setEntrepriseFilter}>
              <SelectTrigger className="w-[220px]"><SelectValue placeholder="Filtrer par entreprise" /></SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="all">Toutes les entreprises</SelectItem>
                  {entreprises.map((e) => (<SelectItem key={e.id} value={String(e.id)}>{e.nom}</SelectItem>))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[170px]"><SelectValue placeholder="Statut" /></SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="NOUVEAU">Nouveau</SelectItem>
                  <SelectItem value="EN_COURS">En cours</SelectItem>
                  <SelectItem value="TERMINE">Terminé</SelectItem>
                  <SelectItem value="ARCHIVE">Archivé</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="size-8 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <ClipboardCheck className="size-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Aucun projet d&apos;audit</p>
            <p className="text-sm mt-1">
              {audits.length === 0 ? "Créez votre premier projet d'audit pour commencer" : "Essayez de modifier vos critères de recherche"}
            </p>
          </div>
        ) : (
          <div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Projet</TableHead>
                  <TableHead>Entreprise</TableHead>
                  <TableHead>Date de début</TableHead>
                  <TableHead>Campagnes</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((audit) => {
                  const StatusIcon = STATUS_ICONS[audit.status];
                  return (
                    <TableRow key={audit.id} className="cursor-pointer" onClick={() => onOpenDetail(audit)}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <ClipboardCheck className="size-4 text-muted-foreground" />
                          <div>
                            <p className="font-medium">{audit.nom_projet}</p>
                            {audit.objectifs && <p className="text-xs text-muted-foreground line-clamp-1 max-w-xs">{audit.objectifs}</p>}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline"><Building2 className="size-3 mr-1" />{entrepriseMap[audit.entreprise_id] || `#${audit.entreprise_id}`}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm"><Calendar className="size-3 text-muted-foreground" />{formatDate(audit.date_debut)}</div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm"><BarChart3 className="size-3 text-muted-foreground" />{audit.total_campaigns ?? 0}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANTS[audit.status]}><StatusIcon className="size-3 mr-1" />{STATUS_LABELS[audit.status]}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                          <Button size="icon" variant="ghost" onClick={() => onOpenDetail(audit)}><Eye /></Button>
                          <Button size="icon" variant="ghost" onClick={() => openEdit(audit)}><Pencil /></Button>
                          <Button size="icon" variant="ghost" onClick={() => openDelete(audit)}><Trash2 className="text-destructive" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>

            <CardFooter className="flex items-center justify-between border-t">
              <p className="text-sm text-muted-foreground">Page {page} sur {pages} — {total} résultat{total !== 1 ? "s" : ""}</p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft data-icon="inline-start" />Précédent</Button>
                <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Suivant<ChevronRight data-icon="inline-end" /></Button>
              </div>
            </CardFooter>
          </div>
        )}
      </Card>

      {/* Dialog: Créer */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nouveau projet d&apos;audit</DialogTitle>
            <DialogDescription>Créez un projet d&apos;audit pour une entreprise</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="create-nom">Nom du projet *</Label>
                <Input id="create-nom" value={form.nom_projet} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, nom_projet: value })); }} placeholder="ex: Audit Infra Q1 2026" />
              </div>
              <div className="flex flex-col gap-2">
                <Label>Entreprise *</Label>
                <Select value={form.entreprise_id ? String(form.entreprise_id) : ""} onValueChange={(v) => setForm(prev => ({ ...prev, entreprise_id: Number(v) }))}>
                  <SelectTrigger><SelectValue placeholder="Sélectionner une entreprise" /></SelectTrigger>
                  <SelectContent><SelectGroup>{entreprises.map((e) => (<SelectItem key={e.id} value={String(e.id)}>{e.nom}</SelectItem>))}</SelectGroup></SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="create-objectifs">Objectifs de l&apos;audit</Label>
              <Textarea id="create-objectifs" value={form.objectifs || ""} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, objectifs: value })); }} placeholder="Décrire les objectifs principaux de cet audit..." rows={3} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="create-limites">Limites / Périmètre</Label>
              <Textarea id="create-limites" value={form.limites || ""} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, limites: value })); }} placeholder="Définir le périmètre et les limites de l'audit..." rows={2} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="create-hypotheses">Hypothèses</Label>
                <Textarea id="create-hypotheses" value={form.hypotheses || ""} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, hypotheses: value })); }} placeholder="Hypothèses de travail..." rows={2} />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="create-risques">Risques initiaux identifiés</Label>
                <Textarea id="create-risques" value={form.risques_initiaux || ""} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, risques_initiaux: value })); }} placeholder="Risques identifiés en amont..." rows={2} />
              </div>
            </div>
          </div>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Annuler</Button>
            <Button onClick={handleCreate} disabled={saving}>{saving && <Loader2 className="animate-spin" data-icon="inline-start" />}Créer le projet</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Modifier */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Modifier le projet d&apos;audit</DialogTitle>
            <DialogDescription>Modifiez les informations de &laquo; {selected?.nom_projet} &raquo;</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="edit-nom">Nom du projet *</Label>
                <Input id="edit-nom" value={form.nom_projet} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, nom_projet: value })); }} />
              </div>
              <div className="flex flex-col gap-2">
                <Label>Statut</Label>
                <Select value={form.status || "NOUVEAU"} onValueChange={(v) => setForm(prev => ({ ...prev, status: v as AuditStatus }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="NOUVEAU">Nouveau</SelectItem>
                      <SelectItem value="EN_COURS">En cours</SelectItem>
                      <SelectItem value="TERMINE">Terminé</SelectItem>
                      <SelectItem value="ARCHIVE">Archivé</SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="edit-objectifs">Objectifs</Label>
              <Textarea id="edit-objectifs" value={form.objectifs || ""} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, objectifs: value })); }} rows={3} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="edit-limites">Limites / Périmètre</Label>
              <Textarea id="edit-limites" value={form.limites || ""} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, limites: value })); }} rows={2} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="edit-hypotheses">Hypothèses</Label>
                <Textarea id="edit-hypotheses" value={form.hypotheses || ""} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, hypotheses: value })); }} rows={2} />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="edit-risques">Risques initiaux</Label>
                <Textarea id="edit-risques" value={form.risques_initiaux || ""} onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, risques_initiaux: value })); }} rows={2} />
              </div>
            </div>
          </div>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>Annuler</Button>
            <Button onClick={handleUpdate} disabled={saving}>{saving && <Loader2 className="animate-spin" data-icon="inline-start" />}Enregistrer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* AlertDialog: Supprimer */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer le projet d&apos;audit &laquo; <strong>{selected?.nom_projet}</strong> &raquo; ?
              Cette action est irréversible et supprimera toutes les campagnes et évaluations associées.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={handleDelete} disabled={saving}>{saving && <Loader2 className="animate-spin" data-icon="inline-start" />}Supprimer</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ════════════════════════════════════════════════════════
// ── DETAIL VIEW ──
// ════════════════════════════════════════════════════════

function AuditDetailView({
  audit,
  entrepriseMap,
  onBack,
  onAuditUpdated,
}: {
  audit: Audit;
  entrepriseMap: Record<number, string>;
  onBack: () => void;
  onAuditUpdated: (a: Audit) => void;
}) {
  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
    } catch { return "—"; }
  };

  const handleStatusChange = async (newStatus: AuditStatus) => {
    try {
      const updated = await auditsApi.update(audit.id, { status: newStatus });
      onAuditUpdated(updated);
    } catch {
      toast.error("Erreur lors du changement de statut");
    }
  };

  const StatusIcon = STATUS_ICONS[audit.status];

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <ClipboardCheck className="size-6" />
            {audit.nom_projet}
          </h1>
          <p className="text-muted-foreground">
            {entrepriseMap[audit.entreprise_id] || `Entreprise #${audit.entreprise_id}`}
          </p>
        </div>
        <Badge variant={STATUS_VARIANTS[audit.status]} className="text-sm px-3 py-1">
          <StatusIcon className="size-4 mr-1" />
          {STATUS_LABELS[audit.status]}
        </Badge>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs font-medium text-muted-foreground">Entreprise</p>
            <p className="text-sm font-medium mt-1 flex items-center gap-1">
              <Building2 className="h-3.5 w-3.5" />
              {entrepriseMap[audit.entreprise_id] || `#${audit.entreprise_id}`}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs font-medium text-muted-foreground">Date de début</p>
            <p className="text-sm font-medium mt-1 flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {formatDate(audit.date_debut)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs font-medium text-muted-foreground">Campagnes</p>
            <p className="text-sm font-medium mt-1 flex items-center gap-1">
              <BarChart3 className="h-3.5 w-3.5" />
              {audit.total_campaigns ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs font-medium text-muted-foreground">Changer le statut</p>
            <Select value={audit.status} onValueChange={(v) => handleStatusChange(v as AuditStatus)}>
              <SelectTrigger className="h-7 mt-1 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="NOUVEAU">Nouveau</SelectItem>
                  <SelectItem value="EN_COURS">En cours</SelectItem>
                  <SelectItem value="TERMINE">Terminé</SelectItem>
                  <SelectItem value="ARCHIVE">Archivé</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      </div>

      {/* Documents */}
      {(audit.lettre_mission_path || audit.contrat_path || audit.planning_path) && (
        <div className="flex gap-2 flex-wrap">
          {audit.lettre_mission_path && <Badge variant="secondary"><FileText className="size-3 mr-1" />Lettre de mission</Badge>}
          {audit.contrat_path && <Badge variant="secondary"><FileText className="size-3 mr-1" />Contrat</Badge>}
          {audit.planning_path && <Badge variant="secondary"><FileText className="size-3 mr-1" />Planning</Badge>}
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="campagnes">
        <TabsList>
          <TabsTrigger value="contexte">Contexte</TabsTrigger>
          <TabsTrigger value="campagnes">Campagnes</TabsTrigger>
        </TabsList>

        <TabsContent value="contexte">
          <Card>
            <CardContent className="pt-6 flex flex-col gap-6">
              {audit.objectifs && (
                <div>
                  <p className="text-sm font-semibold text-muted-foreground mb-1">Objectifs</p>
                  <p className="text-sm whitespace-pre-wrap">{audit.objectifs}</p>
                </div>
              )}
              {audit.limites && (
                <div>
                  <p className="text-sm font-semibold text-muted-foreground mb-1">Limites / Périmètre</p>
                  <p className="text-sm whitespace-pre-wrap">{audit.limites}</p>
                </div>
              )}
              {(audit.hypotheses || audit.risques_initiaux) && (
                <div className="grid grid-cols-2 gap-6">
                  {audit.hypotheses && (
                    <div>
                      <p className="text-sm font-semibold text-muted-foreground mb-1">Hypothèses</p>
                      <p className="text-sm whitespace-pre-wrap">{audit.hypotheses}</p>
                    </div>
                  )}
                  {audit.risques_initiaux && (
                    <div>
                      <p className="text-sm font-semibold text-muted-foreground mb-1">Risques initiaux</p>
                      <p className="text-sm whitespace-pre-wrap">{audit.risques_initiaux}</p>
                    </div>
                  )}
                </div>
              )}
              {!audit.objectifs && !audit.limites && !audit.hypotheses && !audit.risques_initiaux && (
                <p className="text-sm text-muted-foreground text-center py-6">
                  Aucune information de contexte renseignée.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="campagnes">
          <CampaignsTab auditId={audit.id} entrepriseId={audit.entreprise_id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ════════════════════════════════════════════════════════
// ── CAMPAIGNS TAB ──
// ════════════════════════════════════════════════════════

function CampaignsTab({ auditId, entrepriseId }: { auditId: number; entrepriseId: number }) {
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [campaignName, setCampaignName] = useState("");
  const [campaignDesc, setCampaignDesc] = useState("");

  // Expanded campaign detail
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await campaignsApi.list(1, 100, auditId);
      setCampaigns(res.items);
    } catch {
      toast.error("Erreur lors du chargement des campagnes");
    } finally {
      setLoading(false);
    }
  }, [auditId]);

  useEffect(() => { loadCampaigns(); }, [loadCampaigns]);

  const handleCreate = async () => {
    if (!campaignName.trim()) { setFormError("Le nom est obligatoire"); return; }
    setSaving(true); setFormError("");
    try {
      await campaignsApi.create({ name: campaignName, description: campaignDesc || undefined, audit_id: auditId });
      setCreateOpen(false);
      setCampaignName(""); setCampaignDesc("");
      loadCampaigns();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
    } finally { setSaving(false); }
  };

  const handleStatusChange = async (id: number, newStatus: CampaignStatus) => {
    try {
      // Utiliser les endpoints dédiés qui gèrent aussi le statut des équipements
      if (newStatus === "in_progress") {
        await campaignsApi.start(id);
      } else if (newStatus === "completed") {
        await campaignsApi.complete(id);
      } else {
        await campaignsApi.update(id, { status: newStatus });
      }
      loadCampaigns();
    } catch {
      toast.error("Erreur lors du changement de statut de la campagne");
    }
  };

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
    } catch { return "—"; }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {campaigns.length} campagne{campaigns.length !== 1 ? "s" : ""} d&apos;évaluation
        </p>
        <Button size="sm" onClick={() => { setFormError(""); setCampaignName(""); setCampaignDesc(""); setCreateOpen(true); }}>
          <Plus data-icon="inline-start" />
          Nouvelle campagne
        </Button>
      </div>

      {/* Campaign list */}
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : campaigns.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">
            <Target className="size-10 mx-auto mb-3 opacity-50" />
            <p className="font-medium">Aucune campagne</p>
            <p className="text-sm mt-1">Créez une campagne pour commencer les évaluations</p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {campaigns.map((c) => (
            <Card key={c.id} className="overflow-hidden">
              <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/30 transition-colors"
                onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <Target className="size-4 text-muted-foreground shrink-0" />
                  <div className="min-w-0">
                    <p className="font-medium truncate">{c.name}</p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                      <span>{formatDate(c.created_at)}</span>
                      <span>{c.total_assessments} évaluation{c.total_assessments !== 1 ? "s" : ""}</span>
                      {c.compliance_score !== null && (
                        <span className="font-medium text-foreground">{c.compliance_score}% conformité</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <div onClick={(e) => e.stopPropagation()}>
                    <Select value={c.status} onValueChange={(v) => handleStatusChange(c.id, v as CampaignStatus)}>
                      <SelectTrigger className="h-7 w-[130px] text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {(Object.keys(CAMPAIGN_LABELS) as CampaignStatus[]).map((s) => (
                            <SelectItem key={s} value={s}>{CAMPAIGN_LABELS[s]}</SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>

                  {expandedId === c.id ? (
                    <ChevronUp className="size-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="size-4 text-muted-foreground" />
                  )}
                </div>
              </div>

              {/* Expanded: campaign details with assessments */}
              {expandedId === c.id && (
                <div className="border-t">
                  <CampaignDetail
                    campaignId={c.id}
                    entrepriseId={entrepriseId}
                    onAssessmentChanged={loadCampaigns}
                  />
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Dialog: Create campaign */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouvelle campagne d&apos;évaluation</DialogTitle>
            <DialogDescription>
              Créez une campagne pour regrouper les évaluations de cet audit
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="campaign-name">Nom de la campagne *</Label>
              <Input
                id="campaign-name"
                value={campaignName}
                onChange={(e) => setCampaignName(e.target.value)}
                placeholder="ex: Évaluation réseau Q1 2026"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="campaign-desc">Description</Label>
              <Textarea
                id="campaign-desc"
                value={campaignDesc}
                onChange={(e) => setCampaignDesc(e.target.value)}
                placeholder="Description de la campagne..."
                rows={3}
              />
            </div>
          </div>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Annuler</Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Créer la campagne
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ════════════════════════════════════════════════════════
// ── CAMPAIGN DETAIL (expanded) ──
// ════════════════════════════════════════════════════════

function CampaignDetail({
  campaignId,
  entrepriseId,
  onAssessmentChanged,
}: {
  campaignId: number;
  entrepriseId: number;
  onAssessmentChanged: () => void;
}) {
  const router = useRouter();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [score, setScore] = useState<Score | null>(null);
  const [loading, setLoading] = useState(true);
  const [createAssessmentOpen, setCreateAssessmentOpen] = useState(false);

  // Assessment creation form
  const [frameworks, setFrameworks] = useState<FrameworkSummary[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [equipements, setEquipements] = useState<Equipement[]>([]);
  const [selectedSite, setSelectedSite] = useState<string>("");
  const [selectedEquipement, setSelectedEquipement] = useState<string>("");
  const [selectedFramework, setSelectedFramework] = useState<string>("");
  const [assessmentNotes, setAssessmentNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Expanded assessment
  const [expandedAssessmentId, setExpandedAssessmentId] = useState<number | null>(null);

  const loadCampaign = useCallback(async () => {
    setLoading(true);
    try {
      const [c, s] = await Promise.all([
        campaignsApi.get(campaignId),
        campaignsApi.score(campaignId).catch(() => null),
      ]);
      setCampaign(c);
      setScore(s);
    } catch {
      toast.error("Erreur lors du chargement de la campagne");
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => { loadCampaign(); }, [loadCampaign]);

  const openCreateAssessment = async () => {
    setFormError("");
    setSelectedSite(""); setSelectedEquipement(""); setSelectedFramework(""); setAssessmentNotes("");
    setEquipements([]);

    try {
      const [fwRes, siteRes] = await Promise.all([
        frameworksApi.list(1, 100, true),
        sitesApi.list(1, 100, entrepriseId),
      ]);
      setFrameworks(fwRes.items);
      setSites(siteRes.items);
    } catch { /* ignore */ }

    setCreateAssessmentOpen(true);
  };

  const handleSiteChange = async (siteId: string) => {
    setSelectedSite(siteId);
    setSelectedEquipement("");
    if (siteId) {
      try {
        const res = await equipementsApi.list(1, 100, { site_id: Number(siteId) });
        setEquipements(res.items);
      } catch { setEquipements([]); }
    } else {
      setEquipements([]);
    }
  };

  const handleCreateAssessment = async () => {
    if (!selectedEquipement) { setFormError("Sélectionnez un équipement"); return; }
    if (!selectedFramework) { setFormError("Sélectionnez un référentiel"); return; }
    setSaving(true); setFormError("");
    try {
      await assessmentsApi.create(campaignId, {
        equipement_id: Number(selectedEquipement),
        framework_id: Number(selectedFramework),
        notes: assessmentNotes || undefined,
      });
      setCreateAssessmentOpen(false);
      loadCampaign();
      onAssessmentChanged();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
    } finally { setSaving(false); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!campaign) {
    return <div className="p-4 text-sm text-muted-foreground">Impossible de charger la campagne.</div>;
  }

  return (
    <div className="p-4 flex flex-col gap-4">
      {/* Score bar */}
      {score && score.total_controls > 0 && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Score de conformité</span>
            <span className="font-bold text-lg">{score.compliance_score}%</span>
          </div>
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

      {campaign.description && (
        <p className="text-sm text-muted-foreground">{campaign.description}</p>
      )}

      <Separator />

      {/* Assessments header */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          {campaign.assessments.length} évaluation{campaign.assessments.length !== 1 ? "s" : ""}
        </p>
        <Button size="sm" variant="outline" onClick={openCreateAssessment}>
          <Plus data-icon="inline-start" />
          Ajouter une évaluation
        </Button>
      </div>

      {/* Assessment list */}
      {campaign.assessments.length === 0 ? (
        <div className="text-center py-6 text-muted-foreground">
          <Shield className="size-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Aucune évaluation dans cette campagne</p>
          <p className="text-xs mt-1">Ajoutez une évaluation pour associer un équipement à un référentiel</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {campaign.assessments.map((assessment) => (
            <div key={assessment.id} className="border rounded-lg overflow-hidden">
              <div
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/30 transition-colors"
                onClick={() => setExpandedAssessmentId(expandedAssessmentId === assessment.id ? null : assessment.id)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Server className="size-4 text-muted-foreground shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">
                      {assessment.equipement_hostname || assessment.equipement_ip || `Équipement #${assessment.equipement_id}`}
                      {assessment.equipement_ip && assessment.equipement_hostname && (
                        <span className="text-xs text-muted-foreground ml-2 font-mono">{assessment.equipement_ip}</span>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      <Shield className="size-3 inline mr-1" />
                      {assessment.framework_name || `Framework #${assessment.framework_id}`}
                      {assessment.compliance_score !== null && (
                        <span className="ml-2 font-medium text-foreground">{assessment.compliance_score}%</span>
                      )}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {assessment.compliance_score !== null && (
                    <div className="w-16">
                      <Progress value={assessment.compliance_score} className="h-1.5" />
                    </div>
                  )}
                  <Badge variant="outline" className="text-xs">
                    {assessment.results.length} contrôles
                  </Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(`/audits/evaluation?assessmentId=${assessment.id}`);
                    }}
                  >
                    <ClipboardCheck data-icon="inline-start" />
                    Évaluer
                  </Button>
                  {expandedAssessmentId === assessment.id ? (
                    <ChevronUp className="size-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="size-4 text-muted-foreground" />
                  )}
                </div>
              </div>

              {/* Expanded: control results */}
              {expandedAssessmentId === assessment.id && (
                <AssessmentControlResults
                  assessmentId={assessment.id}
                  results={assessment.results}
                  onResultUpdated={loadCampaign}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Dialog: Create assessment */}
      <Dialog open={createAssessmentOpen} onOpenChange={setCreateAssessmentOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Nouvelle évaluation</DialogTitle>
            <DialogDescription>
              Associez un équipement à un référentiel pour créer les contrôles à évaluer
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label>Site *</Label>
              <Select value={selectedSite} onValueChange={handleSiteChange}>
                <SelectTrigger><SelectValue placeholder="Sélectionner un site" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {sites.map((s) => (<SelectItem key={s.id} value={String(s.id)}>{s.nom}</SelectItem>))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Équipement *</Label>
              <Select value={selectedEquipement} onValueChange={setSelectedEquipement} disabled={!selectedSite}>
                <SelectTrigger><SelectValue placeholder={selectedSite ? "Sélectionner un équipement" : "Sélectionnez d'abord un site"} /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {equipements.map((eq) => (
                      <SelectItem key={eq.id} value={String(eq.id)}>
                        <span className="font-mono text-xs mr-2">{eq.ip_address}</span>
                        {eq.hostname || eq.type_equipement}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Référentiel *</Label>
              <Select value={selectedFramework} onValueChange={setSelectedFramework}>
                <SelectTrigger><SelectValue placeholder="Sélectionner un référentiel" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {frameworks.map((fw) => (
                      <SelectItem key={fw.id} value={String(fw.id)}>
                        {fw.name} <span className="text-xs text-muted-foreground ml-1">v{fw.version} · {fw.total_controls} contrôles</span>
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="assessment-notes">Notes</Label>
              <Textarea
                id="assessment-notes"
                value={assessmentNotes}
                onChange={(e) => setAssessmentNotes(e.target.value)}
                placeholder="Notes pour cette évaluation..."
                rows={2}
              />
            </div>
          </div>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateAssessmentOpen(false)}>Annuler</Button>
            <Button onClick={handleCreateAssessment} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Créer l&apos;évaluation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ════════════════════════════════════════════════════════
// ── ASSESSMENT CONTROL RESULTS ──
// ════════════════════════════════════════════════════════

function AssessmentControlResults({
  assessmentId,
  results,
  onResultUpdated,
}: {
  assessmentId: number;
  results: Assessment["results"];
  onResultUpdated: () => void;
}) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{
    status: ComplianceStatus;
    evidence: string;
    comment: string;
    remediation_note: string;
  }>({ status: "not_assessed", evidence: "", comment: "", remediation_note: "" });
  const [saving, setSaving] = useState(false);

  // Suppress unused variable warning
  void assessmentId;

  const openEdit = (r: Assessment["results"][0]) => {
    setEditingId(r.id);
    setEditForm({
      status: r.status,
      evidence: r.evidence || "",
      comment: r.comment || "",
      remediation_note: r.remediation_note || "",
    });
  };

  const handleSave = async () => {
    if (editingId === null) return;
    setSaving(true);
    try {
      await assessmentsApi.updateResult(editingId, {
        status: editForm.status,
        evidence: editForm.evidence || undefined,
        comment: editForm.comment || undefined,
        remediation_note: editForm.remediation_note || undefined,
      });
      setEditingId(null);
      onResultUpdated();
    } catch {
      toast.error("Erreur lors de la sauvegarde de l'évaluation");
    } finally {
      setSaving(false);
    }
  };

  const statusIcon = (s: ComplianceStatus) => {
    switch (s) {
      case "compliant": return <CheckCircle className="size-4 text-green-600" />;
      case "non_compliant": return <AlertCircle className="size-4 text-red-600" />;
      case "partially_compliant": return <CircleDot className="size-4 text-yellow-600" />;
      case "not_applicable": return <Minus className="size-4 text-gray-400" />;
      default: return <CircleDot className="size-4 text-gray-300" />;
    }
  };

  if (results.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground text-center border-t">
        Aucun contrôle à évaluer.
      </div>
    );
  }

  return (
    <div className="border-t">
      <div className="max-h-[400px] overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12"></TableHead>
              <TableHead className="w-[100px]">Réf.</TableHead>
              <TableHead>Contrôle</TableHead>
              <TableHead className="w-[90px]">Sévérité</TableHead>
              <TableHead className="w-[130px]">Statut</TableHead>
              <TableHead className="w-[80px] text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{statusIcon(r.status)}</TableCell>
                <TableCell>
                  <code className="text-xs bg-muted px-1 py-0.5 rounded">{r.control_ref_id || `C${r.control_id}`}</code>
                </TableCell>
                <TableCell>
                  <p className="text-sm truncate max-w-xs">{r.control_title || `Contrôle #${r.control_id}`}</p>
                  {r.is_auto_assessed && (
                    <Badge variant="outline" className="text-[10px] px-1 py-0 mt-0.5">
                      <Zap className="h-2.5 w-2.5 mr-0.5" />auto
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  {r.control_severity && (
                    <Badge variant={SEVERITY_VARIANTS[r.control_severity] || "outline"} className="text-xs">
                      {r.control_severity}
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold", COMPLIANCE_CLASSES[r.status])}>
                    {COMPLIANCE_LABELS[r.status]}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openEdit(r)}>
                    <Pencil />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Edit control result dialog */}
      <Dialog open={editingId !== null} onOpenChange={(open) => { if (!open) setEditingId(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Évaluer le contrôle</DialogTitle>
            <DialogDescription>
              {results.find((r) => r.id === editingId)?.control_title || "Contrôle"}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label>Statut de conformité *</Label>
              <Select value={editForm.status} onValueChange={(v) => setEditForm(prev => ({ ...prev, status: v as ComplianceStatus }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="not_assessed">Non évalué</SelectItem>
                    <SelectItem value="compliant">Conforme</SelectItem>
                    <SelectItem value="non_compliant">Non conforme</SelectItem>
                    <SelectItem value="partially_compliant">Partiellement conforme</SelectItem>
                    <SelectItem value="not_applicable">Non applicable</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="result-evidence">Preuve / Évidence</Label>
              <Textarea
                id="result-evidence"
                value={editForm.evidence}
                onChange={(e) => { const value = e.target.value; setEditForm(prev => ({ ...prev, evidence: value })); }}
                placeholder="Captures d'écran, commandes exécutées, résultats..."
                rows={3}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="result-comment">Commentaire</Label>
              <Textarea
                id="result-comment"
                value={editForm.comment}
                onChange={(e) => { const value = e.target.value; setEditForm(prev => ({ ...prev, comment: value })); }}
                placeholder="Observations de l'auditeur..."
                rows={2}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="result-remediation">Note de remédiation</Label>
              <Textarea
                id="result-remediation"
                value={editForm.remediation_note}
                onChange={(e) => { const value = e.target.value; setEditForm(prev => ({ ...prev, remediation_note: value })); }}
                placeholder="Actions recommandées pour la mise en conformité..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingId(null)}>Annuler</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Sauvegarder
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
