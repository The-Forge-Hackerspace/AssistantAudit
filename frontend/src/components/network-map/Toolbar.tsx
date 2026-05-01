"use client";

import { Map as MapIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Entreprise, Site } from "@/types";

/**
 * Bandeau supérieur de la page Cartographie réseau :
 * titre + filtres entreprise/site + onglets de navigation.
 * NB : la barre d'actions par onglet (`MapToolbar`) est conservée à part.
 */
interface ToolbarProps {
  entreprises: Entreprise[];
  sites: Site[];
  selectedEntrepriseId: number | null;
  selectedSiteId: number | null;
  onSelectEntreprise: (id: number) => void;
  onSelectSite: (id: number) => void;
}

export function NetworkMapToolbar({
  entreprises,
  sites,
  selectedEntrepriseId,
  selectedSiteId,
  onSelectEntreprise,
  onSelectSite,
}: ToolbarProps) {
  return (
    <>
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <MapIcon className="h-6 w-6" />
          Cartographie réseau
        </h1>
        <p className="text-muted-foreground">
          Diagrammes simplifiés par site et vue multi-site pour restitution client.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filtres</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <Label>Entreprise</Label>
            <Select
              value={selectedEntrepriseId ? String(selectedEntrepriseId) : ""}
              onValueChange={(value) => onSelectEntreprise(Number(value))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Choisir une entreprise" />
              </SelectTrigger>
              <SelectContent>
                {entreprises.map((e) => (
                  <SelectItem key={e.id} value={String(e.id)}>
                    {e.nom}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Site</Label>
            <Select
              value={selectedSiteId ? String(selectedSiteId) : ""}
              onValueChange={(value) => onSelectSite(Number(value))}
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
        </CardContent>
      </Card>
    </>
  );
}

/**
 * Liste d'onglets — extraite pour permettre au consommateur de placer
 * `<TabsContent>` à proximité de chaque vue.
 */
export function NetworkMapTabsList() {
  return (
    <TabsList>
      <TabsTrigger value="site">Topologie site</TabsTrigger>
      <TabsTrigger value="overview">Vue multi-site</TabsTrigger>
      <TabsTrigger value="detailed">Vue détaillée</TabsTrigger>
    </TabsList>
  );
}
