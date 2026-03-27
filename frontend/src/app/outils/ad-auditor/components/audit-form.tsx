"use client";

import {
  Play,
  Loader2,
  RefreshCw,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

import type { Equipement } from "@/types";

// ── Props ────────────────────────────────────────────────────
export interface AuditFormProps {
  equipements: Equipement[];
  loadingEquipements: boolean;
  selectedEquipementId: string;
  setSelectedEquipementId: (value: string) => void;
  targetHost: string;
  setTargetHost: (value: string) => void;
  targetPort: string;
  setTargetPort: (value: string) => void;
  useSsl: boolean;
  setUseSsl: (value: boolean) => void;
  username: string;
  setUsername: (value: string) => void;
  password: string;
  setPassword: (value: string) => void;
  domain: string;
  setDomain: (value: string) => void;
  authMethod: "ntlm" | "simple";
  setAuthMethod: (value: "ntlm" | "simple") => void;
  launching: boolean;
  handleLaunch: () => void;
  loadAudits: () => void;
}

// ── Component ────────────────────────────────────────────────
export function AuditForm({
  equipements,
  loadingEquipements,
  selectedEquipementId,
  setSelectedEquipementId,
  targetHost,
  setTargetHost,
  targetPort,
  setTargetPort,
  useSsl,
  setUseSsl,
  username,
  setUsername,
  password,
  setPassword,
  domain,
  setDomain,
  authMethod,
  setAuthMethod,
  launching,
  handleLaunch,
  loadAudits,
}: AuditFormProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Connexion LDAP</CardTitle>
        <CardDescription>
          Configurez la connexion au contrôleur de domaine Active Directory
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {/* Equipment select */}
          <div className="flex flex-col gap-2">
            <Label>Équipement (optionnel)</Label>
            {loadingEquipements ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <Select value={selectedEquipementId} onValueChange={setSelectedEquipementId}>
                <SelectTrigger>
                  <SelectValue placeholder="— Aucun —" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {equipements.map((eq) => (
                      <SelectItem key={eq.id} value={String(eq.id)}>
                        {eq.hostname || eq.type_equipement} ({eq.ip_address})
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Target host */}
          <div className="flex flex-col gap-2">
            <Label>Hôte DC *</Label>
            <Input
              placeholder="dc01.domain.local"
              value={targetHost}
              onChange={(e) => setTargetHost(e.target.value)}
            />
          </div>

          {/* Port */}
          <div className="flex flex-col gap-2">
            <Label>Port LDAP</Label>
            <Input
              type="number"
              value={targetPort}
              onChange={(e) => setTargetPort(e.target.value)}
            />
          </div>

          {/* Domain */}
          <div className="flex flex-col gap-2">
            <Label>Domaine *</Label>
            <Input
              placeholder="DOMAIN.LOCAL"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
            />
          </div>

          {/* Username */}
          <div className="flex flex-col gap-2">
            <Label>Utilisateur *</Label>
            <Input
              placeholder="admin ou DOMAIN\\admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          {/* Password */}
          <div className="flex flex-col gap-2">
            <Label>Mot de passe *</Label>
            <Input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {/* Auth method */}
          <div className="flex flex-col gap-2">
            <Label>Méthode d&apos;authentification</Label>
            <Select value={authMethod} onValueChange={(v) => setAuthMethod(v as "ntlm" | "simple")}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="ntlm">NTLM</SelectItem>
                  <SelectItem value="simple">Simple</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>

          {/* SSL */}
          <div className="flex flex-col gap-2 items-end">
            <div className="flex items-center space-x-2 pb-2">
              <input
                type="checkbox"
                id="use-ssl"
                checked={useSsl}
                onChange={(e) => setUseSsl(e.target.checked)}
                className="size-4 rounded border-gray-300"
              />
              <Label htmlFor="use-ssl" className="cursor-pointer">
                Utiliser LDAPS (SSL)
              </Label>
            </div>
          </div>
        </div>

        <div className="mt-4 flex gap-2">
          <Button onClick={handleLaunch} disabled={launching}>
            {launching ? (
              <>
                <Loader2 className="animate-spin" data-icon="inline-start" />
                Lancement...
              </>
            ) : (
              <>
                <Play data-icon="inline-start" />
                Lancer l&apos;audit AD
              </>
            )}
          </Button>
          <Button variant="outline" onClick={loadAudits}>
            <RefreshCw data-icon="inline-start" />
            Rafraîchir
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
