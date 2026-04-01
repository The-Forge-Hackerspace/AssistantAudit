"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Plus,
  Pencil,
  Trash2,
  Eye,
  ChevronLeft,
  ChevronRight,
  Search,
  Loader2,
  Server,
} from "lucide-react";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { equipementsApi, sitesApi } from "@/services/api";
import type { Equipement, EquipementCreate, Site, TypeEquipement } from "@/types";
import { toast } from "sonner";
import { TableSkeleton } from "@/components/skeletons";
import {
  EQUIPEMENT_TYPE_LABELS as TYPE_LABELS,
  EQUIPEMENT_TYPE_ICONS as TYPE_ICONS,
  EQUIPEMENT_STATUS_LABELS as STATUS_LABELS,
  EQUIPEMENT_STATUS_VARIANTS as STATUS_VARIANTS,
} from "@/lib/constants";
import { EquipementFormFields } from "./components/equipement-form-fields";
import { EquipementDetailDialog } from "./components/equipement-detail-dialog";
import { TagFilter } from "@/components/tags/tag-filter";

// ── Default create form ──
const EMPTY_FORM: EquipementCreate = {
  site_id: 0,
  type_equipement: "serveur",
  ip_address: "",
  hostname: "",
  fabricant: "",
  os_detected: "",
};

export default function EquipementsPage() {
  return (
    <Suspense fallback={<div className="p-6">Chargement…</div>}>
      <EquipementsContent />
    </Suspense>
  );
}

function EquipementsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialSite = searchParams.get("site") || "all";

  // ── State ──
  const [equipements, setEquipements] = useState<Equipement[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [siteMap, setSiteMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");

  // Filters
  const [siteFilter, setSiteFilter] = useState<string>(initialSite);
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [tagFilter, setTagFilter] = useState<number[]>([]);

  // Dialogs
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selected, setSelected] = useState<Equipement | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Form state
  const [form, setForm] = useState<EquipementCreate & { notes_audit?: string }>({
    ...EMPTY_FORM,
  });

  const PAGE_SIZE = 10;

  // ── Load sites for filter & form ──
  useEffect(() => {
    const loadSites = async () => {
      try {
        const res = await sitesApi.list(1, 100);
        setSites(res.items);
        const map: Record<number, string> = {};
        res.items.forEach((s) => (map[s.id] = s.nom));
        setSiteMap(map);
      } catch {
        toast.error("Erreur lors du chargement des sites");
      }
    };
    loadSites();
  }, []);

  // ── Load equipements ──
  const loadEquipements = useCallback(async () => {
    setLoading(true);
    try {
      const filters: { site_id?: number; type_equipement?: string; status_audit?: string } = {};
      if (siteFilter !== "all") filters.site_id = Number(siteFilter);
      if (typeFilter !== "all") filters.type_equipement = typeFilter;
      if (statusFilter !== "all") filters.status_audit = statusFilter;
      const res = await equipementsApi.list(page, PAGE_SIZE, filters);
      setEquipements(res.items);
      setPages(res.pages);
      setTotal(res.total);
    } catch {
      toast.error("Erreur lors du chargement des équipements");
    } finally {
      setLoading(false);
    }
  }, [page, siteFilter, typeFilter, statusFilter]);

  useEffect(() => {
    loadEquipements();
  }, [loadEquipements]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [siteFilter, typeFilter, statusFilter]);

  // ── Search filtering (client-side on current page) ──
  const filtered = search
    ? equipements.filter(
        (e) =>
          e.ip_address.toLowerCase().includes(search.toLowerCase()) ||
          (e.hostname || "").toLowerCase().includes(search.toLowerCase()) ||
          (e.fabricant || "").toLowerCase().includes(search.toLowerCase()) ||
          (siteMap[e.site_id] || "").toLowerCase().includes(search.toLowerCase())
      )
    : equipements;

  // ── Helpers ──
  const resetForm = () => {
    setForm({ ...EMPTY_FORM });
    setFormError("");
  };

  const openCreate = () => {
    resetForm();
    if (siteFilter !== "all") {
      setForm((f) => ({ ...f, site_id: Number(siteFilter) }));
    }
    setCreateOpen(true);
  };

  const openEdit = (e: Equipement) => {
    setSelected(e);
    setForm({
      site_id: e.site_id,
      type_equipement: e.type_equipement,
      ip_address: e.ip_address,
      hostname: e.hostname || "",
      fabricant: e.fabricant || "",
      os_detected: e.os_detected || "",
      notes_audit: e.notes_audit || "",
      // Type-specific fields
      ...(e.type_equipement === "reseau" && { firmware_version: e.firmware_version || "" }),
      ...(e.type_equipement === "serveur" && {
        os_version_detail: e.os_version_detail || "",
        modele_materiel: e.modele_materiel || "",
      }),
      ...(e.type_equipement === "firewall" && {
        license_status: e.license_status || "",
        vpn_users_count: e.vpn_users_count ?? 0,
        rules_count: e.rules_count ?? 0,
      }),
    });
    setFormError("");
    setEditOpen(true);
  };

  const openDelete = (e: Equipement) => {
    setSelected(e);
    setFormError("");
    setDeleteOpen(true);
  };

  const openDetail = (e: Equipement) => {
    setSelected(e);
    setDetailOpen(true);
  };

  // ── CRUD ──
  const handleCreate = async () => {
    if (!form.ip_address.trim()) {
      setFormError("L'adresse IP est obligatoire");
      return;
    }
    if (!form.site_id) {
      setFormError("Veuillez sélectionner un site");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      const { notes_audit, ...createPayload } = form;
      const payload = { ...createPayload, notes_audit };
      await equipementsApi.create(payload as EquipementCreate);
      setCreateOpen(false);
      resetForm();
      loadEquipements();
      toast.success("Équipement créé avec succès");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
      toast.error("Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!selected || !form.ip_address.trim()) {
      setFormError("L'adresse IP est obligatoire");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await equipementsApi.update(selected.id, {
        hostname: form.hostname || undefined,
        fabricant: form.fabricant || undefined,
        os_detected: form.os_detected || undefined,
        notes_audit: form.notes_audit || undefined,
        // Type-specific
        ...(selected.type_equipement === "reseau" && {
          firmware_version: (form as Record<string, unknown>).firmware_version || undefined,
        }),
        ...(selected.type_equipement === "serveur" && {
          os_version_detail: (form as Record<string, unknown>).os_version_detail || undefined,
          modele_materiel: (form as Record<string, unknown>).modele_materiel || undefined,
        }),
        ...(selected.type_equipement === "firewall" && {
          license_status: (form as Record<string, unknown>).license_status || undefined,
          vpn_users_count: (form as Record<string, unknown>).vpn_users_count || undefined,
          rules_count: (form as Record<string, unknown>).rules_count || undefined,
        }),
      });
      setEditOpen(false);
      resetForm();
      loadEquipements();
      toast.success("Équipement mis à jour");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la mise à jour");
      toast.error("Erreur lors de la mise à jour");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    setSaving(true);
    setFormError("");
    try {
      await equipementsApi.delete(selected.id);
      setDeleteOpen(false);
      loadEquipements();
      toast.success("Équipement supprimé");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la suppression");
      toast.error("Erreur lors de la suppression");
    } finally {
      setSaving(false);
    }
  };

  const TypeIcon = ({ type }: { type: TypeEquipement }) => {
    const Icon = TYPE_ICONS[type] || Server;
    return <Icon className="size-4" />;
  };

  return (
    <div className="flex flex-col gap-6">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Équipements</h1>
          <p className="text-muted-foreground">
            {total} équipement{total !== 1 ? "s" : ""} enregistré{total !== 1 ? "s" : ""}
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus data-icon="inline-start" />
          Nouvel équipement
        </Button>
      </div>

      {/* ── Filters ── */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Rechercher par IP, hostname, fabricant..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={siteFilter} onValueChange={setSiteFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Filtrer par site" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="all">Tous les sites</SelectItem>
                  {sites.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.nom}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="all">Tous les types</SelectItem>
                  {Object.entries(TYPE_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[170px]">
                <SelectValue placeholder="Statut" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="A_AUDITER">À auditer</SelectItem>
                  <SelectItem value="EN_COURS">En cours</SelectItem>
                  <SelectItem value="CONFORME">Conforme</SelectItem>
                  <SelectItem value="NON_CONFORME">Non conforme</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* ── Tag filter ── */}
      <TagFilter onFilterChange={setTagFilter} selectedTagIds={tagFilter} />

      {/* ── Table ── */}
      <Card>
        {loading ? (
          <TableSkeleton rows={5} cols={5} />
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <Server className="size-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Aucun équipement trouvé</p>
            <p className="text-sm mt-1">
              {equipements.length === 0
                ? "Ajoutez votre premier équipement pour commencer"
                : "Essayez de modifier vos critères de recherche"}
            </p>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>IP</TableHead>
                  <TableHead>Hostname</TableHead>
                  <TableHead>Site</TableHead>
                  <TableHead>Fabricant</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((eq) => (
                  <TableRow key={eq.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <TypeIcon type={eq.type_equipement} />
                        <span className="text-sm">{TYPE_LABELS[eq.type_equipement]}</span>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{eq.ip_address}</TableCell>
                    <TableCell>{eq.hostname || "—"}</TableCell>
                    <TableCell>
                      <button
                        className="text-sm text-primary hover:underline"
                        onClick={() => router.push(`/sites?entreprise=all`)}
                      >
                        {siteMap[eq.site_id] || `#${eq.site_id}`}
                      </button>
                    </TableCell>
                    <TableCell>{eq.fabricant || "—"}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANTS[eq.status_audit]}>
                        {STATUS_LABELS[eq.status_audit]}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button size="icon" variant="ghost" onClick={() => openDetail(eq)}>
                          <Eye />
                        </Button>
                        <Button size="icon" variant="ghost" onClick={() => openEdit(eq)}>
                          <Pencil />
                        </Button>
                        <Button size="icon" variant="ghost" onClick={() => openDelete(eq)}>
                          <Trash2 className="text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            <CardFooter className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {page} sur {pages} — {total} résultat{total !== 1 ? "s" : ""}
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  <ChevronLeft data-icon="inline-start" />
                  Précédent
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Suivant
                  <ChevronRight data-icon="inline-end" />
                </Button>
              </div>
            </CardFooter>
          </>
        )}
      </Card>

      {/* ── Dialog: Créer ── */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nouvel équipement</DialogTitle>
            <DialogDescription>
              Ajoutez un équipement à un site
            </DialogDescription>
          </DialogHeader>

          <EquipementFormFields
            mode="create"
            form={form}
            setForm={setForm}
            sites={sites}
            formError={formError}
            idPrefix="create"
          />

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Annuler
            </Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Créer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Dialog: Modifier ── */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Modifier l&apos;équipement</DialogTitle>
            <DialogDescription>
              Modifiez les informations de {selected?.hostname || selected?.ip_address}
            </DialogDescription>
          </DialogHeader>

          <EquipementFormFields
            mode="edit"
            form={form}
            setForm={setForm}
            sites={sites}
            formError={formError}
            selectedIp={selected?.ip_address}
            selectedType={selected?.type_equipement}
            idPrefix="edit"
          />

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Annuler
            </Button>
            <Button onClick={handleUpdate} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Enregistrer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── AlertDialog: Supprimer ── */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer l&apos;équipement{" "}
              <strong>{selected?.hostname || selected?.ip_address}</strong> ? Cette action est
              irréversible et supprimera tous les assessments associés.
            </AlertDialogDescription>
          </AlertDialogHeader>

          {formError && <p className="text-sm text-destructive">{formError}</p>}

          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteOpen(false)}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleDelete}
              disabled={saving}
            >
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ── Dialog: Détail ── */}
      <EquipementDetailDialog
        selected={selected}
        open={detailOpen}
        onOpenChange={setDetailOpen}
        siteMap={siteMap}
        onEdit={openEdit}
      />
    </div>
  );
}
