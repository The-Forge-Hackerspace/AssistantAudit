"use client";

import { useEffect, useState, useCallback } from "react";
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
} from "lucide-react";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { auditsApi } from "@/services/api";
import { toast } from "sonner";
import type {
  Audit,
  AuditCreate,
  AuditStatus,
  Entreprise,
} from "@/types";
import {
  STATUS_LABELS,
  STATUS_VARIANTS,
  STATUS_ICONS,
} from "../lib/constants";

export interface AuditListViewProps {
  entreprises: Entreprise[];
  entrepriseMap: Record<number, string>;
  initialEntreprise: string;
  onOpenDetail: (a: Audit) => void;
}

export function AuditListView({
  entreprises,
  entrepriseMap,
  initialEntreprise,
  onOpenDetail,
}: AuditListViewProps) {
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
