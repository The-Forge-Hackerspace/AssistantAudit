"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import type { UseNetworkMap } from "@/hooks/useNetworkMap";
import type { NetworkLinkCreate, PortDefinition } from "@/types";

/**
 * Dialogue d'édition d'un lien réseau intra-site (ajout / modification /
 * suppression). Lecture/écriture des champs déléguée au hook `useNetworkMap`
 * pour préserver le comportement de réinitialisation et de fermeture.
 */
interface LinkDialogProps {
  linkForm: UseNetworkMap["linkForm"];
  siteEquipements: { equipement_id: number; label: string; ip_address: string }[];
}

export function LinkDialog({ linkForm, siteEquipements }: LinkDialogProps) {
  const f = linkForm;
  return (
    <Dialog
      open={f.open}
      onOpenChange={(open) => {
        if (!open) f.reset();
        f.setOpen(open);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{f.editingLinkId ? "Modifier le lien" : "Nouveau lien"}</DialogTitle>
          <DialogDescription>
            {f.editingLinkId ? "Modifier les propriétés du lien" : "Relier deux équipements du site"}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Source</Label>
            <Select
              value={f.sourceEquipementId}
              onValueChange={f.setSourceEquipementId}
              disabled={!!f.editingLinkId}
            >
              <SelectTrigger>
                <SelectValue placeholder="Équipement source" />
              </SelectTrigger>
              <SelectContent>
                {siteEquipements.map((eq) => (
                  <SelectItem key={eq.equipement_id} value={String(eq.equipement_id)}>
                    {eq.label} ({eq.ip_address})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Cible</Label>
            <Select
              value={f.targetEquipementId}
              onValueChange={f.setTargetEquipementId}
              disabled={!!f.editingLinkId}
            >
              <SelectTrigger>
                <SelectValue placeholder="Équipement cible" />
              </SelectTrigger>
              <SelectContent>
                {siteEquipements.map((eq) => (
                  <SelectItem key={eq.equipement_id} value={String(eq.equipement_id)}>
                    {eq.label} ({eq.ip_address})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label>Interface source</Label>
              <Input
                value={f.sourceInterface}
                onChange={(e) => f.setSourceInterface(e.target.value)}
                placeholder="Gi0/1"
              />
            </div>
            <div>
              <Label>Interface cible</Label>
              <Input
                value={f.targetInterface}
                onChange={(e) => f.setTargetInterface(e.target.value)}
                placeholder="eth0"
              />
            </div>
          </div>
          {f.sourceEquipPorts.length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>Port source</Label>
                <PortSelect
                  value={f.selectedSourcePortId}
                  ports={f.sourceEquipPorts}
                  onResolve={(resolved) => {
                    f.setSelectedSourcePortId(resolved);
                    if (resolved) {
                      const port = f.sourceEquipPorts.find((p) => p.id === resolved);
                      if (port) f.setSourceInterface(port.id);
                    } else {
                      f.setSourceInterface("");
                    }
                  }}
                />
              </div>
              {f.targetEquipPorts.length > 0 && (
                <div>
                  <Label>Port cible</Label>
                  <PortSelect
                    value={f.selectedTargetPortId}
                    ports={f.targetEquipPorts}
                    onResolve={(resolved) => {
                      f.setSelectedTargetPortId(resolved);
                      if (resolved) {
                        const port = f.targetEquipPorts.find((p) => p.id === resolved);
                        if (port) f.setTargetInterface(port.id);
                      } else {
                        f.setTargetInterface("");
                      }
                    }}
                  />
                </div>
              )}
            </div>
          )}
          {f.sourceEquipPorts.length === 0 && f.targetEquipPorts.length > 0 && (
            <div>
              <Label>Port cible</Label>
              <PortSelect
                value={f.selectedTargetPortId}
                ports={f.targetEquipPorts}
                onResolve={(resolved) => {
                  f.setSelectedTargetPortId(resolved);
                  if (resolved) {
                    const port = f.targetEquipPorts.find((p) => p.id === resolved);
                    if (port) f.setTargetInterface(port.id);
                  } else {
                    f.setTargetInterface("");
                  }
                }}
              />
            </div>
          )}
          <div>
            <Label>Type de lien</Label>
            <Select
              value={f.linkType}
              onValueChange={(value) => f.setLinkType(value as NetworkLinkCreate["link_type"])}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ethernet">Ethernet</SelectItem>
                <SelectItem value="fiber">Fibre</SelectItem>
                <SelectItem value="wifi">Wi-Fi</SelectItem>
                <SelectItem value="vpn">VPN</SelectItem>
                <SelectItem value="wan">WAN</SelectItem>
                <SelectItem value="serial">Série</SelectItem>
                <SelectItem value="other">Autre</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label>Débit</Label>
              <Select value={f.bandwidth} onValueChange={f.setBandwidth}>
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="100 Mbps">100 Mbps</SelectItem>
                  <SelectItem value="1 Gbps">1 Gbps</SelectItem>
                  <SelectItem value="2.5 Gbps">2.5 Gbps</SelectItem>
                  <SelectItem value="5 Gbps">5 Gbps</SelectItem>
                  <SelectItem value="10 Gbps">10 Gbps</SelectItem>
                  <SelectItem value="25 Gbps">25 Gbps</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>VLAN</Label>
              <Input value={f.vlan} onChange={(e) => f.setVlan(e.target.value)} placeholder="VLAN 10" />
            </div>
          </div>
          <div>
            <Label>Segment réseau</Label>
            <Input
              value={f.networkSegment}
              onChange={(e) => f.setNetworkSegment(e.target.value)}
              placeholder="DMZ"
            />
          </div>
          <div>
            <Label>Description</Label>
            <Input
              value={f.linkDescription}
              onChange={(e) => f.setLinkDescription(e.target.value)}
              placeholder="LAGG trunk, uplink…"
            />
          </div>
        </div>
        <DialogFooter className={f.editingLinkId ? "flex !justify-between" : ""}>
          {f.editingLinkId && (
            <Button variant="destructive" onClick={f.remove} disabled={f.saving}>
              Supprimer
            </Button>
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => f.setOpen(false)}>
              Annuler
            </Button>
            <Button onClick={f.save} disabled={f.saving}>
              {f.editingLinkId ? "Enregistrer" : "Créer le lien"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Select factorisé pour les ports source/cible. */
function PortSelect({
  value,
  ports,
  onResolve,
}: {
  value: string;
  ports: PortDefinition[];
  onResolve: (resolved: string) => void;
}) {
  return (
    <Select
      value={value || "__none__"}
      onValueChange={(v) => onResolve(v === "__none__" ? "" : v)}
    >
      <SelectTrigger>
        <SelectValue placeholder="Aucun" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="__none__">Aucun</SelectItem>
        {ports.map((port) => (
          <SelectItem key={port.id} value={port.id}>
            {port.name} ({port.type}, {port.speed})
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}


