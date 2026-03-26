"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Building2,
  Plus,
  Search,
  Pencil,
  Trash2,
  Eye,
  MapPin,
  Loader2,
  Users,
  ChevronLeft,
  ChevronRight,
  X,
  UserPlus,
} from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
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
import { entreprisesApi } from "@/services/api";
import type { Entreprise, EntrepriseCreate, Contact } from "@/types";
import { toast } from "sonner";
import { TableSkeleton } from "@/components/skeletons";
import { cn } from "@/lib/utils";

// ── Contact form row ──
interface ContactFormData {
  nom: string;
  role: string;
  email: string;
  telephone: string;
  is_main_contact: boolean;
  _key?: string;
}

const emptyContact: ContactFormData = {
  nom: "",
  role: "",
  email: "",
  telephone: "",
  is_main_contact: false,
};

let contactKeyCounter = 0;
function nextContactKey() {
  return `contact-${++contactKeyCounter}`;
}

// ── Main page ──
export default function EntreprisesPage() {
  const router = useRouter();

  // List state
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  // Dialog state
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selected, setSelected] = useState<Entreprise | null>(null);
  const [saving, setSaving] = useState(false);

  // Form state
  const [form, setForm] = useState<EntrepriseCreate>({
    nom: "",
    adresse: "",
    secteur_activite: "",
    siret: "",
    presentation_desc: "",
    contraintes_reglementaires: "",
    contacts: [],
  });
  const [contacts, setContacts] = useState<ContactFormData[]>([]);
  const [formError, setFormError] = useState("");

  const PAGE_SIZE = 10;

  const loadEntreprises = useCallback(async () => {
    setLoading(true);
    try {
      const res = await entreprisesApi.list(page, PAGE_SIZE);
      setEntreprises(res.items);
      setTotal(res.total);
      setPages(res.pages);
    } catch (error) {
      toast.error("Impossible de charger les entreprises");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadEntreprises();
  }, [loadEntreprises]);

  // ── Filtered list (client-side search on loaded page) ──
  const filtered = search
    ? entreprises.filter(
        (e) =>
          e.nom.toLowerCase().includes(search.toLowerCase()) ||
          (e.secteur_activite || "").toLowerCase().includes(search.toLowerCase()) ||
          (e.siret || "").includes(search)
      )
    : entreprises;

  // ── Helpers ──
  const resetForm = () => {
    setForm({
      nom: "",
      adresse: "",
      secteur_activite: "",
      siret: "",
      presentation_desc: "",
      contraintes_reglementaires: "",
      contacts: [],
    });
    setContacts([]);
    setFormError("");
  };

  const openCreate = () => {
    resetForm();
    setCreateOpen(true);
  };

  const openEdit = (e: Entreprise) => {
    setSelected(e);
    setForm({
      nom: e.nom,
      adresse: e.adresse || "",
      secteur_activite: e.secteur_activite || "",
      siret: e.siret || "",
      presentation_desc: e.presentation_desc || "",
      contraintes_reglementaires: e.contraintes_reglementaires || "",
      contacts: [],
    });
    setContacts(
      e.contacts.map((c) => ({
        nom: c.nom,
        role: c.role || "",
        email: c.email || "",
        telephone: c.telephone || "",
        is_main_contact: c.is_main_contact,
      }))
    );
    setFormError("");
    setEditOpen(true);
  };

  const openDelete = (e: Entreprise) => {
    setSelected(e);
    setDeleteOpen(true);
  };

  const openDetail = (e: Entreprise) => {
    setSelected(e);
    setDetailOpen(true);
  };

  // ── Contact management ──
  const addContact = () => {
    setContacts([...contacts, { ...emptyContact, _key: nextContactKey() }]);
  };

  const updateContact = (index: number, field: keyof ContactFormData, value: string | boolean) => {
    const updated = contacts.map((c, i) => (i === index ? { ...c, [field]: value } : c));
    setContacts(updated);
  };

  const removeContact = (index: number) => {
    setContacts(contacts.filter((_, i) => i !== index));
  };

  // ── CRUD handlers ──
  const handleCreate = async () => {
    if (!form.nom.trim()) {
      setFormError("Le nom de l'entreprise est obligatoire");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await entreprisesApi.create({
        ...form,
        contacts: contacts.filter((c) => c.nom.trim()),
      });
      setCreateOpen(false);
      resetForm();
      loadEntreprises();
      toast.success("Entreprise créée avec succès");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
      toast.error("Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!selected || !form.nom.trim()) {
      setFormError("Le nom de l'entreprise est obligatoire");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await entreprisesApi.update(selected.id, {
        nom: form.nom,
        adresse: form.adresse || undefined,
        secteur_activite: form.secteur_activite || undefined,
        siret: form.siret || undefined,
        presentation_desc: form.presentation_desc || undefined,
        contraintes_reglementaires: form.contraintes_reglementaires || undefined,
        contacts: contacts.filter((c) => c.nom.trim()),
      });
      setEditOpen(false);
      resetForm();
      loadEntreprises();
      toast.success("Entreprise mise à jour");
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
    try {
      await entreprisesApi.delete(selected.id);
      setDeleteOpen(false);
      setSelected(null);
      loadEntreprises();
      toast.success("Entreprise supprimée");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la suppression");
      toast.error("Erreur lors de la suppression");
    } finally {
      setSaving(false);
    }
  };

  // ── Render ──
  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Building2 className="size-6" />
            Entreprises
          </h1>
          <p className="text-muted-foreground">
            Gérez les entreprises clientes et leurs informations
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus data-icon="inline-start" />
          Nouvelle entreprise
        </Button>
      </div>

      {/* Search + stats */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher par nom, secteur ou SIRET..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Badge variant="secondary" className="text-sm">
          {total} entreprise{total > 1 ? "s" : ""}
        </Badge>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton rows={5} cols={4} />
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <Building2 className="size-12 mb-4 opacity-30" />
              <p className="text-lg font-medium">Aucune entreprise</p>
              <p className="text-sm">
                {search ? "Aucun résultat pour cette recherche" : "Commencez par ajouter une entreprise"}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Secteur</TableHead>
                  <TableHead>SIRET</TableHead>
                  <TableHead>Contacts</TableHead>
                  <TableHead>Créée le</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((entreprise) => (
                  <TableRow
                    key={entreprise.id}
                    className="cursor-pointer"
                    onClick={() => openDetail(entreprise)}
                  >
                    <TableCell className="font-medium">{entreprise.nom}</TableCell>
                    <TableCell>
                      {entreprise.secteur_activite ? (
                        <Badge variant="outline">{entreprise.secteur_activite}</Badge>
                      ) : (
                        <span className="text-muted-foreground text-sm">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-sm">
                        {entreprise.siret || "—"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Users className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-sm">{entreprise.contacts?.length || 0}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(entreprise.created_at).toLocaleDateString("fr-FR")}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => openDetail(entreprise)}
                          title="Voir le détail"
                        >
                          <Eye />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => openEdit(entreprise)}
                          title="Modifier"
                        >
                          <Pencil />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-destructive hover:text-destructive"
                          onClick={() => openDelete(entreprise)}
                          title="Supprimer"
                        >
                          <Trash2 />
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
          <CardFooter className="flex items-center justify-between border-t px-4 py-3">
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
                <ChevronLeft data-icon="inline-start" />
                Précédent
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant
                <ChevronRight data-icon="inline-end" />
              </Button>
            </div>
          </CardFooter>
        )}
      </Card>

      {/* ── Dialog: Créer ── */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nouvelle entreprise</DialogTitle>
            <DialogDescription>
              Renseignez les informations de l&apos;entreprise cliente
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="create-nom">Nom *</Label>
                <Input
                  id="create-nom"
                  value={form.nom}
                  onChange={(e) => setForm({ ...form, nom: e.target.value })}
                  placeholder="Nom de l'entreprise"
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="create-siret">SIRET</Label>
                <Input
                  id="create-siret"
                  value={form.siret}
                  onChange={(e) => setForm({ ...form, siret: e.target.value })}
                  placeholder="12345678901234"
                  maxLength={14}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="create-secteur">Secteur d&apos;activité</Label>
                <Input
                  id="create-secteur"
                  value={form.secteur_activite}
                  onChange={(e) => setForm({ ...form, secteur_activite: e.target.value })}
                  placeholder="ex: Finance, Santé, Industrie..."
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="create-adresse">Adresse</Label>
                <Input
                  id="create-adresse"
                  value={form.adresse}
                  onChange={(e) => setForm({ ...form, adresse: e.target.value })}
                  placeholder="Adresse du siège"
                />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="create-presentation">Présentation</Label>
              <Textarea
                id="create-presentation"
                className="min-h-[80px]"
                value={form.presentation_desc}
                onChange={(e) => setForm({ ...form, presentation_desc: e.target.value })}
                placeholder="Description de l'entreprise..."
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="create-contraintes">Contraintes réglementaires</Label>
              <Textarea
                id="create-contraintes"
                className="min-h-[60px]"
                value={form.contraintes_reglementaires}
                onChange={(e) => setForm({ ...form, contraintes_reglementaires: e.target.value })}
                placeholder="RGPD, PCI-DSS, ISO 27001..."
              />
            </div>
            <Separator />
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <Label className="text-base font-semibold">Contacts</Label>
                <Button type="button" variant="outline" size="sm" onClick={addContact}>
                  <UserPlus data-icon="inline-start" />
                  Ajouter
                </Button>
              </div>
              {contacts.map((contact, index) => (
                <div key={index} className="rounded-md border p-3 flex flex-col gap-3 relative">
                  <Button type="button" variant="ghost" size="icon" className="absolute top-1 right-1 size-6" onClick={() => removeContact(index)}>
                    <X />
                  </Button>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1">
                      <Label className="text-xs">Nom</Label>
                      <Input value={contact.nom} onChange={(e) => updateContact(index, "nom", e.target.value)} placeholder="Nom du contact" className="h-8 text-sm" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <Label className="text-xs">Rôle</Label>
                      <Input value={contact.role} onChange={(e) => updateContact(index, "role", e.target.value)} placeholder="DSI, RSSI, Admin..." className="h-8 text-sm" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1">
                      <Label className="text-xs">Email</Label>
                      <Input type="email" value={contact.email} onChange={(e) => updateContact(index, "email", e.target.value)} placeholder="email@exemple.com" className="h-8 text-sm" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <Label className="text-xs">Téléphone</Label>
                      <Input value={contact.telephone} onChange={(e) => updateContact(index, "telephone", e.target.value)} placeholder="+33 1 23 45 67 89" className="h-8 text-sm" />
                    </div>
                  </div>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <Checkbox checked={contact.is_main_contact} onCheckedChange={(checked) => updateContact(index, "is_main_contact", !!checked)} />
                    Contact principal
                  </label>
                </div>
              ))}
              {contacts.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-2">Aucun contact ajouté</p>
              )}
            </div>
          </div>

          {formError && (
            <p className="text-sm text-destructive">{formError}</p>
          )}

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
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Modifier l&apos;entreprise</DialogTitle>
            <DialogDescription>
              Modifiez les informations de &laquo; {selected?.nom} &raquo;
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="edit-nom">Nom *</Label>
                <Input
                  id="edit-nom"
                  value={form.nom}
                  onChange={(e) => setForm({ ...form, nom: e.target.value })}
                  placeholder="Nom de l'entreprise"
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="edit-siret">SIRET</Label>
                <Input
                  id="edit-siret"
                  value={form.siret}
                  onChange={(e) => setForm({ ...form, siret: e.target.value })}
                  placeholder="12345678901234"
                  maxLength={14}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="edit-secteur">Secteur d&apos;activité</Label>
                <Input
                  id="edit-secteur"
                  value={form.secteur_activite}
                  onChange={(e) => setForm({ ...form, secteur_activite: e.target.value })}
                  placeholder="ex: Finance, Santé, Industrie..."
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="edit-adresse">Adresse</Label>
                <Input
                  id="edit-adresse"
                  value={form.adresse}
                  onChange={(e) => setForm({ ...form, adresse: e.target.value })}
                  placeholder="Adresse du siège"
                />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="edit-presentation">Présentation</Label>
              <Textarea
                id="edit-presentation"
                className="min-h-[80px]"
                value={form.presentation_desc}
                onChange={(e) => setForm({ ...form, presentation_desc: e.target.value })}
                placeholder="Description de l'entreprise..."
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="edit-contraintes">Contraintes réglementaires</Label>
              <Textarea
                id="edit-contraintes"
                className="min-h-[60px]"
                value={form.contraintes_reglementaires}
                onChange={(e) => setForm({ ...form, contraintes_reglementaires: e.target.value })}
                placeholder="RGPD, PCI-DSS, ISO 27001..."
              />
            </div>
            <Separator />
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <Label className="text-base font-semibold">Contacts</Label>
                <Button type="button" variant="outline" size="sm" onClick={addContact}>
                  <UserPlus data-icon="inline-start" />
                  Ajouter
                </Button>
              </div>
              {contacts.map((contact, index) => (
                <div key={contact._key || index} className="rounded-md border p-3 flex flex-col gap-3 relative">
                  <Button type="button" variant="ghost" size="icon" className="absolute top-1 right-1 size-6" onClick={() => removeContact(index)}>
                    <X />
                  </Button>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1">
                      <Label className="text-xs">Nom</Label>
                      <Input value={contact.nom} onChange={(e) => updateContact(index, "nom", e.target.value)} placeholder="Nom du contact" className="h-8 text-sm" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <Label className="text-xs">Rôle</Label>
                      <Input value={contact.role} onChange={(e) => updateContact(index, "role", e.target.value)} placeholder="DSI, RSSI, Admin..." className="h-8 text-sm" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1">
                      <Label className="text-xs">Email</Label>
                      <Input type="email" value={contact.email} onChange={(e) => updateContact(index, "email", e.target.value)} placeholder="email@exemple.com" className="h-8 text-sm" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <Label className="text-xs">Téléphone</Label>
                      <Input value={contact.telephone} onChange={(e) => updateContact(index, "telephone", e.target.value)} placeholder="+33 1 23 45 67 89" className="h-8 text-sm" />
                    </div>
                  </div>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <Checkbox checked={contact.is_main_contact} onCheckedChange={(checked) => updateContact(index, "is_main_contact", !!checked)} />
                    Contact principal
                  </label>
                </div>
              ))}
              {contacts.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-2">Aucun contact ajouté</p>
              )}
            </div>
          </div>

          {formError && (
            <p className="text-sm text-destructive">{formError}</p>
          )}

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

      {/* ── Dialog: Supprimer ── */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer l&apos;entreprise &laquo;{" "}
              <strong>{selected?.nom}</strong> &raquo; ? Cette action est
              irréversible et supprimera tous les sites, équipements et audits
              associés.
            </AlertDialogDescription>
          </AlertDialogHeader>

          {formError && (
            <p className="text-sm text-destructive">{formError}</p>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={handleDelete} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ── Dialog: Détail ── */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Building2 className="size-5" />
              {selected?.nom}
            </DialogTitle>
          </DialogHeader>

          {selected && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <InfoField label="Secteur d'activité" value={selected.secteur_activite} />
                <InfoField label="SIRET" value={selected.siret} mono />
                <InfoField label="Adresse" value={selected.adresse} />
                <InfoField
                  label="Créée le"
                  value={new Date(selected.created_at).toLocaleDateString("fr-FR", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                />
              </div>

              {selected.presentation_desc && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Présentation</p>
                  <p className="text-sm">{selected.presentation_desc}</p>
                </div>
              )}

              {selected.contraintes_reglementaires && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">
                    Contraintes réglementaires
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {selected.contraintes_reglementaires.split(",").map((c, i) => (
                      <Badge key={i} variant="outline">
                        {c.trim()}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <Separator />

              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-1">
                  <Users className="size-4" />
                  Contacts ({selected.contacts?.length || 0})
                </p>
                {selected.contacts?.length > 0 ? (
                  <div className="flex flex-col gap-2">
                    {selected.contacts.map((contact) => (
                      <div
                        key={contact.id}
                        className="flex items-center justify-between rounded-md border p-3"
                      >
                        <div>
                          <p className="text-sm font-medium flex items-center gap-2">
                            {contact.nom}
                            {contact.is_main_contact && (
                              <Badge variant="default" className="text-[10px] px-1 py-0 h-4">
                                Principal
                              </Badge>
                            )}
                          </p>
                          {contact.role && (
                            <p className="text-xs text-muted-foreground">{contact.role}</p>
                          )}
                        </div>
                        <div className="text-right text-sm">
                          {contact.email && <p>{contact.email}</p>}
                          {contact.telephone && (
                            <p className="text-muted-foreground">{contact.telephone}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Aucun contact enregistré
                  </p>
                )}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => router.push(`/sites?entreprise=${selected?.id}`)}>
              <MapPin data-icon="inline-start" />
              Voir les sites
            </Button>
            <Button
              onClick={() => {
                setDetailOpen(false);
                if (selected) openEdit(selected);
              }}
            >
              <Pencil data-icon="inline-start" />
              Modifier
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Small helper ──
function InfoField({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      <p className={cn("text-sm", mono && "font-mono")}>{value || "—"}</p>
    </div>
  );
}
