"use client";

import { Play, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import type { Agent, OradadConfig } from "@/types";

export interface CollectFormProps {
  oradadAgents: Agent[];
  loadingAgents: boolean;
  configs: OradadConfig[];
  selectedAgentUuid: string;
  setSelectedAgentUuid: (v: string) => void;
  selectedConfigId: string;
  setSelectedConfigId: (v: string) => void;
  domainOverride: string;
  setDomainOverride: (v: string) => void;
  launching: boolean;
  handleLaunch: () => void;
}

export function CollectForm({
  oradadAgents,
  loadingAgents,
  configs,
  selectedAgentUuid,
  setSelectedAgentUuid,
  selectedConfigId,
  setSelectedConfigId,
  domainOverride,
  setDomainOverride,
  launching,
  handleLaunch,
}: CollectFormProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Lancer une collecte</CardTitle>
        <CardDescription>
          Sélectionnez un agent et un profil de configuration pour collecter les données AD.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="flex flex-col gap-2">
              <Label htmlFor="launch-agent">Agent *</Label>
              {loadingAgents ? (
                <Skeleton className="h-10 w-full" />
              ) : oradadAgents.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Aucun agent actif avec l&apos;outil ORADAD
                </p>
              ) : (
                <Select value={selectedAgentUuid} onValueChange={setSelectedAgentUuid}>
                  <SelectTrigger id="launch-agent">
                    <SelectValue placeholder="Sélectionner un agent" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {oradadAgents.map((a) => (
                        <SelectItem key={a.agent_uuid} value={a.agent_uuid}>
                          {a.name} {a.last_ip ? `(${a.last_ip})` : ""}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="launch-config">Profil de configuration *</Label>
              <Select value={selectedConfigId} onValueChange={setSelectedConfigId}>
                <SelectTrigger id="launch-config">
                  <SelectValue placeholder="Sélectionner un profil" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {configs.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.name} (Niv. {c.level})
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              {configs.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Créez d&apos;abord un profil dans la section ci-dessus.
                </p>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="oradad-domain-override">Domaine override (optionnel)</Label>
              <Input
                id="oradad-domain-override"
                placeholder="Override ponctuel"
                value={domainOverride}
                onChange={(e) => setDomainOverride(e.target.value)}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleLaunch}
              disabled={launching || !selectedAgentUuid || !selectedConfigId}
            >
              {launching ? (
                <Loader2 data-icon="inline-start" className="animate-spin" />
              ) : (
                <Play data-icon="inline-start" />
              )}
              Lancer la collecte
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
