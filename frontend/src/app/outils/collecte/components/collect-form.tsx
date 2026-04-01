"use client";

import {
  Server,
  Monitor,
  Play,
  Loader2,
  Shield,
  Info,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import type { Equipement } from "@/types";

// ── Constantes ──────────────────────────────────────────────
const PROFILE_OPTIONS: { value: string; label: string; description: string }[] = [
  { value: "linux_server", label: "Serveur Linux", description: "OS, kernel, SSH, firewall, utilisateurs, services, stockage" },
  { value: "opnsense", label: "OPNsense", description: "pf rules, Suricata IDS, CARP HA, VPN, packages, interfaces" },
  { value: "stormshield", label: "Stormshield (SNS)", description: "Filter rules, VPN IPsec/SSL, HA, auth, supervision, logs" },
  { value: "fortigate", label: "FortiGate (FortiOS)", description: "Firewall policies, VPN, admin users, FortiGuard, HA, logs" },
];

export { PROFILE_OPTIONS };

// ── Props ──
export interface CollectFormProps {
  method: "ssh" | "winrm";
  setMethod: (v: "ssh" | "winrm") => void;
  deviceProfile: string;
  setDeviceProfile: (v: string) => void;
  selectedEquipementId: string;
  setSelectedEquipementId: (v: string) => void;
  targetHost: string;
  setTargetHost: (v: string) => void;
  targetPort: string;
  setTargetPort: (v: string) => void;
  username: string;
  setUsername: (v: string) => void;
  password: string;
  setPassword: (v: string) => void;
  privateKey: string;
  setPrivateKey: (v: string) => void;
  passphrase: string;
  setPassphrase: (v: string) => void;
  useSsl: boolean;
  setUseSsl: (v: boolean) => void;
  transport: string;
  setTransport: (v: string) => void;
  launching: boolean;
  loadingEquipements: boolean;
  groupedEquipements: {
    serveurs: Equipement[];
    firewalls: Equipement[];
    reseaux: Equipement[];
    autres: Equipement[];
  };
  onLaunch: () => void;
}

export function CollectForm({
  method,
  setMethod,
  deviceProfile,
  setDeviceProfile,
  selectedEquipementId,
  setSelectedEquipementId,
  targetHost,
  setTargetHost,
  targetPort,
  setTargetPort,
  username,
  setUsername,
  password,
  setPassword,
  privateKey,
  setPrivateKey,
  passphrase,
  setPassphrase,
  useSsl,
  setUseSsl,
  transport,
  setTransport,
  launching,
  loadingEquipements,
  groupedEquipements,
  onLaunch,
}: CollectFormProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Play className="size-5" />
          Lancer une collecte
        </CardTitle>
        <CardDescription>
          Connectez-vous à un serveur pour collecter automatiquement les informations d&apos;audit.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {/* Row 1: Method + Profile + Equipment */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex flex-col gap-2">
            <Label>Méthode de connexion</Label>
            <Select value={method} onValueChange={(v) => setMethod(v as "ssh" | "winrm")}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="ssh">
                    <span className="flex items-center gap-2">
                      <Server className="size-4" /> SSH — Linux / Firewall
                    </span>
                  </SelectItem>
                  <SelectItem value="winrm">
                    <span className="flex items-center gap-2">
                      <Monitor className="size-4" /> WinRM — Serveur Windows
                    </span>
                  </SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>

          {method === "ssh" && (
            <div className="flex flex-col gap-2">
              <Label>Profil de collecte</Label>
              <Select value={deviceProfile} onValueChange={setDeviceProfile}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {PROFILE_OPTIONS.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        <span className="flex items-center gap-2">
                          {p.value === "linux_server" ? (
                            <Server className="size-4" />
                          ) : (
                            <Shield className="size-4" />
                          )}
                          {p.label}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <Label>Équipement cible</Label>
            {loadingEquipements ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <Select value={selectedEquipementId} onValueChange={setSelectedEquipementId}>
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un équipement…" />
                </SelectTrigger>
                <SelectContent>
                  {groupedEquipements.serveurs.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>Serveurs</SelectLabel>
                      {groupedEquipements.serveurs.map((e) => (
                        <SelectItem key={e.id} value={String(e.id)}>
                          {e.hostname || e.ip_address} — {e.ip_address}
                          {e.fabricant ? ` (${e.fabricant})` : ""}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                  {groupedEquipements.firewalls.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>Firewalls</SelectLabel>
                      {groupedEquipements.firewalls.map((e) => (
                        <SelectItem key={e.id} value={String(e.id)}>
                          {e.hostname || e.ip_address} — {e.ip_address}
                          {e.fabricant ? ` (${e.fabricant})` : ""}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                  {groupedEquipements.reseaux.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>Réseau</SelectLabel>
                      {groupedEquipements.reseaux.map((e) => (
                        <SelectItem key={e.id} value={String(e.id)}>
                          {e.hostname || e.ip_address} — {e.ip_address}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                  {groupedEquipements.autres.length > 0 && (
                    <SelectGroup>
                      <SelectLabel>Autres</SelectLabel>
                      {groupedEquipements.autres.map((e) => (
                        <SelectItem key={e.id} value={String(e.id)}>
                          {e.hostname || e.ip_address} — {e.ip_address}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        {/* Row 2: Connection details */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex flex-col gap-2">
            <Label>Hôte / IP</Label>
            <Input
              value={targetHost}
              onChange={(e) => setTargetHost(e.target.value)}
              placeholder="192.168.1.10"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label>Port</Label>
            <Input
              value={targetPort}
              onChange={(e) => setTargetPort(e.target.value)}
              placeholder={method === "ssh" ? "22" : "5985"}
              type="number"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label>Utilisateur</Label>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={method === "ssh" ? "root" : "DOMAIN\\admin"}
            />
          </div>
        </div>

        {/* Row 3: Auth */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <Label>Mot de passe</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {method === "ssh" ? (
            <div className="flex flex-col gap-2">
              <Label>Clé privée SSH (optionnel)</Label>
              <Textarea
                value={privateKey}
                onChange={(e) => setPrivateKey(e.target.value)}
                placeholder="-----BEGIN RSA PRIVATE KEY-----..."
                rows={3}
                className="font-mono text-xs"
              />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label>Transport</Label>
                <Select value={transport} onValueChange={setTransport}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="ntlm">NTLM</SelectItem>
                      <SelectItem value="kerberos">Kerberos</SelectItem>
                      <SelectItem value="basic">Basic</SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-2 items-end">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useSsl}
                    onChange={(e) => {
                      setUseSsl(e.target.checked);
                      if (e.target.checked && targetPort === "5985") setTargetPort("5986");
                      if (!e.target.checked && targetPort === "5986") setTargetPort("5985");
                    }}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">HTTPS (port 5986)</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Info box */}
        <div className="rounded-lg border p-3 bg-blue-50 dark:bg-blue-950/20 text-sm">
          <p className="font-medium text-blue-700 dark:text-blue-400 mb-1 flex items-center gap-1">
            <Info className="size-4" /> Informations collectées
          </p>
          <p className="text-blue-600 dark:text-blue-500">
            {method === "winrm"
              ? "OS, mises à jour Windows, WSUS, comptes (admin renommé, politique MdP), pare-feu Windows, RDP/NLA, audit policy, journaux d'événements, Defender, stockage"
              : PROFILE_OPTIONS.find((p) => p.value === deviceProfile)?.description
                ?? "OS, kernel, mises à jour, SSH config, firewall (ufw/iptables), utilisateurs, services, rsyslog, auditd, PAM, antivirus/EDR, stockage"}
          </p>
        </div>

        {/* Launch button */}
        <Button
          onClick={onLaunch}
          disabled={launching || !selectedEquipementId || !targetHost || !username}
          className="gap-2"
        >
          {launching ? (
            <Loader2 className="animate-spin" data-icon="inline-start" />
          ) : (
            <Play data-icon="inline-start" />
          )}
          Lancer la collecte
        </Button>
      </CardContent>
    </Card>
  );
}
