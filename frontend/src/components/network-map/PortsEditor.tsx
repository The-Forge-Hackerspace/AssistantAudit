"use client";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
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
import type { UseNetworkMap } from "@/hooks/useNetworkMap";
import type { VlanDefinition } from "@/types";

/** Boutons de préréglages selon le type d'équipement. */
export function PresetButtons({
  typeEquipement,
  onApply,
}: {
  typeEquipement: string;
  onApply: (preset: string) => void;
}) {
  if (["reseau", "switch", "router", "access_point"].includes(typeEquipement)) {
    return (
      <>
        <Button variant="outline" size="sm" onClick={() => onApply("24×GigE+4×SFP+")}>
          24×GigE+4×SFP+
        </Button>
        <Button variant="outline" size="sm" onClick={() => onApply("48×GigE+4×SFP+")}>
          48×GigE+4×SFP+
        </Button>
        <Button variant="outline" size="sm" onClick={() => onApply("8×SFP+10G")}>
          8×SFP+10G
        </Button>
        <Button variant="outline" size="sm" onClick={() => onApply("4×SFP28-25G")}>
          4×SFP28-25G
        </Button>
      </>
    );
  }
  if (["serveur", "hyperviseur", "nas"].includes(typeEquipement)) {
    return (
      <>
        <Button variant="outline" size="sm" onClick={() => onApply("2×Ethernet")}>
          2×Ethernet
        </Button>
        <Button variant="outline" size="sm" onClick={() => onApply("4×Ethernet")}>
          4×Ethernet
        </Button>
        <Button variant="outline" size="sm" onClick={() => onApply("2×Ethernet+1×Mgmt")}>
          2×Ethernet+1×Mgmt
        </Button>
        <Button variant="outline" size="sm" onClick={() => onApply("4×Ethernet+1×Mgmt")}>
          4×Ethernet+1×Mgmt
        </Button>
      </>
    );
  }
  if (typeEquipement === "firewall") {
    return (
      <>
        <Button variant="outline" size="sm" onClick={() => onApply("4×Ethernet+1×Mgmt")}>
          4×Ethernet+1×Mgmt
        </Button>
        <Button variant="outline" size="sm" onClick={() => onApply("8×Ethernet+1×Mgmt")}>
          8×Ethernet+1×Mgmt
        </Button>
        <Button variant="outline" size="sm" onClick={() => onApply("2×Ethernet+2×SFP+")}>
          2×Ethernet+2×SFP+
        </Button>
      </>
    );
  }
  if (
    ["printer", "camera", "telephone", "iot", "cloud_gateway", "equipement"].includes(
      typeEquipement,
    )
  ) {
    return (
      <>
        <Button variant="outline" size="sm" onClick={() => onApply("1×Ethernet")}>
          1×Ethernet
        </Button>
        <Button variant="outline" size="sm" onClick={() => onApply("2×Ethernet")}>
          2×Ethernet
        </Button>
      </>
    );
  }
  return null;
}

/** Tableau d'édition des ports avec assignation VLAN natif/taggés. */
export function PortsTable({
  detail,
  siteVlans,
}: {
  detail: UseNetworkMap["detail"];
  siteVlans: VlanDefinition[];
}) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nom</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Vitesse</TableHead>
            <TableHead>Rangée</TableHead>
            <TableHead>VLAN Natif</TableHead>
            <TableHead>VLANs Taggés</TableHead>
            <TableHead className="w-10">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {detail.editingPorts.map((port, idx) => (
            <TableRow key={port.id}>
              <TableCell>{port.name}</TableCell>
              <TableCell>{port.type}</TableCell>
              <TableCell>{port.speed}</TableCell>
              <TableCell>{port.row === 0 ? "Haut (0)" : "Bas (1)"}</TableCell>
              <TableCell>
                <Select
                  value={port.untaggedVlan ? String(port.untaggedVlan) : "none"}
                  onValueChange={(val) => {
                    const newPorts = [...detail.editingPorts];
                    newPorts[idx].untaggedVlan = val === "none" ? null : parseInt(val);
                    detail.setEditingPorts(newPorts);
                  }}
                >
                  <SelectTrigger className="w-[120px] h-8">
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
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-2 max-w-[200px]">
                  {siteVlans.map((v) => (
                    <label
                      key={v.vlan_id}
                      className="flex items-center space-x-1 text-xs whitespace-nowrap"
                    >
                      <input
                        type="checkbox"
                        checked={(port.taggedVlans || []).includes(v.vlan_id)}
                        onChange={(e) => {
                          const newPorts = [...detail.editingPorts];
                          const current = newPorts[idx].taggedVlans || [];
                          if (e.target.checked) {
                            newPorts[idx].taggedVlans = [...current, v.vlan_id];
                          } else {
                            newPorts[idx].taggedVlans = current.filter((id) => id !== v.vlan_id);
                          }
                          detail.setEditingPorts(newPorts);
                        }}
                      />
                      <span>{v.vlan_id}</span>
                    </label>
                  ))}
                </div>
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive h-8 w-8 p-0"
                  onClick={() => detail.handleRemovePort(port.id)}
                >
                  &times;
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {detail.editingPorts.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground py-4">
                Aucun port configuré
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
