"use client";

import { useState } from "react";
import {
  Settings,
  Plus,
  Pencil,
  Trash2,
  Eye,
  EyeOff,
  ChevronDown,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectGroup,
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
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { OradadConfig, DomainEntry } from "@/types";

// ── Constants ──
const LEVEL_LABELS: Record<string, string> = {
  "1": "Minimal",
  "2": "Standard",
  "3": "Détaillé",
  "4": "Complet",
};

const CONFIDENTIAL_LABELS: Record<string, string> = {
  "0": "Ne pas collecter",
  "1": "Avec limites",
  "2": "Sans limites",
};

const EMPTY_DOMAIN: DomainEntry = {
  server: "",
  port: 389,
  domain_name: "",
  username: "",
  user_domain: "",
  password: "",
};

// ── DomainRow sub-component ──
function DomainRow({
  domain,
  index,
  onChange,
  onRemove,
  canRemove,
}: {
  domain: DomainEntry;
  index: number;
  onChange: (index: number, field: keyof DomainEntry, value: string | number) => void;
  onRemove: (index: number) => void;
  canRemove: boolean;
}) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="rounded-lg border p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Domaine {index + 1}</span>
        {canRemove && (
          <Button variant="ghost" size="sm" className="text-destructive" onClick={() => onRemove(index)}>
            <Trash2 data-icon="inline-start" />
            Retirer
          </Button>
        )}
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="flex flex-col gap-1">
          <Label htmlFor={`domain-server-${index}`} className="text-xs">Serveur / IP du DC *</Label>
          <Input
            id={`domain-server-${index}`}
            placeholder="192.168.1.10 ou dc01.client.local"
            value={domain.server}
            onChange={(e) => onChange(index, "server", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor={`domain-port-${index}`} className="text-xs">Port LDAP</Label>
          <Input
            id={`domain-port-${index}`}
            type="number"
            min={1}
            max={65535}
            placeholder="389"
            value={domain.port}
            onChange={(e) => onChange(index, "port", Number(e.target.value) || 389)}
          />
        </div>
        <div className="flex flex-col gap-1 md:col-span-2">
          <Label htmlFor={`domain-name-${index}`} className="text-xs">Nom du domaine *</Label>
          <Input
            id={`domain-name-${index}`}
            placeholder="client.local"
            value={domain.domain_name}
            onChange={(e) => onChange(index, "domain_name", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor={`domain-username-${index}`} className="text-xs">Nom d&apos;utilisateur *</Label>
          <Input
            id={`domain-username-${index}`}
            placeholder="auditeur"
            value={domain.username}
            onChange={(e) => onChange(index, "username", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor={`domain-userdomain-${index}`} className="text-xs">Domaine utilisateur *</Label>
          <Input
            id={`domain-userdomain-${index}`}
            placeholder="CLIENT"
            value={domain.user_domain}
            onChange={(e) => onChange(index, "user_domain", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1 md:col-span-2">
          <Label htmlFor={`domain-password-${index}`} className="text-xs">Mot de passe *</Label>
          <div className="flex gap-2">
            <Input
              id={`domain-password-${index}`}
              type={showPassword ? "text" : "password"}
              placeholder="••••••"
              value={domain.password}
              onChange={(e) => onChange(index, "password", e.target.value)}
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
            >
              {showPassword ? <EyeOff data-icon /> : <Eye data-icon />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Props ──
export interface ConfigProfilesProps {
  configs: OradadConfig[];
  loadingConfigs: boolean;
  showConfigDialog: boolean;
  setShowConfigDialog: (open: boolean) => void;
  editingConfig: OradadConfig | null;
  deleteConfigTarget: OradadConfig | null;
  setDeleteConfigTarget: (config: OradadConfig | null) => void;
  savingConfig: boolean;
  // Config form fields
  cfgName: string;
  setCfgName: (v: string) => void;
  cfgAutoGetDomain: boolean;
  setCfgAutoGetDomain: (v: boolean) => void;
  cfgAutoGetTrusts: boolean;
  setCfgAutoGetTrusts: (v: boolean) => void;
  cfgLevel: string;
  setCfgLevel: (v: string) => void;
  cfgConfidential: string;
  setCfgConfidential: (v: string) => void;
  cfgProcessSysvol: boolean;
  setCfgProcessSysvol: (v: boolean) => void;
  cfgSysvolFilter: string;
  setCfgSysvolFilter: (v: string) => void;
  cfgOutputFiles: boolean;
  setCfgOutputFiles: (v: boolean) => void;
  cfgOutputMla: boolean;
  setCfgOutputMla: (v: boolean) => void;
  cfgSleepTime: string;
  setCfgSleepTime: (v: string) => void;
  cfgShowAdvanced: boolean;
  setCfgShowAdvanced: (v: boolean) => void;
  cfgDomains: (DomainEntry & { _key: number })[];
  // Config CRUD handlers
  openNewConfig: () => void;
  openEditConfig: (config: OradadConfig) => void;
  handleSaveConfig: () => void;
  handleDeleteConfig: () => void;
  handleDomainChange: (index: number, field: keyof DomainEntry, value: string | number) => void;
  handleAddDomain: () => void;
  handleRemoveDomain: (index: number) => void;
}

export function ConfigProfiles({
  configs,
  loadingConfigs,
  showConfigDialog,
  setShowConfigDialog,
  editingConfig,
  deleteConfigTarget,
  setDeleteConfigTarget,
  savingConfig,
  cfgName,
  setCfgName,
  cfgAutoGetDomain,
  setCfgAutoGetDomain,
  cfgAutoGetTrusts,
  setCfgAutoGetTrusts,
  cfgLevel,
  setCfgLevel,
  cfgConfidential,
  setCfgConfidential,
  cfgProcessSysvol,
  setCfgProcessSysvol,
  cfgSysvolFilter,
  setCfgSysvolFilter,
  cfgOutputFiles,
  setCfgOutputFiles,
  cfgOutputMla,
  setCfgOutputMla,
  cfgSleepTime,
  setCfgSleepTime,
  cfgShowAdvanced,
  setCfgShowAdvanced,
  cfgDomains,
  openNewConfig,
  openEditConfig,
  handleSaveConfig,
  handleDeleteConfig,
  handleDomainChange,
  handleAddDomain,
  handleRemoveDomain,
}: ConfigProfilesProps) {
  return (
    <>
      {/* ── Config profiles section ── */}
      <Accordion type="single" collapsible>
        <AccordionItem value="configs" className="rounded-lg border">
          <AccordionTrigger className="px-6 hover:no-underline">
            <div className="flex items-center gap-2">
              <Settings className="size-5" />
              <span className="font-semibold">Profils de configuration</span>
              <Badge variant="secondary" className="text-xs">{configs.length}</Badge>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-4">
            {loadingConfigs ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <div className="flex flex-col gap-3">
                <div className="flex justify-end">
                  <Button size="sm" onClick={openNewConfig}>
                    <Plus data-icon="inline-start" />
                    Nouveau profil
                  </Button>
                </div>
                {configs.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Aucun profil. Créez un profil de configuration avant de lancer une collecte.
                  </p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Nom</TableHead>
                        <TableHead>Niveau</TableHead>
                        <TableHead>Confidentiel</TableHead>
                        <TableHead>Domaines</TableHead>
                        <TableHead>SYSVOL</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {configs.map((cfg) => (
                        <TableRow key={cfg.id}>
                          <TableCell className="font-medium">{cfg.name}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{LEVEL_LABELS[String(cfg.level)] || cfg.level}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{CONFIDENTIAL_LABELS[String(cfg.confidential)] || cfg.confidential}</Badge>
                          </TableCell>
                          <TableCell>
                            {cfg.auto_get_domain ? (
                              <Badge variant="secondary">Auto</Badge>
                            ) : cfg.explicit_domains ? (
                              <Badge variant="outline">{cfg.explicit_domains.length} domaine(s)</Badge>
                            ) : (
                              <span className="text-sm text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell>{cfg.process_sysvol ? "Oui" : "Non"}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Button variant="ghost" size="sm" onClick={() => openEditConfig(cfg)}>
                                <Pencil data-icon="inline-start" />
                                Modifier
                              </Button>
                              <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setDeleteConfigTarget(cfg)}>
                                <Trash2 data-icon="inline-start" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            )}
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* ── Config dialog ── */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingConfig ? "Modifier le profil" : "Nouveau profil"}</DialogTitle>
            <DialogDescription>
              Configurez les paramètres de collecte ORADAD.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="cfg-name">Nom du profil *</Label>
              <Input id="cfg-name" value={cfgName} onChange={(e) => setCfgName(e.target.value)} placeholder="ex : Audit Client X" />
            </div>

            <Separator />

            {/* Auto-detect toggles */}
            <div className="flex items-center justify-between">
              <div className="flex flex-col gap-0.5">
                <Label htmlFor="cfg-auto-domain">Détection automatique du domaine</Label>
                <span className="text-xs text-muted-foreground">
                  Activer uniquement si l&apos;agent est joint au domaine cible
                </span>
              </div>
              <Switch id="cfg-auto-domain" checked={cfgAutoGetDomain} onCheckedChange={setCfgAutoGetDomain} />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex flex-col gap-0.5">
                <Label htmlFor="cfg-auto-trusts">Détection automatique des trusts</Label>
                <span className="text-xs text-muted-foreground">
                  Activer uniquement si l&apos;agent est joint au domaine cible
                </span>
              </div>
              <Switch id="cfg-auto-trusts" checked={cfgAutoGetTrusts} onCheckedChange={setCfgAutoGetTrusts} />
            </div>

            {/* ── Target domains — central section, shown when auto-detect is OFF ── */}
            {!cfgAutoGetDomain && (
              <>
                <Separator />
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label className="text-base font-semibold">Domaines cibles *</Label>
                      <p className="text-xs text-muted-foreground">
                        Renseignez les contrôleurs de domaine et les identifiants de connexion.
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleAddDomain}>
                      <Plus data-icon="inline-start" />
                      Ajouter un domaine
                    </Button>
                  </div>
                  {cfgDomains.map((d, i) => (
                    <DomainRow
                      key={d._key}
                      domain={d}
                      index={i}
                      onChange={handleDomainChange}
                      onRemove={handleRemoveDomain}
                      canRemove={cfgDomains.length > 1}
                    />
                  ))}
                </div>
              </>
            )}

            <Separator />

            {/* Collection parameters */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="cfg-level">Niveau de collecte</Label>
              <Select value={cfgLevel} onValueChange={setCfgLevel}>
                <SelectTrigger id="cfg-level"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="1">1 — Minimal</SelectItem>
                    <SelectItem value="2">2 — Standard</SelectItem>
                    <SelectItem value="3">3 — Détaillé</SelectItem>
                    <SelectItem value="4">4 — Complet</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="cfg-confidential">Attributs confidentiels</Label>
              <Select value={cfgConfidential} onValueChange={setCfgConfidential}>
                <SelectTrigger id="cfg-confidential"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="0">Ne pas collecter</SelectItem>
                    <SelectItem value="1">Avec limites</SelectItem>
                    <SelectItem value="2">Sans limites</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="cfg-sysvol">Collecter le SYSVOL</Label>
              <Switch id="cfg-sysvol" checked={cfgProcessSysvol} onCheckedChange={setCfgProcessSysvol} />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="cfg-output-files">Sortie fichiers texte</Label>
              <Switch id="cfg-output-files" checked={cfgOutputFiles} onCheckedChange={setCfgOutputFiles} />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="cfg-output-mla">Sortie archive MLA</Label>
              <Switch id="cfg-output-mla" checked={cfgOutputMla} onCheckedChange={setCfgOutputMla} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="cfg-sleep">Délai entre requêtes (secondes)</Label>
              <Input id="cfg-sleep" type="number" min="0" value={cfgSleepTime} onChange={(e) => setCfgSleepTime(e.target.value)} />
            </div>

            {/* Advanced */}
            <Button variant="ghost" size="sm" className="self-start" onClick={() => setCfgShowAdvanced(!cfgShowAdvanced)}>
              <ChevronDown data-icon="inline-start" className={cn("transition-transform", cfgShowAdvanced && "rotate-180")} />
              Avancé
            </Button>
            {cfgShowAdvanced && (
              <div className="flex flex-col gap-2">
                <Label>Filtre SYSVOL</Label>
                <Textarea
                  rows={4}
                  value={cfgSysvolFilter}
                  onChange={(e) => setCfgSysvolFilter(e.target.value)}
                  placeholder="*.bat;*.vbs;*.ps1;..."
                  className="font-mono text-xs"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>Annuler</Button>
            <Button onClick={handleSaveConfig} disabled={savingConfig}>
              {savingConfig && <Loader2 data-icon="inline-start" className="animate-spin" />}
              {editingConfig ? "Enregistrer" : "Créer"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete config confirmation ── */}
      <AlertDialog open={!!deleteConfigTarget} onOpenChange={(open) => !open && setDeleteConfigTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer le profil ?</AlertDialogTitle>
            <AlertDialogDescription>
              Le profil « {deleteConfigTarget?.name} » sera supprimé définitivement.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfig}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
