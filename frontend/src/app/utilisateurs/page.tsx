"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Users2,
  Plus,
  Search,
  Pencil,
  Trash2,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  Power,
} from "lucide-react";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { usersApi } from "@/services/api";
import { useAuth } from "@/contexts/auth-context";
import type { User, RegisterRequest, UserUpdate } from "@/types";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { TableSkeleton } from "@/components/skeletons";

type UserRole = "admin" | "auditeur" | "lecteur";

const roleBadgeVariant = (role: string) => {
  switch (role) {
    case "admin":
      return "destructive" as const;
    case "auditeur":
      return "default" as const;
    default:
      return "secondary" as const;
  }
};

const roleLabel = (role: string) => {
  switch (role) {
    case "admin":
      return "Admin";
    case "auditeur":
      return "Auditeur";
    case "lecteur":
      return "Lecteur";
    default:
      return role;
  }
};

export default function UtilisateursPage() {
  const { user: currentUser } = useAuth();

  // List state
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  // Dialog state
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selected, setSelected] = useState<User | null>(null);
  const [saving, setSaving] = useState(false);

  // Create form state
  const [createForm, setCreateForm] = useState<RegisterRequest>({
    username: "",
    email: "",
    password: "",
    full_name: "",
    role: "auditeur",
  });
  const [showCreatePassword, setShowCreatePassword] = useState(false);

  // Edit form state
  const [editForm, setEditForm] = useState<UserUpdate>({});
  const [editPassword, setEditPassword] = useState("");
  const [showEditPassword, setShowEditPassword] = useState(false);

  const [formError, setFormError] = useState("");

  const PAGE_SIZE = 20;

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await usersApi.list(page, PAGE_SIZE);
      setUsers(res.items);
      setTotal(res.total);
      setPages(res.pages);
    } catch {
      toast.error("Impossible de charger les utilisateurs");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // Client-side search + role filter
  const filtered = users.filter((u) => {
    const matchesSearch =
      !search ||
      u.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === "all" || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  // Handlers
  const resetCreateForm = () => {
    setCreateForm({ username: "", email: "", password: "", full_name: "", role: "auditeur" });
    setShowCreatePassword(false);
    setFormError("");
  };

  const openCreate = () => {
    resetCreateForm();
    setCreateOpen(true);
  };

  const openEdit = (u: User) => {
    setSelected(u);
    setEditForm({
      email: u.email,
      full_name: u.full_name || "",
      role: u.role,
      is_active: u.is_active,
    });
    setEditPassword("");
    setShowEditPassword(false);
    setFormError("");
    setEditOpen(true);
  };

  const openDelete = (u: User) => {
    setSelected(u);
    setFormError("");
    setDeleteOpen(true);
  };

  const handleCreate = async () => {
    if (!createForm.full_name.trim()) {
      setFormError("Le nom complet est obligatoire");
      return;
    }
    if (!createForm.username.trim()) {
      setFormError("Le nom d'utilisateur est obligatoire");
      return;
    }
    if (!createForm.email.trim()) {
      setFormError("L'email est obligatoire");
      return;
    }
    if (!createForm.password || createForm.password.length < 8) {
      setFormError("Le mot de passe doit contenir au moins 8 caractères");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await usersApi.create(createForm);
      setCreateOpen(false);
      resetCreateForm();
      loadUsers();
      toast.success("Utilisateur créé avec succès");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la création");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!selected) return;
    setSaving(true);
    setFormError("");
    try {
      const payload: UserUpdate = { ...editForm };
      if (editPassword.trim()) {
        if (editPassword.length < 8) {
          setFormError("Le mot de passe doit contenir au moins 8 caractères");
          setSaving(false);
          return;
        }
        payload.password = editPassword;
      }
      await usersApi.update(selected.id, payload);
      setEditOpen(false);
      loadUsers();
      toast.success("Utilisateur mis à jour");
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
      await usersApi.delete(selected.id);
      setDeleteOpen(false);
      setSelected(null);
      loadUsers();
      toast.success("Utilisateur désactivé");
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFormError(err.response?.data?.detail || "Erreur lors de la désactivation");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (u: User) => {
    if (u.id === currentUser?.id) {
      toast.error("Vous ne pouvez pas vous désactiver vous-même");
      return;
    }
    try {
      await usersApi.update(u.id, { is_active: !u.is_active });
      loadUsers();
      toast.success(u.is_active ? "Utilisateur désactivé" : "Utilisateur réactivé");
    } catch {
      toast.error("Erreur lors de la modification du statut");
    }
  };

  // Guard: only admin
  if (currentUser?.role !== "admin") {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
        <Users2 className="size-12 mb-4 opacity-30" />
        <p className="text-lg font-medium">Accès réservé aux administrateurs</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Users2 className="size-6" />
            Utilisateurs
          </h1>
          <p className="text-muted-foreground">
            Gérez les comptes utilisateurs et leurs rôles
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus data-icon="inline-start" />
          Nouvel utilisateur
        </Button>
      </div>

      {/* Search + filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher par nom, username ou email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Tous les rôles" />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value="all">Tous les rôles</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
              <SelectItem value="auditeur">Auditeur</SelectItem>
              <SelectItem value="lecteur">Lecteur</SelectItem>
            </SelectGroup>
          </SelectContent>
        </Select>
        <Badge variant="secondary" className="text-sm">
          {total} utilisateur{total > 1 ? "s" : ""}
        </Badge>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton rows={5} cols={6} />
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <Users2 className="size-12 mb-4 opacity-30" />
              <p className="text-lg font-medium">Aucun utilisateur</p>
              <p className="text-sm">
                {search || roleFilter !== "all"
                  ? "Aucun résultat pour cette recherche"
                  : "Commencez par ajouter un utilisateur"}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom complet</TableHead>
                  <TableHead>Username</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Rôle</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Créé le</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">
                      {u.full_name || "—"}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {u.username}
                    </TableCell>
                    <TableCell className="text-sm">{u.email}</TableCell>
                    <TableCell>
                      <Badge variant={roleBadgeVariant(u.role)}>
                        {roleLabel(u.role)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.is_active ? "outline" : "secondary"}>
                        {u.is_active ? "Actif" : "Inactif"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(u.created_at).toLocaleDateString("fr-FR")}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => openEdit(u)}
                          title="Modifier"
                        >
                          <Pencil />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => handleToggleActive(u)}
                          title={u.is_active ? "Désactiver" : "Activer"}
                          disabled={u.id === currentUser?.id}
                        >
                          <Power className={cn(u.is_active ? "text-emerald-600" : "text-muted-foreground")} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-destructive hover:text-destructive"
                          onClick={() => openDelete(u)}
                          title="Désactiver"
                          disabled={u.id === currentUser?.id}
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

      {/* Dialog: Créer */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Nouvel utilisateur</DialogTitle>
            <DialogDescription>
              Créez un nouveau compte utilisateur
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="create-fullname">Nom complet *</Label>
              <Input
                id="create-fullname"
                value={createForm.full_name}
                onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                placeholder="Jean Dupont"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="create-username">Nom d&apos;utilisateur *</Label>
                <Input
                  id="create-username"
                  value={createForm.username}
                  onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })}
                  placeholder="jdupont"
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="create-email">Email *</Label>
                <Input
                  id="create-email"
                  type="email"
                  value={createForm.email}
                  onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                  placeholder="jean@exemple.com"
                />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="create-password">Mot de passe *</Label>
              <div className="relative">
                <Input
                  id="create-password"
                  type={showCreatePassword ? "text" : "password"}
                  value={createForm.password}
                  onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                  placeholder="Minimum 8 caractères"
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowCreatePassword(!showCreatePassword)}
                >
                  {showCreatePassword ? (
                    <EyeOff className="text-muted-foreground" />
                  ) : (
                    <Eye className="text-muted-foreground" />
                  )}
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="create-role">Rôle</Label>
              <Select
                value={createForm.role}
                onValueChange={(value) => setCreateForm({ ...createForm, role: value as UserRole })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="auditeur">Auditeur</SelectItem>
                    <SelectItem value="lecteur">Lecteur</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
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

      {/* Dialog: Modifier */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Modifier l&apos;utilisateur</DialogTitle>
            <DialogDescription>
              Modifiez les informations de &laquo; {selected?.full_name || selected?.username} &raquo;
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="edit-fullname">Nom complet</Label>
              <Input
                id="edit-fullname"
                value={editForm.full_name || ""}
                onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                placeholder="Jean Dupont"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="edit-email">Email</Label>
              <Input
                id="edit-email"
                type="email"
                value={editForm.email || ""}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                placeholder="jean@exemple.com"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="edit-password">
                Nouveau mot de passe{" "}
                <span className="text-muted-foreground font-normal">(laisser vide pour ne pas changer)</span>
              </Label>
              <div className="relative">
                <Input
                  id="edit-password"
                  type={showEditPassword ? "text" : "password"}
                  value={editPassword}
                  onChange={(e) => setEditPassword(e.target.value)}
                  placeholder="Minimum 8 caractères"
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowEditPassword(!showEditPassword)}
                >
                  {showEditPassword ? (
                    <EyeOff className="text-muted-foreground" />
                  ) : (
                    <Eye className="text-muted-foreground" />
                  )}
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="edit-role">Rôle</Label>
              <Select
                value={editForm.role || "auditeur"}
                onValueChange={(value) => setEditForm({ ...editForm, role: value as UserRole })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="auditeur">Auditeur</SelectItem>
                    <SelectItem value="lecteur">Lecteur</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
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

      {/* AlertDialog: Supprimer (désactiver) */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la désactivation</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir désactiver le compte de &laquo;{" "}
              <strong>{selected?.full_name || selected?.username}</strong> &raquo; ?
              L&apos;utilisateur ne pourra plus se connecter mais ses données seront conservées.
            </AlertDialogDescription>
          </AlertDialogHeader>

          {formError && (
            <p className="text-sm text-destructive">{formError}</p>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={handleDelete} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />}
              Désactiver
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
