"use client";

import { useRef } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useTheme } from "next-themes";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";
import { LinkDialog } from "@/components/network-map/ConnectionForm";
import { EquipmentDetailDialog } from "@/components/network-map/EquipmentDetailDialog";
import { SiteConnectionDialog } from "@/components/network-map/SiteConnectionDialog";
import { TabsArea } from "@/components/network-map/TabsArea";
import {
  NetworkMapTabsList,
  NetworkMapToolbar,
} from "@/components/network-map/Toolbar";
import {
  PortPresetConfirmDialog,
  VlanEditorDialog,
} from "@/components/network-map/VlanEditor";
import { useNetworkMap } from "@/hooks/useNetworkMap";

/**
 * Page de cartographie réseau — orchestrateur uniquement. Toute la logique
 * vit dans `useNetworkMap` ; les composants présentationnels sont dans
 * `components/network-map/`.
 */
export default function NetworkMapPage() {
  const { resolvedTheme } = useTheme();
  const rfColorMode = resolvedTheme === "dark" ? "dark" : "light";
  const map = useNetworkMap();
  const { context, data, reload } = map;

  const siteFlowRef = useRef<HTMLDivElement>(null);
  const overviewFlowRef = useRef<HTMLDivElement>(null);
  const detailedFlowRef = useRef<HTMLDivElement>(null);

  if (context.loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Cartographie réseau</CardTitle>
            <CardDescription>Chargement…</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <div className="space-y-6">
        <NetworkMapToolbar
          entreprises={context.entreprises}
          sites={context.sites}
          selectedEntrepriseId={context.selectedEntrepriseId}
          selectedSiteId={context.selectedSiteId}
          onSelectEntreprise={context.setSelectedEntrepriseId}
          onSelectSite={context.setSelectedSiteId}
        />

        <Tabs
          value={context.activeTab}
          onValueChange={(value) =>
            context.setActiveTab(value as "site" | "overview" | "detailed")
          }
        >
          <NetworkMapTabsList />
          <TabsArea
            map={map}
            rfColorMode={rfColorMode}
            siteFlowRef={siteFlowRef}
            overviewFlowRef={overviewFlowRef}
            detailedFlowRef={detailedFlowRef}
          />
        </Tabs>

        <LinkDialog linkForm={map.linkForm} siteEquipements={data.siteEquipements} />
        <SiteConnectionDialog siteConnForm={map.siteConnForm} sites={context.sites} />
        <EquipmentDetailDialog
          detail={map.detail}
          sites={context.sites}
          siteVlans={data.siteVlans}
          selectedSiteId={context.selectedSiteId}
          onOpenVlanEditor={() => map.vlanEditor.setOpen(true)}
          loadVlans={reload.loadVlans}
        />
        <VlanEditorDialog vlanEditor={map.vlanEditor} siteVlans={data.siteVlans} />
        <PortPresetConfirmDialog
          open={map.detail.isPortPresetConfirmOpen}
          setOpen={map.detail.setIsPortPresetConfirmOpen}
          currentPortsCount={map.detail.editingPorts.length}
          onConfirm={map.detail.confirmPreset}
          onCancel={() => {
            map.detail.setIsPortPresetConfirmOpen(false);
            map.detail.setPendingPreset(null);
          }}
        />
      </div>
    </ReactFlowProvider>
  );
}
