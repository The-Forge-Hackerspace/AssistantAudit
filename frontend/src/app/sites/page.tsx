"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  MapPin,
  Plus,
  Search,
  Pencil,
  Trash2,
  Eye,
  Server,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Building2,
  Filter,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { sitesApi, entreprisesApi } from "@/services/api";
import type { Site, SiteCreate, Entreprise } from "@/types";

export default function SitesPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    }>
      <SitesContent />
    </Suspense>
  );
}

function SitesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialEntrepriseFilter = searchParams.get("entreprise");

  // List state
  const [sites, setSites] = useState<Site[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  // Filter state
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [entrepriseFilter, setEntrepriseFilter] = useState<string>(
    initialEntrepriseFilter || "all"
  );
  const [entrepriseMap, setEntrepriseMap] = useState<Record<number, string>>({});

  // Dialog state
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selected, setSelected] = useState<Site | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Form state
  const [form, setForm] = useState<SiteCreate>({
    nom: "",
    description: "",
    adresse: "",
    entreprise_id: 0,
  });

  const PAGE_SIZE = 10;

  // Load entreprises for filter & form dropdown
  useEffect(() => {
    async function loadEntreprises() {
      try {
        const res = await entreprisesApi.list(1, 100);
        setEntreprises(res.items);
        const map: Record<number, string> = {};
        res.items.forEach((e) => {
          map[e.id] = e.nom;
        });
        setEntrepriseMap(map);
      } catch (error) {
        console.error("Erreur chargement entreprises:", error);
      }
    }
    loadEntreprises();
  }, []);

  const loadSites = useCallback(async () => {
    setLoading(true);
    try {
      const entId = entrepriseFilter !== "all" ? Number(entrepriseFilter) : undefined;
      const res = await sitesApi.list(page, PAGE_SIZE, entId);
      setSites(res.items);
      setTotal(res.total);
      setPages(res.pages);
    } catch (error) {
      console.error("Erreur chargement sites:", error);
    } finally {
      setLoading(false);
    }
  }, [page, entrepriseFilter]);

  useEffect(() => {
    loadSites();
  }, [loadSites]);

  // Reset page when filter changes
  useEffect(() => {
    setPage(1);
  }, [entrepriseFilter]);

  // ── Filtered list (client-side search on loaded page) ──
  const filtered = search
    ? sites.filter(
        (s) =>
          s.nom.toLowerCase().includes(search.toLowerCase()) ||
          (s.adresse || "").toLowerCase().includes(search.toLowerCase()) ||
          (entrepriseMap[s.entreprise_id] || "").toLowerCase().includes(search.toLowerCase())
      )
    : sites;

  // ── Helpers ──
  const resetForm = () => {
    setForm({ nom: "", description: "", adresse: "", entreprise_id: 0 });
    setFormError("");
  };

  const openCreate = () => {
    resetForm();
    // Pre-select filtered entreprise if one is active
    if (entrepriseFilter !== "all") {
      setForm((f) => ({ ...f, entreprise_id: Number(entrepriseFilter) }));
    }
    setCreateOpen(true);
  };

  const openEdit = (s: Site) => {
    setSelected(s);
    setForm({ nom: s.nom, description: s.description || "", adresse: s.adresse || "", entreprise_id: s.entreprise_id });
    setFormError("");
    setEditOpen(true);
  };

  const openDelete = (s: Site) => {
    setSelected(s);
    setFormError("");
    setDeleteOpen(true);
  };

  const openDetail = (s: Site) => {
    setSelected(s);
    setDetailOpen(true);
  };

  // ── CRUD ──
  const handleCreate = async () => {
    if (!form.nom.trim()) {
      setFormError("Le nom du site est obligatoire");
      return;
    }
    if (!form.entreprise_id) {
      setFormError("Veuillez sélectionner une entreprise");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await sitesApi.create(form);
      setCreateOpen(false);
      resetForm();
      loadSites();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!selected || !form.nom.trim()) {
      setFormError("Le nom du site est obligatoire");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await sitesApi.update(selected.id, {
        nom: form.nom,
        description: form.description || undefined,
        adresse: form.adresse || undefined,
      });
      setEditOpen(false);
      resetForm();
      loadSites();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la mise à jour");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    setSaving(true);
    setFormError("");
    try {
      await sitesApi.delete(selected.id);
      setDeleteOpen(false);
      setSelected(null);
      loadSites();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la suppression");
    } finally {
      setSaving(false);
    }
  };

  // ── Render ──
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <MapPin className="h-6 w-6" />
            Sites
          </h1>
          <p className="text-muted-foreground">
            Gérez les emplacements physiques des entreprises
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-2" />
          Nouveau site
        </Button>
      </div>

      {/* Search + filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher par nom, adresse ou entreprise..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={entrepriseFilter} onValueChange={setEntrepriseFilter}>
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

        <Badge variant="secondary" className="text-sm">
          {total} site{total > 1 ? "s" : ""}
        </Badge>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <MapPin className="h-12 w-12 mb-4 opacity-30" />
              <p className="text-lg font-medium">Aucun site</p>
              <p className="text-sm">
                {search || entrepriseFilter !== "all"
                  ? "Aucun résultat pour ces critères"
                  : "Commencez par ajouter un site"}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Entreprise</TableHead>
                  <TableHead>Adresse</TableHead>
                  <TableHead>Équipements</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((site) => (
                  <TableRow
                    key={site.id}
                    className="cursor-pointer"
                    onClick={() => openDetail(site)}
                  >
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                        {site.nom}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-normal">
                        <Building2 className="h-3 w-3 mr-1" />
                        {entrepriseMap[site.entreprise_id] || `#${site.entreprise_id}`}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {site.adresse || "—"}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Server className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-sm">{site.equipement_count}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div
                        className="flex items-center justify-end gap-1"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => openDetail(site)}
                          title="Voir le détail"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => openEdit(site)}
                          title="Modifier"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:text-destructive"
                          onClick={() => openDelete(site)}
                          title="Supprimer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between border-t px-4 py-3">
            <p className="text-sm text-muted-foreground">
              Page {page} sur {pages} — {total} résultat{total > 1 ? "s" : ""}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Précédent
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* ── Dialog: Créer ── */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Nouveau site</DialogTitle>
            <DialogDescription>
              Ajoutez un emplacement physique à une entreprise
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Entreprise *</Label>
              <Select
                value={form.entreprise_id ? String(form.entreprise_id) : ""}
                onValueChange={(v) => setForm({ ...form, entreprise_id: Number(v) })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner une entreprise" />
                </SelectTrigger>
                <SelectContent>
                  {entreprises.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-site-nom">Nom du site *</Label>
              <Input
                id="create-site-nom"
                value={form.nom}
                onChange={(e) => setForm({ ...form, nom: e.target.value })}
                placeholder="ex: Siège social, Datacenter Paris, Agence Lyon..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-site-description">Description</Label>
              <Textarea
                id="create-site-description"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Décrivez l'activité ou la fonction de ce site..."
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-site-adresse">Adresse</Label>
              <Input
                id="create-site-adresse"
                value={form.adresse}
                onChange={(e) => setForm({ ...form, adresse: e.target.value })}
                placeholder="Adresse complète du site"
              />
            </div>
          </div>

          {formError && <p className="text-sm text-destructive">{formError}</p>}

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Annuler
            </Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Créer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Dialog: Modifier ── */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Modifier le site</DialogTitle>
            <DialogDescription>
              Modifiez les informations de &laquo; {selected?.nom} &raquo;
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-site-nom">Nom du site *</Label>
              <Input
                id="edit-site-nom"
                value={form.nom}
                onChange={(e) => setForm({ ...form, nom: e.target.value })}
                placeholder="ex: Siège social, Datacenter Paris, Agence Lyon..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-site-description">Description</Label>
              <Textarea
                id="edit-site-description"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Décrivez l'activité ou la fonction de ce site..."
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-site-adresse">Adresse</Label>
              <Input
                id="edit-site-adresse"
                value={form.adresse}
                onChange={(e) => setForm({ ...form, adresse: e.target.value })}
                placeholder="Adresse complète du site"
              />
            </div>
          </div>

          {formError && <p className="text-sm text-destructive">{formError}</p>}

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Annuler
            </Button>
            <Button onClick={handleUpdate} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Enregistrer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Dialog: Supprimer ── */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmer la suppression</DialogTitle>
            <DialogDescription>
              Êtes-vous sûr de vouloir supprimer le site &laquo;{" "}
              <strong>{selected?.nom}</strong> &raquo; ? Cette action est
              irréversible et supprimera tous les équipements associés.
            </DialogDescription>
          </DialogHeader>

          {formError && <p className="text-sm text-destructive">{formError}</p>}

          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Annuler
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Supprimer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Dialog: Détail ── */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              {selected?.nom}
            </DialogTitle>
          </DialogHeader>

          {selected && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Entreprise</p>
                  <Badge variant="outline" className="mt-1">
                    <Building2 className="h-3 w-3 mr-1" />
                    {entrepriseMap[selected.entreprise_id] || `#${selected.entreprise_id}`}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Équipements</p>
                  <div className="flex items-center gap-1 mt-1">
                    <Server className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">{selected.equipement_count}</span>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-muted-foreground">Description</p>
                <p className="text-sm mt-1 whitespace-pre-wrap">{selected.description || "Non renseignée"}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Adresse</p>
                <p className="text-sm mt-1">{selected.adresse || "Non renseignée"}</p>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() =>
                router.push(`/equipements?site=${selected?.id}`)
              }
            >
              <Server className="h-4 w-4 mr-2" />
              Voir les équipements
            </Button>
            <Button
              onClick={() => {
                setDetailOpen(false);
                if (selected) openEdit(selected);
              }}
            >
              <Pencil className="h-4 w-4 mr-2" />
              Modifier
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
