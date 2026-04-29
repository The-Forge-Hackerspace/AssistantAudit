"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  EQUIPEMENT_STATUS_LABELS,
  EQUIPEMENT_STATUS_VARIANTS,
  EQUIPEMENT_TYPE_ICONS,
  EQUIPEMENT_TYPE_LABELS,
} from "@/lib/constants";
import type { UseNetworkMap } from "@/hooks/useNetworkMap";
import type { PortDefinition, Site, VlanDefinition } from "@/types";

import { PortsTable, PresetButtons } from "./PortsEditor";

/**
 * Dialogue détaillé d'un équipement : informations, évaluations, gestion
 * des ports + assignation VLAN. Toute la logique vit dans `useNetworkMap`.
 */
interface EquipmentDetailDialogProps {
  detail: UseNetworkMap["detail"];
  sites: Site[];
  siteVlans: VlanDefinition[];
  selectedSiteId: number | null;
  onOpenVlanEditor: () => void;
  loadVlans: (siteId: number) => Promise<void>;
}

export function EquipmentDetailDialog({
  detail,
  sites,
  siteVlans,
  selectedSiteId,
  onOpenVlanEditor,
  loadVlans,
}: EquipmentDetailDialogProps) {
  const eq = detail.equipement;
  return (
    <Dialog open={detail.open} onOpenChange={detail.setOpen}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {eq &&
              (() => {
                const Icon = EQUIPEMENT_TYPE_ICONS[eq.type_equipement];
                return <Icon className="h-5 w-5 text-primary" />;
              })()}
            {eq?.hostname || eq?.ip_address || "Chargement…"}
          </DialogTitle>
        </DialogHeader>

        {detail.loading && (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        )}

        {eq && !detail.loading && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Type</p>
                <div className="flex items-center gap-2 mt-1">
                  {(() => {
                    const Icon = EQUIPEMENT_TYPE_ICONS[eq.type_equipement];
                    return <Icon className="h-4 w-4 text-primary" />;
                  })()}
                  <span className="text-sm font-medium">
                    {EQUIPEMENT_TYPE_LABELS[eq.type_equipement]}
                  </span>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Statut audit</p>
                <Badge variant={EQUIPEMENT_STATUS_VARIANTS[eq.status_audit]} className="mt-1">
                  {EQUIPEMENT_STATUS_LABELS[eq.status_audit]}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Adresse IP</p>
                <p className="text-sm mt-1 font-mono">{eq.ip_address}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Hostname</p>
                <p className="text-sm mt-1">{eq.hostname || "Non renseigné"}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Site</p>
                <Badge variant="outline" className="mt-1">
                  {sites.find((s) => s.id === eq.site_id)?.nom || `#${eq.site_id}`}
                </Badge>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Fabricant</p>
                <p className="text-sm mt-1">{eq.fabricant || "Non renseigné"}</p>
              </div>
            </div>

            <div>
              <p className="text-sm font-medium text-muted-foreground">OS détecté</p>
              <p className="text-sm mt-1">{eq.os_detected || "Non renseigné"}</p>
            </div>

            {eq.type_equipement === "reseau" && eq.firmware_version && (
              <div className="border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground mb-2">Détails réseau</p>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Firmware</p>
                  <p className="text-sm mt-1">{eq.firmware_version}</p>
                </div>
              </div>
            )}

            {eq.type_equipement === "serveur" && (
              <div className="border-t pt-4 space-y-3">
                <p className="text-sm font-medium text-muted-foreground">Détails serveur</p>
                {eq.os_version_detail && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">
                      Version OS détaillée
                    </p>
                    <p className="text-sm mt-1">{eq.os_version_detail}</p>
                  </div>
                )}
                {eq.modele_materiel && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Modèle matériel</p>
                    <p className="text-sm mt-1">{eq.modele_materiel}</p>
                  </div>
                )}
              </div>
            )}

            {eq.type_equipement === "firewall" && (
              <div className="border-t pt-4 space-y-3">
                <p className="text-sm font-medium text-muted-foreground">Détails firewall</p>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Licence</p>
                    <p className="text-sm mt-1">{eq.license_status || "—"}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Users VPN</p>
                    <p className="text-sm mt-1">{eq.vpn_users_count ?? 0}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Règles</p>
                    <p className="text-sm mt-1">{eq.rules_count ?? 0}</p>
                  </div>
                </div>
              </div>
            )}

            {eq.notes_audit && (
              <div className="border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground">Notes d&apos;audit</p>
                <p className="text-sm mt-1 whitespace-pre-wrap">{eq.notes_audit}</p>
              </div>
            )}

            {detail.assessments.length > 0 && (
              <div className="border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Évaluations ({detail.assessments.length})
                </p>
                <div className="space-y-2">
                  {detail.assessments.map((a) => (
                    <div
                      key={a.id}
                      className="flex items-center justify-between rounded-md border px-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-medium">{a.framework_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {a.created_at
                            ? new Date(a.created_at).toLocaleDateString("fr-FR")
                            : "—"}
                        </p>
                      </div>
                      <Badge variant="outline">#{a.id}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="border-t pt-4 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-muted-foreground">Configuration des ports</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (selectedSiteId) loadVlans(selectedSiteId);
                    onOpenVlanEditor();
                  }}
                >
                  Gérer les VLANs
                </Button>
              </div>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Préréglages</p>
                <div className="flex flex-wrap gap-2">
                  <PresetButtons typeEquipement={eq.type_equipement} onApply={detail.handleApplyPreset} />
                </div>
              </div>

              <PortsTable detail={detail} siteVlans={siteVlans} />

              <div className="flex items-end gap-2 border p-3 rounded-md bg-muted/50">
                <div className="grid grid-cols-4 gap-2 flex-1">
                  <div>
                    <Label className="text-xs">Nom</Label>
                    <Input
                      className="h-8"
                      value={detail.newPortName}
                      onChange={(e) => detail.setNewPortName(e.target.value)}
                      placeholder="ex: GigE 1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Type</Label>
                    <Select
                      value={detail.newPortType}
                      onValueChange={(v) => detail.setNewPortType(v as PortDefinition["type"])}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ethernet">Ethernet</SelectItem>
                        <SelectItem value="sfp">SFP</SelectItem>
                        <SelectItem value="sfp+">SFP+</SelectItem>
                        <SelectItem value="console">Console</SelectItem>
                        <SelectItem value="mgmt">Mgmt</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Vitesse</Label>
                    <Select value={detail.newPortSpeed} onValueChange={detail.setNewPortSpeed}>
                      <SelectTrigger className="h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="100 Mbps">100 Mbps</SelectItem>
                        <SelectItem value="1 Gbps">1 Gbps</SelectItem>
                        <SelectItem value="10 Gbps">10 Gbps</SelectItem>
                        <SelectItem value="25 Gbps">25 Gbps</SelectItem>
                        <SelectItem value="40 Gbps">40 Gbps</SelectItem>
                        <SelectItem value="100 Gbps">100 Gbps</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Rangée</Label>
                    <Select
                      value={String(detail.newPortRow)}
                      onValueChange={(v) => detail.setNewPortRow(Number(v))}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0">Haut (0)</SelectItem>
                        <SelectItem value="1">Bas (1)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <Button size="sm" className="h-8" onClick={detail.handleAddPort}>
                  Ajouter
                </Button>
              </div>
              <div className="flex justify-end pt-2">
                <Button onClick={detail.handleSavePorts} disabled={detail.savingPorts}>
                  Sauvegarder les ports
                </Button>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => detail.setOpen(false)}>
            Fermer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

