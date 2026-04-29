"use client";

import { ChevronDown, ChevronUp } from "lucide-react";

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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { UseNetworkMap } from "@/hooks/useNetworkMap";
import type { VlanDefinition } from "@/types";

/**
 * Panneau dépliable listant les VLANs d'un site (visible sous la vue détaillée).
 */
interface VlanPanelProps {
  siteVlans: VlanDefinition[];
  expanded: boolean;
  setExpanded: (v: boolean) => void;
  onOpenEditor: () => void;
}

export function VlanPanel({ siteVlans, expanded, setExpanded, onOpenEditor }: VlanPanelProps) {
  return (
    <div className="rounded-md border bg-card">
      <button
        type="button"
        className="w-full flex items-center justify-between px-3 py-2 text-sm"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="font-medium">VLANs ({siteVlans.length})</span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
      {expanded && (
        <div className="border-t px-3 py-3 space-y-3">
          {siteVlans.length > 0 ? (
            <div className="space-y-2">
              {siteVlans.map((v) => (
                <div
                  key={v.id}
                  className="grid grid-cols-[16px_56px_minmax(120px,1fr)_minmax(120px,1fr)] gap-3 items-start text-xs"
                >
                  <div
                    className="w-4 h-4 rounded-sm border"
                    style={{ backgroundColor: v.color }}
                  />
                  <span className="font-mono font-bold leading-4">{v.vlan_id}</span>
                  <div>
                    <div className="font-medium text-foreground">{v.name}</div>
                    {v.description && (
                      <div className="text-muted-foreground">{v.description}</div>
                    )}
                  </div>
                  <div className="font-mono text-muted-foreground">{v.subnet || "—"}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">Aucun VLAN défini pour ce site.</div>
          )}
          <div className="pt-1">
            <Button variant="outline" size="sm" onClick={onOpenEditor}>
              Gérer les VLANs
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Dialogue de gestion des VLANs : table + formulaire d'ajout.
 */
interface VlanEditorDialogProps {
  vlanEditor: UseNetworkMap["vlanEditor"];
  siteVlans: VlanDefinition[];
}

export function VlanEditorDialog({ vlanEditor, siteVlans }: VlanEditorDialogProps) {
  const v = vlanEditor;
  return (
    <Dialog open={v.open} onOpenChange={v.setOpen}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Gestion des VLANs</DialogTitle>
          <DialogDescription>
            Définir les VLANs disponibles pour ce site. Ils pourront être assignés aux ports des
            équipements.
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">Couleur</TableHead>
                <TableHead>ID</TableHead>
                <TableHead>Nom</TableHead>
                <TableHead>Sous-réseau</TableHead>
                <TableHead className="w-10">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {siteVlans.map((vlanItem) => (
                <TableRow key={vlanItem.id}>
                  <TableCell>
                    <div
                      className="w-5 h-5 rounded border"
                      style={{ backgroundColor: vlanItem.color }}
                    />
                  </TableCell>
                  <TableCell className="font-mono">{vlanItem.vlan_id}</TableCell>
                  <TableCell>{vlanItem.name}</TableCell>
                  <TableCell className="font-mono text-xs">{vlanItem.subnet || "—"}</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive h-8 w-8 p-0"
                      onClick={() => v.remove(vlanItem.id)}
                    >
                      &times;
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {siteVlans.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-4">
                    Aucun VLAN défini
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        <div className="flex items-end gap-2 border p-3 rounded-md bg-muted/50">
          <div className="grid grid-cols-5 gap-2 flex-1">
            <div>
              <Label className="text-xs">ID VLAN</Label>
              <Input
                className="h-8"
                type="number"
                min={1}
                max={4094}
                value={v.newVlanId}
                onChange={(e) => v.setNewVlanId(e.target.value)}
                placeholder="10"
              />
            </div>
            <div>
              <Label className="text-xs">Nom</Label>
              <Input
                className="h-8"
                value={v.newVlanName}
                onChange={(e) => v.setNewVlanName(e.target.value)}
                placeholder="Management"
              />
            </div>
            <div>
              <Label className="text-xs">Sous-réseau</Label>
              <Input
                className="h-8"
                value={v.newVlanSubnet}
                onChange={(e) => v.setNewVlanSubnet(e.target.value)}
                placeholder="192.168.10.0/24"
              />
            </div>
            <div>
              <Label className="text-xs">Couleur</Label>
              <input
                type="color"
                className="h-8 w-full rounded border cursor-pointer"
                value={v.newVlanColor}
                onChange={(e) => v.setNewVlanColor(e.target.value)}
              />
            </div>
            <div>
              <Label className="text-xs">Description</Label>
              <Input
                className="h-8"
                value={v.newVlanDescription}
                onChange={(e) => v.setNewVlanDescription(e.target.value)}
                placeholder="Optionnel"
              />
            </div>
          </div>
          <Button
            size="sm"
            className="h-8"
            onClick={v.create}
            disabled={v.saving || !v.newVlanId || !v.newVlanName}
          >
            Ajouter
          </Button>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => v.setOpen(false)}>
            Fermer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Dialogue de confirmation pour le remplacement des ports via préréglage.
 */
interface PortPresetConfirmDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  currentPortsCount: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export function PortPresetConfirmDialog({
  open,
  setOpen,
  currentPortsCount,
  onConfirm,
  onCancel,
}: PortPresetConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Remplacer les ports existants ?</DialogTitle>
          <DialogDescription>
            Vous êtes sur le point d&apos;appliquer un préréglage. Cela effacera les{" "}
            {currentPortsCount} ports actuellement configurés. Voulez-vous continuer ?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Annuler
          </Button>
          <Button variant="destructive" onClick={onConfirm}>
            Remplacer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
