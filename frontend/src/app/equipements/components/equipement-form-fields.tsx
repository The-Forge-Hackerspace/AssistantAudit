"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Site, TypeEquipement, EquipementCreate } from "@/types";
import {
  EQUIPEMENT_TYPE_LABELS as TYPE_LABELS,
} from "@/lib/constants";

// ── Props ──

export interface EquipementFormFieldsProps {
  /** "create" shows site + type selectors and editable IP; "edit" shows read-only IP/type */
  mode: "create" | "edit";
  form: EquipementCreate & { notes_audit?: string };
  setForm: React.Dispatch<React.SetStateAction<EquipementCreate & { notes_audit?: string }>>;
  sites: Site[];
  formError: string;
  /** Only needed in edit mode — the current type and IP for the read-only header */
  selectedIp?: string;
  selectedType?: TypeEquipement;
  /** HTML id prefix to avoid duplicate ids between create/edit dialogs */
  idPrefix: string;
}

export function EquipementFormFields({
  mode,
  form,
  setForm,
  sites,
  formError,
  selectedIp,
  selectedType,
  idPrefix,
}: EquipementFormFieldsProps) {
  const typeForConditionalFields = mode === "edit" ? selectedType : form.type_equipement;

  return (
    <div className="flex flex-col gap-4">
      {/* ── Create-only: Site + Type selectors ── */}
      {mode === "create" && (
        <>
          <div className="flex flex-col gap-2">
            <Label>Site *</Label>
            <Select
              value={form.site_id ? String(form.site_id) : ""}
              onValueChange={(v) => setForm(prev => ({ ...prev, site_id: Number(v) }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner un site" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {sites.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.nom}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <Label>Type d&apos;équipement *</Label>
            <Select
              value={form.type_equipement}
              onValueChange={(v) =>
                setForm(prev => ({ ...prev, type_equipement: v as TypeEquipement }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {Object.entries(TYPE_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
        </>
      )}

      {/* ── Edit-only: read-only IP + type ── */}
      {mode === "edit" && (
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <Label>Adresse IP</Label>
            <Input value={selectedIp || ""} disabled className="font-mono" />
            <p className="text-xs text-muted-foreground">Non modifiable</p>
          </div>
          <div className="flex flex-col gap-2">
            <Label>Type</Label>
            <Input value={TYPE_LABELS[selectedType || "equipement"]} disabled />
          </div>
        </div>
      )}

      {/* ── Common: IP + Hostname (create) / Hostname + Fabricant (edit) ── */}
      {mode === "create" && (
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor={`${idPrefix}-ip`}>Adresse IP *</Label>
            <Input
              id={`${idPrefix}-ip`}
              value={form.ip_address}
              onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, ip_address: value })); }}
              placeholder="192.168.1.1"
              className="font-mono"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`${idPrefix}-hostname`}>Hostname</Label>
            <Input
              id={`${idPrefix}-hostname`}
              value={form.hostname}
              onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, hostname: value })); }}
              placeholder="SRV-DC01"
            />
          </div>
        </div>
      )}

      {mode === "create" && (
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor={`${idPrefix}-fabricant`}>Fabricant</Label>
            <Input
              id={`${idPrefix}-fabricant`}
              value={form.fabricant}
              onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, fabricant: value })); }}
              placeholder="Dell, HP, Fortinet..."
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`${idPrefix}-os`}>OS détecté</Label>
            <Input
              id={`${idPrefix}-os`}
              value={form.os_detected}
              onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, os_detected: value })); }}
              placeholder="Windows Server 2022, FortiOS 7.4..."
            />
          </div>
        </div>
      )}

      {mode === "edit" && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor={`${idPrefix}-hostname`}>Hostname</Label>
              <Input
                id={`${idPrefix}-hostname`}
                value={form.hostname}
                onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, hostname: value })); }}
                placeholder="SRV-DC01"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor={`${idPrefix}-fabricant`}>Fabricant</Label>
              <Input
                id={`${idPrefix}-fabricant`}
                value={form.fabricant}
                onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, fabricant: value })); }}
                placeholder="Dell, HP..."
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor={`${idPrefix}-os`}>OS détecté</Label>
            <Input
              id={`${idPrefix}-os`}
              value={form.os_detected}
              onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, os_detected: value })); }}
              placeholder="Windows Server 2022..."
            />
          </div>
        </>
      )}

      {/* ── Type-specific fields ── */}
      {typeForConditionalFields === "reseau" && (
        <div className="flex flex-col gap-2 border-t pt-4">
          <p className="text-sm font-medium text-muted-foreground">Champs réseau</p>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`${idPrefix}-firmware`}>Version firmware</Label>
            <Input
              id={`${idPrefix}-firmware`}
              value={(form as Record<string, unknown>).firmware_version as string || ""}
              onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, firmware_version: value })); }}
              placeholder={mode === "create" ? "ex: IOS 15.2, ArubaOS 8.10..." : undefined}
            />
          </div>
        </div>
      )}

      {typeForConditionalFields === "serveur" && (
        <div className="flex flex-col gap-4 border-t pt-4">
          <p className="text-sm font-medium text-muted-foreground">Champs serveur</p>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`${idPrefix}-os-detail`}>Détail version OS</Label>
            <Input
              id={`${idPrefix}-os-detail`}
              value={(form as Record<string, unknown>).os_version_detail as string || ""}
              onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, os_version_detail: value })); }}
              placeholder={mode === "create" ? "ex: Windows Server 2022 Datacenter Build 20348" : undefined}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`${idPrefix}-modele`}>Modèle matériel</Label>
            <Input
              id={`${idPrefix}-modele`}
              value={(form as Record<string, unknown>).modele_materiel as string || ""}
              onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, modele_materiel: value })); }}
              placeholder={mode === "create" ? "ex: Dell PowerEdge R740" : undefined}
            />
          </div>
        </div>
      )}

      {typeForConditionalFields === "firewall" && (
        <div className="flex flex-col gap-4 border-t pt-4">
          <p className="text-sm font-medium text-muted-foreground">Champs firewall</p>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`${idPrefix}-license`}>Statut licence</Label>
            <Input
              id={`${idPrefix}-license`}
              value={(form as Record<string, unknown>).license_status as string || ""}
              onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, license_status: value })); }}
              placeholder={mode === "create" ? "ex: Active, Expired, Trial..." : undefined}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor={`${idPrefix}-vpn`}>Utilisateurs VPN</Label>
              <Input
                id={`${idPrefix}-vpn`}
                type="number"
                value={(form as Record<string, unknown>).vpn_users_count as number ?? 0}
                onChange={(e) =>
                  { const value = parseInt(e.target.value) || 0; setForm(prev => ({ ...prev, vpn_users_count: value })); }
                }
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor={`${idPrefix}-rules`}>Nombre de règles</Label>
              <Input
                id={`${idPrefix}-rules`}
                type="number"
                value={(form as Record<string, unknown>).rules_count as number ?? 0}
                onChange={(e) =>
                  { const value = parseInt(e.target.value) || 0; setForm(prev => ({ ...prev, rules_count: value })); }
                }
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Notes d'audit ── */}
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${idPrefix}-notes`}>Notes d&apos;audit</Label>
        <Textarea
          id={`${idPrefix}-notes`}
          value={form.notes_audit || ""}
          onChange={(e) => { const value = e.target.value; setForm(prev => ({ ...prev, notes_audit: value })); }}
          placeholder="Observations, remarques..."
          rows={3}
        />
      </div>

      {formError && <p className="text-sm text-destructive">{formError}</p>}
    </div>
  );
}
