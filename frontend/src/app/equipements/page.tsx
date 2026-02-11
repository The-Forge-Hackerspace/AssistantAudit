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
  Shield,
  Wifi,
  Monitor,
  MapPin,
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
import { equipementsApi, sitesApi } from "@/services/api";
import type { Equipement, EquipementCreate, Site, TypeEquipement, StatusAudit } from "@/types";

// ── Constants ──
const TYPE_LABELS: Record<TypeEquipement, string> = {
  serveur: "Serveur",
  firewall: "Firewall",
  reseau: "Réseau",
  equipement: "Autre",
};

const TYPE_ICONS: Record<TypeEquipement, typeof Server> = {
  serveur: Monitor,
  firewall: Shield,
  reseau: Wifi,
  equipement: Server,
};

const STATUS_LABELS: Record<StatusAudit, string> = {
  A_AUDITER: "À auditer",
  EN_COURS: "En cours",
  CONFORME: "Conforme",
  NON_CONFORME: "Non conforme",
};

const STATUS_VARIANTS: Record<StatusAudit, "default" | "secondary" | "destructive" | "outline"> = {
  A_AUDITER: "outline",
  EN_COURS: "secondary",
  CONFORME: "default",
  NON_CONFORME: "destructive",
};

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
        /* ignore */
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
      /* ignore */
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
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
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
      await equipementsApi.delete(selected.id);
      setDeleteOpen(false);
      loadEquipements();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la suppression");
    } finally {
      setSaving(false);
    }
  };

  const TypeIcon = ({ type }: { type: TypeEquipement }) => {
    const Icon = TYPE_ICONS[type] || Server;
    return <Icon className="h-4 w-4" />;
  };

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Équipements</h1>
          <p className="text-muted-foreground">
            {total} équipement{total !== 1 ? "s" : ""} enregistré{total !== 1 ? "s" : ""}
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-2" />
          Nouvel équipement
        </Button>
      </div>

      {/* ── Filters ── */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
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
                <SelectItem value="all">Tous les sites</SelectItem>
                {sites.map((s) => (
                  <SelectItem key={s.id} value={String(s.id)}>
                    {s.nom}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les types</SelectItem>
                <SelectItem value="serveur">Serveur</SelectItem>
                <SelectItem value="firewall">Firewall</SelectItem>
                <SelectItem value="reseau">Réseau</SelectItem>
                <SelectItem value="equipement">Autre</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[170px]">
                <SelectValue placeholder="Statut" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les statuts</SelectItem>
                <SelectItem value="A_AUDITER">À auditer</SelectItem>
                <SelectItem value="EN_COURS">En cours</SelectItem>
                <SelectItem value="CONFORME">Conforme</SelectItem>
                <SelectItem value="NON_CONFORME">Non conforme</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* ── Table ── */}
      <Card>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <Server className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Aucun équipement trouvé</p>
            <p className="text-sm mt-1">
              {equipements.length === 0
                ? "Ajoutez votre premier équipement pour commencer"
                : "Essayez de modifier vos critères de recherche"}
            </p>
          </div>
        ) : (
          <div>
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
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button size="icon" variant="ghost" onClick={() => openEdit(eq)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button size="icon" variant="ghost" onClick={() => openDelete(eq)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t">
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
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Précédent
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Suivant
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          </div>
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

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Site *</Label>
              <Select
                value={form.site_id ? String(form.site_id) : ""}
                onValueChange={(v) => setForm({ ...form, site_id: Number(v) })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un site" />
                </SelectTrigger>
                <SelectContent>
                  {sites.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Type d&apos;équipement *</Label>
              <Select
                value={form.type_equipement}
                onValueChange={(v) =>
                  setForm({ ...form, type_equipement: v as TypeEquipement })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="serveur">Serveur</SelectItem>
                  <SelectItem value="firewall">Firewall</SelectItem>
                  <SelectItem value="reseau">Réseau (switch, routeur, borne...)</SelectItem>
                  <SelectItem value="equipement">Autre</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="create-ip">Adresse IP *</Label>
                <Input
                  id="create-ip"
                  value={form.ip_address}
                  onChange={(e) => setForm({ ...form, ip_address: e.target.value })}
                  placeholder="192.168.1.1"
                  className="font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="create-hostname">Hostname</Label>
                <Input
                  id="create-hostname"
                  value={form.hostname}
                  onChange={(e) => setForm({ ...form, hostname: e.target.value })}
                  placeholder="SRV-DC01"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="create-fabricant">Fabricant</Label>
                <Input
                  id="create-fabricant"
                  value={form.fabricant}
                  onChange={(e) => setForm({ ...form, fabricant: e.target.value })}
                  placeholder="Dell, HP, Fortinet..."
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="create-os">OS détecté</Label>
                <Input
                  id="create-os"
                  value={form.os_detected}
                  onChange={(e) => setForm({ ...form, os_detected: e.target.value })}
                  placeholder="Windows Server 2022, FortiOS 7.4..."
                />
              </div>
            </div>

            {/* Type-specific fields */}
            {form.type_equipement === "reseau" && (
              <div className="space-y-2 border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground">Champs réseau</p>
                <div className="space-y-2">
                  <Label htmlFor="create-firmware">Version firmware</Label>
                  <Input
                    id="create-firmware"
                    value={(form as Record<string, unknown>).firmware_version as string || ""}
                    onChange={(e) => setForm({ ...form, firmware_version: e.target.value })}
                    placeholder="ex: IOS 15.2, ArubaOS 8.10..."
                  />
                </div>
              </div>
            )}

            {form.type_equipement === "serveur" && (
              <div className="space-y-4 border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground">Champs serveur</p>
                <div className="space-y-2">
                  <Label htmlFor="create-os-detail">Détail version OS</Label>
                  <Input
                    id="create-os-detail"
                    value={(form as Record<string, unknown>).os_version_detail as string || ""}
                    onChange={(e) => setForm({ ...form, os_version_detail: e.target.value })}
                    placeholder="ex: Windows Server 2022 Datacenter Build 20348"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-modele">Modèle matériel</Label>
                  <Input
                    id="create-modele"
                    value={(form as Record<string, unknown>).modele_materiel as string || ""}
                    onChange={(e) => setForm({ ...form, modele_materiel: e.target.value })}
                    placeholder="ex: Dell PowerEdge R740"
                  />
                </div>
              </div>
            )}

            {form.type_equipement === "firewall" && (
              <div className="space-y-4 border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground">Champs firewall</p>
                <div className="space-y-2">
                  <Label htmlFor="create-license">Statut licence</Label>
                  <Input
                    id="create-license"
                    value={(form as Record<string, unknown>).license_status as string || ""}
                    onChange={(e) => setForm({ ...form, license_status: e.target.value })}
                    placeholder="ex: Active, Expired, Trial..."
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="create-vpn">Utilisateurs VPN</Label>
                    <Input
                      id="create-vpn"
                      type="number"
                      value={(form as Record<string, unknown>).vpn_users_count as number ?? 0}
                      onChange={(e) =>
                        setForm({ ...form, vpn_users_count: parseInt(e.target.value) || 0 })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="create-rules">Nombre de règles</Label>
                    <Input
                      id="create-rules"
                      type="number"
                      value={(form as Record<string, unknown>).rules_count as number ?? 0}
                      onChange={(e) =>
                        setForm({ ...form, rules_count: parseInt(e.target.value) || 0 })
                      }
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="create-notes">Notes d&apos;audit</Label>
              <Textarea
                id="create-notes"
                value={form.notes_audit || ""}
                onChange={(e) => setForm({ ...form, notes_audit: e.target.value })}
                placeholder="Observations, remarques..."
                rows={3}
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
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Modifier l&apos;équipement</DialogTitle>
            <DialogDescription>
              Modifiez les informations de {selected?.hostname || selected?.ip_address}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Adresse IP</Label>
                <Input value={selected?.ip_address || ""} disabled className="font-mono" />
                <p className="text-xs text-muted-foreground">Non modifiable</p>
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <Input value={TYPE_LABELS[selected?.type_equipement || "equipement"]} disabled />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-hostname">Hostname</Label>
                <Input
                  id="edit-hostname"
                  value={form.hostname}
                  onChange={(e) => setForm({ ...form, hostname: e.target.value })}
                  placeholder="SRV-DC01"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-fabricant">Fabricant</Label>
                <Input
                  id="edit-fabricant"
                  value={form.fabricant}
                  onChange={(e) => setForm({ ...form, fabricant: e.target.value })}
                  placeholder="Dell, HP..."
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-os">OS détecté</Label>
              <Input
                id="edit-os"
                value={form.os_detected}
                onChange={(e) => setForm({ ...form, os_detected: e.target.value })}
                placeholder="Windows Server 2022..."
              />
            </div>

            {/* Type-specific fields */}
            {selected?.type_equipement === "reseau" && (
              <div className="space-y-2 border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground">Champs réseau</p>
                <div className="space-y-2">
                  <Label htmlFor="edit-firmware">Version firmware</Label>
                  <Input
                    id="edit-firmware"
                    value={(form as Record<string, unknown>).firmware_version as string || ""}
                    onChange={(e) => setForm({ ...form, firmware_version: e.target.value })}
                  />
                </div>
              </div>
            )}

            {selected?.type_equipement === "serveur" && (
              <div className="space-y-4 border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground">Champs serveur</p>
                <div className="space-y-2">
                  <Label htmlFor="edit-os-detail">Détail version OS</Label>
                  <Input
                    id="edit-os-detail"
                    value={(form as Record<string, unknown>).os_version_detail as string || ""}
                    onChange={(e) => setForm({ ...form, os_version_detail: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-modele">Modèle matériel</Label>
                  <Input
                    id="edit-modele"
                    value={(form as Record<string, unknown>).modele_materiel as string || ""}
                    onChange={(e) => setForm({ ...form, modele_materiel: e.target.value })}
                  />
                </div>
              </div>
            )}

            {selected?.type_equipement === "firewall" && (
              <div className="space-y-4 border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground">Champs firewall</p>
                <div className="space-y-2">
                  <Label htmlFor="edit-license">Statut licence</Label>
                  <Input
                    id="edit-license"
                    value={(form as Record<string, unknown>).license_status as string || ""}
                    onChange={(e) => setForm({ ...form, license_status: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit-vpn">Utilisateurs VPN</Label>
                    <Input
                      id="edit-vpn"
                      type="number"
                      value={(form as Record<string, unknown>).vpn_users_count as number ?? 0}
                      onChange={(e) =>
                        setForm({ ...form, vpn_users_count: parseInt(e.target.value) || 0 })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit-rules">Nombre de règles</Label>
                    <Input
                      id="edit-rules"
                      type="number"
                      value={(form as Record<string, unknown>).rules_count as number ?? 0}
                      onChange={(e) =>
                        setForm({ ...form, rules_count: parseInt(e.target.value) || 0 })
                      }
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="edit-notes">Notes d&apos;audit</Label>
              <Textarea
                id="edit-notes"
                value={form.notes_audit || ""}
                onChange={(e) => setForm({ ...form, notes_audit: e.target.value })}
                placeholder="Observations, remarques..."
                rows={3}
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
              Êtes-vous sûr de vouloir supprimer l&apos;équipement{" "}
              <strong>{selected?.hostname || selected?.ip_address}</strong> ? Cette action est
              irréversible et supprimera tous les assessments associés.
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
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selected && <TypeIcon type={selected.type_equipement} />}
              {selected?.hostname || selected?.ip_address}
            </DialogTitle>
          </DialogHeader>

          {selected && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Type</p>
                  <div className="flex items-center gap-2 mt-1">
                    <TypeIcon type={selected.type_equipement} />
                    <span className="text-sm font-medium">
                      {TYPE_LABELS[selected.type_equipement]}
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Statut audit</p>
                  <Badge variant={STATUS_VARIANTS[selected.status_audit]} className="mt-1">
                    {STATUS_LABELS[selected.status_audit]}
                  </Badge>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Adresse IP</p>
                  <p className="text-sm mt-1 font-mono">{selected.ip_address}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Hostname</p>
                  <p className="text-sm mt-1">{selected.hostname || "Non renseigné"}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Site</p>
                  <Badge variant="outline" className="mt-1">
                    <MapPin className="h-3 w-3 mr-1" />
                    {siteMap[selected.site_id] || `#${selected.site_id}`}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Fabricant</p>
                  <p className="text-sm mt-1">{selected.fabricant || "Non renseigné"}</p>
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-muted-foreground">OS détecté</p>
                <p className="text-sm mt-1">{selected.os_detected || "Non renseigné"}</p>
              </div>

              {/* Type-specific details */}
              {selected.type_equipement === "reseau" && selected.firmware_version && (
                <div className="border-t pt-4">
                  <p className="text-sm font-medium text-muted-foreground mb-2">Détails réseau</p>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Firmware</p>
                    <p className="text-sm mt-1">{selected.firmware_version}</p>
                  </div>
                </div>
              )}

              {selected.type_equipement === "serveur" && (
                <div className="border-t pt-4 space-y-3">
                  <p className="text-sm font-medium text-muted-foreground">Détails serveur</p>
                  {selected.os_version_detail && (
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Version OS détaillée</p>
                      <p className="text-sm mt-1">{selected.os_version_detail}</p>
                    </div>
                  )}
                  {selected.modele_materiel && (
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Modèle matériel</p>
                      <p className="text-sm mt-1">{selected.modele_materiel}</p>
                    </div>
                  )}
                </div>
              )}

              {selected.type_equipement === "firewall" && (
                <div className="border-t pt-4 space-y-3">
                  <p className="text-sm font-medium text-muted-foreground">Détails firewall</p>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Licence</p>
                      <p className="text-sm mt-1">{selected.license_status || "—"}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Users VPN</p>
                      <p className="text-sm mt-1">{selected.vpn_users_count ?? 0}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Règles</p>
                      <p className="text-sm mt-1">{selected.rules_count ?? 0}</p>
                    </div>
                  </div>
                </div>
              )}

              {selected.notes_audit && (
                <div className="border-t pt-4">
                  <p className="text-sm font-medium text-muted-foreground">Notes d&apos;audit</p>
                  <p className="text-sm mt-1 whitespace-pre-wrap">{selected.notes_audit}</p>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
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
