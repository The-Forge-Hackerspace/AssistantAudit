"use client";

import { MapPin, Pencil, Server } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Equipement, TypeEquipement } from "@/types";
import {
  EQUIPEMENT_TYPE_LABELS as TYPE_LABELS,
  EQUIPEMENT_TYPE_ICONS as TYPE_ICONS,
  EQUIPEMENT_STATUS_LABELS as STATUS_LABELS,
  EQUIPEMENT_STATUS_VARIANTS as STATUS_VARIANTS,
} from "@/lib/constants";

// ── Props ──

export interface EquipementDetailDialogProps {
  selected: Equipement | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  siteMap: Record<number, string>;
  onEdit: (equipement: Equipement) => void;
}

function TypeIcon({ type }: { type: TypeEquipement }) {
  const Icon = TYPE_ICONS[type] || Server;
  return <Icon className="size-4" />;
}

export function EquipementDetailDialog({
  selected,
  open,
  onOpenChange,
  siteMap,
  onEdit,
}: EquipementDetailDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {selected && <TypeIcon type={selected.type_equipement} />}
            {selected?.hostname || selected?.ip_address}
          </DialogTitle>
        </DialogHeader>

        {selected && (
          <div className="flex flex-col gap-4">
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
                  <MapPin className="size-3 mr-1" />
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
              <div className="border-t pt-4 flex flex-col gap-3">
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
              <div className="border-t pt-4 flex flex-col gap-3">
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
              onOpenChange(false);
              if (selected) onEdit(selected);
            }}
          >
            <Pencil data-icon="inline-start" />
            Modifier
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
