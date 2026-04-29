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
import type { Site, SiteConnection } from "@/types";

/**
 * Dialogue d'édition d'une connexion inter-site (vue multi-site) :
 * choix des deux sites, type, débit, description.
 */
interface SiteConnectionDialogProps {
  siteConnForm: UseNetworkMap["siteConnForm"];
  sites: Site[];
}

export function SiteConnectionDialog({ siteConnForm, sites }: SiteConnectionDialogProps) {
  const f = siteConnForm;
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
          <DialogTitle>
            {f.editingSiteConnId
              ? "Modifier la connexion inter-site"
              : "Nouvelle connexion inter-site"}
          </DialogTitle>
          <DialogDescription>
            {f.editingSiteConnId
              ? "Modifier les propriétés de la connexion"
              : "Relier deux sites de l'entreprise"}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Site source</Label>
            <Select
              value={f.sourceSiteId}
              onValueChange={f.setSourceSiteId}
              disabled={!!f.editingSiteConnId}
            >
              <SelectTrigger>
                <SelectValue placeholder="Choisir un site" />
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
          <div>
            <Label>Site cible</Label>
            <Select
              value={f.targetSiteId}
              onValueChange={f.setTargetSiteId}
              disabled={!!f.editingSiteConnId}
            >
              <SelectTrigger>
                <SelectValue placeholder="Choisir un site" />
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
          <div>
            <Label>Type de connexion</Label>
            <Select
              value={f.linkType}
              onValueChange={(value) => f.setLinkType(value as SiteConnection["link_type"])}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="wan">WAN</SelectItem>
                <SelectItem value="vpn">VPN</SelectItem>
                <SelectItem value="mpls">MPLS</SelectItem>
                <SelectItem value="sdwan">SD-WAN</SelectItem>
                <SelectItem value="other">Autre</SelectItem>
              </SelectContent>
            </Select>
          </div>
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
            <Label>Description</Label>
            <Input
              value={f.description}
              onChange={(e) => f.setDescription(e.target.value)}
              placeholder="IPsec tunnel, MPLS VRF…"
            />
          </div>
        </div>
        <DialogFooter className={f.editingSiteConnId ? "flex !justify-between" : ""}>
          {f.editingSiteConnId && (
            <Button variant="destructive" onClick={f.remove} disabled={f.saving}>
              Supprimer
            </Button>
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => f.setOpen(false)}>
              Annuler
            </Button>
            <Button onClick={f.save} disabled={f.saving}>
              {f.editingSiteConnId ? "Enregistrer" : "Créer la connexion"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
