"use client";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { UseNetworkMap } from "@/hooks/useNetworkMap";
import type { VlanDefinition } from "@/types";

/**
 * Popover d'édition inline d'un port (VLAN natif + VLANs taggés) déclenché
 * depuis la vue détaillée. Positionné en absolu sur la carte.
 */
interface InlinePortEditorProps {
  inlinePort: UseNetworkMap["inlinePort"];
  siteVlans: VlanDefinition[];
}

export function InlinePortEditor({ inlinePort, siteVlans }: InlinePortEditorProps) {
  if (!inlinePort.port || !inlinePort.equipementId || !inlinePort.position) return null;
  const port = inlinePort.port;
  return (
    <>
      <div className="fixed inset-0 z-40" onClick={inlinePort.close} />
      <div
        className="fixed z-50 w-[320px] rounded-md border bg-card p-3 shadow-xl space-y-3"
        style={{ left: inlinePort.position.x + 8, top: inlinePort.position.y + 8 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <p className="text-sm font-medium">{port.name}</p>
          <p className="text-xs text-muted-foreground">
            VLAN natif: {port.untaggedVlan ?? "Aucun"}
            {" · "}
            VLANs taggés:{" "}
            {(port.taggedVlans || []).length > 0 ? port.taggedVlans?.join(", ") : "Aucun"}
          </p>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">VLAN natif</Label>
          <Select
            value={port.untaggedVlan ? String(port.untaggedVlan) : "none"}
            onValueChange={(value) => {
              inlinePort.setPort((prev) => {
                if (!prev) return prev;
                return {
                  ...prev,
                  untaggedVlan: value === "none" ? null : parseInt(value),
                };
              });
            }}
          >
            <SelectTrigger className="h-8">
              <SelectValue placeholder="Aucun" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Aucun</SelectItem>
              {siteVlans.map((v) => (
                <SelectItem key={v.vlan_id} value={String(v.vlan_id)}>
                  {v.vlan_id} - {v.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">VLANs taggés</Label>
          <div className="max-h-28 overflow-auto rounded border p-2 space-y-1">
            {siteVlans.length > 0 ? (
              siteVlans.map((v) => (
                <label key={v.vlan_id} className="flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={(port.taggedVlans || []).includes(v.vlan_id)}
                    onChange={(e) => {
                      inlinePort.setPort((prev) => {
                        if (!prev) return prev;
                        const current = prev.taggedVlans || [];
                        const taggedVlans = e.target.checked
                          ? [...current, v.vlan_id]
                          : current.filter((id) => id !== v.vlan_id);
                        return { ...prev, taggedVlans };
                      });
                    }}
                  />
                  <span>
                    {v.vlan_id} - {v.name}
                  </span>
                </label>
              ))
            ) : (
              <div className="text-xs text-muted-foreground">Aucun VLAN disponible</div>
            )}
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={inlinePort.close}>
            Annuler
          </Button>
          <Button size="sm" onClick={inlinePort.save}>
            Sauvegarder
          </Button>
        </div>
      </div>
    </>
  );
}
