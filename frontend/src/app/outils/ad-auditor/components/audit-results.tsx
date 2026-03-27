"use client";

import React from "react";
import {
  Loader2,
  Trash2,
  Eye,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Users,
  Shield,
  Key,
  Server,
  ClipboardCheck,
  Info,
  Lock,
  FileText,
  ShieldCheck,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Skeleton } from "@/components/ui/skeleton";

import type {
  ADAuditResultSummary,
  ADAuditResultRead,
  ADAuditFinding,
} from "@/types";

// ── Constants ───────────────────────────────────────────────
const STATUS_LABELS: Record<string, string> = {
  running: "En cours",
  success: "Succès",
  failed: "Échec",
};

const STATUS_COLORS: Record<string, string> = {
  running: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  success: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
  medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  low: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  info: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

const FINDING_STATUS_ICONS: Record<string, React.ReactNode> = {
  compliant: <CheckCircle2 className="size-4 text-green-500" />,
  non_compliant: <XCircle className="size-4 text-red-500" />,
  partial: <AlertTriangle className="size-4 text-yellow-500" />,
  info: <Info className="size-4 text-blue-500" />,
};

// ── Props ────────────────────────────────────────────────────
export interface AuditResultsProps {
  audits: ADAuditResultSummary[];
  loadingAudits: boolean;
  handleViewDetail: (auditId: number) => void;
  handleOpenPrefill: (auditId: number, equipementId: number | null) => void;
  handleDelete: (auditId: number) => void;
  selectedAudit: ADAuditResultRead | null;
  detailOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

// ── Component ────────────────────────────────────────────────
export function AuditResults({
  audits,
  loadingAudits,
  handleViewDetail,
  handleOpenPrefill,
  handleDelete,
  selectedAudit,
  detailOpen,
  onOpenChange,
}: AuditResultsProps) {
  return (
    <>
      {/* Audit History Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Historique des audits</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingAudits ? (
            <div className="flex flex-col gap-2">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : audits.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              Aucun audit AD effectué pour le moment.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Cible</TableHead>
                  <TableHead>Domaine</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Durée</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {audits.map((audit) => (
                  <TableRow key={audit.id}>
                    <TableCell className="font-mono text-sm">#{audit.id}</TableCell>
                    <TableCell>{audit.target_host}:{audit.target_port}</TableCell>
                    <TableCell>{audit.domain_name || audit.domain || "—"}</TableCell>
                    <TableCell>
                      <Badge className={STATUS_COLORS[audit.status] || ""}>
                        {audit.status === "running" && <Loader2 className="size-3 animate-spin" />}
                        {STATUS_LABELS[audit.status] || audit.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {audit.summary ? (
                        <div className="flex items-center gap-2">
                          <Progress value={audit.summary.compliance_score} className="h-2 w-16" />
                          <span className="text-sm font-medium">
                            {Math.round(audit.summary.compliance_score)}%
                          </span>
                        </div>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      {audit.duration_seconds ? `${audit.duration_seconds}s` : "—"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {new Date(audit.created_at).toLocaleString("fr-FR")}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          disabled={audit.status === "running"}
                          onClick={() => handleViewDetail(audit.id)}
                          title="Voir le détail"
                        >
                          <Eye />
                        </Button>
                        {audit.status === "success" && audit.equipement_id && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleOpenPrefill(audit.id, audit.equipement_id)}
                            title="Pré-remplir un assessment"
                          >
                            <ClipboardCheck />
                          </Button>
                        )}
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="ghost" size="icon" title="Supprimer">
                              <Trash2 className="text-red-500" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Supprimer cet audit ?</AlertDialogTitle>
                              <AlertDialogDescription>
                                Cette action est irréversible.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Annuler</AlertDialogCancel>
                              <AlertDialogAction onClick={() => handleDelete(audit.id)}>
                                Supprimer
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ── Detail Dialog ── */}
      <Dialog open={detailOpen} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-y-auto">
          {selectedAudit && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <ShieldCheck className="size-5 text-cyan-500" />
                  Audit AD #{selectedAudit.id} — {selectedAudit.domain_name || selectedAudit.domain}
                </DialogTitle>
                <DialogDescription>
                  {selectedAudit.target_host}:{selectedAudit.target_port} ·
                  Durée : {selectedAudit.duration_seconds}s ·
                  {selectedAudit.domain_functional_level && ` Niveau fonctionnel : ${selectedAudit.domain_functional_level}`}
                </DialogDescription>
              </DialogHeader>

              {/* Summary */}
              {selectedAudit.summary && (
                <div className="grid gap-3 grid-cols-2 md:grid-cols-5 mb-4">
                  <SummaryCard
                    label="Contrôles"
                    value={selectedAudit.summary.total_controls}
                    icon={<Shield className="size-4" />}
                  />
                  <SummaryCard
                    label="Conformes"
                    value={selectedAudit.summary.compliant}
                    icon={<CheckCircle2 className="size-4 text-green-500" />}
                    color="text-green-600"
                  />
                  <SummaryCard
                    label="Non conformes"
                    value={selectedAudit.summary.non_compliant}
                    icon={<XCircle className="size-4 text-red-500" />}
                    color="text-red-600"
                  />
                  <SummaryCard
                    label="Partiels"
                    value={selectedAudit.summary.partial}
                    icon={<AlertTriangle className="size-4 text-yellow-500" />}
                    color="text-yellow-600"
                  />
                  <SummaryCard
                    label="Score"
                    value={`${Math.round(selectedAudit.summary.compliance_score)}%`}
                    icon={<Shield className="size-4 text-cyan-500" />}
                    color="text-cyan-600"
                  />
                </div>
              )}

              {/* Tabs */}
              <Tabs defaultValue="findings" className="w-full">
                <TabsList className="grid w-full grid-cols-5">
                  <TabsTrigger value="findings">Findings</TabsTrigger>
                  <TabsTrigger value="domain">Domaine</TabsTrigger>
                  <TabsTrigger value="users">Utilisateurs</TabsTrigger>
                  <TabsTrigger value="groups">Groupes</TabsTrigger>
                  <TabsTrigger value="policy">Politiques</TabsTrigger>
                </TabsList>

                {/* Findings Tab */}
                <TabsContent value="findings" className="flex flex-col gap-3">
                  {selectedAudit.findings && selectedAudit.findings.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[40px]"></TableHead>
                          <TableHead>Ref</TableHead>
                          <TableHead>Contrôle</TableHead>
                          <TableHead>Sévérité</TableHead>
                          <TableHead>Statut</TableHead>
                          <TableHead>Preuve</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedAudit.findings.map((f: ADAuditFinding, i: number) => (
                          <TableRow key={i}>
                            <TableCell>{FINDING_STATUS_ICONS[f.status] || null}</TableCell>
                            <TableCell className="font-mono text-xs">{f.control_ref}</TableCell>
                            <TableCell className="font-medium">{f.title}</TableCell>
                            <TableCell>
                              <Badge className={SEVERITY_COLORS[f.severity] || ""}>
                                {f.severity}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{f.status}</Badge>
                            </TableCell>
                            <TableCell className="text-sm max-w-xs truncate" title={f.evidence}>
                              {f.evidence || "—"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-muted-foreground text-center py-4">
                      Aucun finding disponible.
                    </p>
                  )}
                </TabsContent>

                {/* Domain Tab */}
                <TabsContent value="domain" className="flex flex-col gap-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <InfoBlock label="Nom du domaine" value={selectedAudit.domain_name} />
                    <InfoBlock label="Niveau fonctionnel" value={selectedAudit.domain_functional_level} />
                    <InfoBlock label="Forêt" value={selectedAudit.forest_functional_level} />
                    <InfoBlock label="LAPS déployé" value={selectedAudit.laps_deployed ? "Oui" : "Non"} />
                  </div>

                  {/* DC list */}
                  {selectedAudit.dc_list && selectedAudit.dc_list.length > 0 && (
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-1">
                        <Server className="size-4" /> Contrôleurs de domaine ({selectedAudit.dc_list.length})
                      </h4>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Nom</TableHead>
                            <TableHead>DN</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedAudit.dc_list.map((dc: Record<string, unknown>, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-mono text-sm">
                                {String(dc.name || dc.cn || "—")}
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {String(dc.dn || "—")}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  {/* GPO list */}
                  {selectedAudit.gpo_list && selectedAudit.gpo_list.length > 0 && (
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-1">
                        <FileText className="size-4" /> GPOs ({selectedAudit.gpo_list.length})
                      </h4>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Nom</TableHead>
                            <TableHead>DN</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedAudit.gpo_list.map((gpo: Record<string, unknown>, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-medium">
                                {String(gpo.name || gpo.displayName || "—")}
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {String(gpo.dn || "—")}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </TabsContent>

                {/* Users Tab */}
                <TabsContent value="users" className="flex flex-col gap-4">
                  <div className="grid gap-4 grid-cols-3">
                    <SummaryCard
                      label="Total"
                      value={selectedAudit.total_users ?? "—"}
                      icon={<Users className="size-4" />}
                    />
                    <SummaryCard
                      label="Actifs"
                      value={selectedAudit.enabled_users ?? "—"}
                      icon={<CheckCircle2 className="size-4 text-green-500" />}
                      color="text-green-600"
                    />
                    <SummaryCard
                      label="Désactivés"
                      value={selectedAudit.disabled_users ?? "—"}
                      icon={<XCircle className="size-4 text-red-500" />}
                      color="text-red-600"
                    />
                  </div>

                  {/* Never expire password */}
                  {selectedAudit.never_expire_password && selectedAudit.never_expire_password.length > 0 && (
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-1 text-orange-600">
                        <AlertTriangle className="size-4" /> Mot de passe n&apos;expire jamais ({selectedAudit.never_expire_password.length})
                      </h4>
                      <UserTable users={selectedAudit.never_expire_password} />
                    </div>
                  )}

                  {/* Inactive users */}
                  {selectedAudit.inactive_users && selectedAudit.inactive_users.length > 0 && (
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-1 text-yellow-600">
                        <Clock className="size-4" /> Utilisateurs inactifs ({selectedAudit.inactive_users.length})
                      </h4>
                      <UserTable users={selectedAudit.inactive_users} />
                    </div>
                  )}

                  {/* Never logged in */}
                  {selectedAudit.never_logged_in && selectedAudit.never_logged_in.length > 0 && (
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-1 text-gray-600">
                        <Info className="size-4" /> Jamais connectés ({selectedAudit.never_logged_in.length})
                      </h4>
                      <UserTable users={selectedAudit.never_logged_in} />
                    </div>
                  )}
                </TabsContent>

                {/* Groups Tab */}
                <TabsContent value="groups" className="flex flex-col gap-4">
                  <GroupSection
                    title="Domain Admins"
                    members={selectedAudit.domain_admins}
                    color="text-red-600"
                  />
                  <GroupSection
                    title="Enterprise Admins"
                    members={selectedAudit.enterprise_admins}
                    color="text-orange-600"
                  />
                  <GroupSection
                    title="Schema Admins"
                    members={selectedAudit.schema_admins}
                    color="text-yellow-600"
                  />

                  {selectedAudit.admin_account_status && (
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-1">
                        <Key className="size-4" /> Compte Administrateur Builtin
                      </h4>
                      <div className="grid gap-2 md:grid-cols-3">
                        <InfoBlock
                          label="Nom"
                          value={String(selectedAudit.admin_account_status.name || "Administrator")}
                        />
                        <InfoBlock
                          label="Activé"
                          value={selectedAudit.admin_account_status.enabled ? "Oui" : "Non"}
                        />
                        <InfoBlock
                          label="Renommé"
                          value={selectedAudit.admin_account_status.renamed ? "Oui" : "Non"}
                        />
                      </div>
                    </div>
                  )}
                </TabsContent>

                {/* Policy Tab */}
                <TabsContent value="policy" className="flex flex-col gap-4">
                  {selectedAudit.password_policy && (
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-1">
                        <Lock className="size-4" /> Politique de mots de passe par défaut
                      </h4>
                      <div className="grid gap-3 md:grid-cols-3">
                        {Object.entries(selectedAudit.password_policy).map(([k, v]) => (
                          <InfoBlock key={k} label={k} value={String(v ?? "—")} />
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedAudit.fine_grained_policies && selectedAudit.fine_grained_policies.length > 0 && (
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-1">
                        <Shield className="size-4" /> Fine-Grained Password Policies ({selectedAudit.fine_grained_policies.length})
                      </h4>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Nom</TableHead>
                            <TableHead>DN</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedAudit.fine_grained_policies.map((p: Record<string, unknown>, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-medium">
                                {String(p.name || p.cn || "—")}
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {String(p.dn || "—")}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

// ── Helper Components ──────────────────────────────────────────

function SummaryCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color?: string;
}) {
  return (
    <Card>
      <CardContent className="p-4 flex items-center gap-3">
        {icon}
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className={`text-lg font-bold ${color || ""}`}>{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function InfoBlock({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="bg-muted/50 rounded-lg p-3">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-sm font-medium">{value || "—"}</p>
    </div>
  );
}

function UserTable({ users }: { users: Record<string, unknown>[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Nom</TableHead>
          <TableHead>sAMAccountName</TableHead>
          <TableHead>DN</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {users.slice(0, 20).map((u, i) => (
          <TableRow key={i}>
            <TableCell className="font-medium">
              {String(u.name || u.cn || "—")}
            </TableCell>
            <TableCell className="font-mono text-sm">
              {String(u.sAMAccountName || "—")}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground truncate max-w-xs" title={String(u.dn || "")}>
              {String(u.dn || "—")}
            </TableCell>
          </TableRow>
        ))}
        {users.length > 20 && (
          <TableRow>
            <TableCell colSpan={3} className="text-center text-muted-foreground">
              ... et {users.length - 20} de plus
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

function GroupSection({
  title,
  members,
  color,
}: {
  title: string;
  members: Record<string, unknown>[] | null;
  color?: string;
}) {
  if (!members) return null;
  return (
    <div>
      <h4 className={`font-semibold mb-2 flex items-center gap-1 ${color || ""}`}>
        <Users className="size-4" /> {title} ({members.length})
      </h4>
      {members.length === 0 ? (
        <p className="text-muted-foreground text-sm">Aucun membre</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nom</TableHead>
              <TableHead>DN</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.map((m, i) => (
              <TableRow key={i}>
                <TableCell className="font-medium">
                  {String(m.name || m.cn || "—")}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {String(m.dn || "—")}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

// Re-export SummaryCard for use in prefill dialog (page.tsx)
export { SummaryCard };
