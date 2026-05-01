"use client";

import { type RefObject } from "react";
import { Globe, Network } from "lucide-react";
import { toast } from "sonner";

import { MapToolbar } from "@/app/outils/network-map/components/map-toolbar";
import { exportDiagramPng, exportDiagramSvg } from "@/app/outils/network-map/components/map-utils";
import { TabsContent } from "@/components/ui/tabs";
import { InlinePortEditor } from "@/components/network-map/InlinePortEditor";
import { TopologyView } from "@/components/network-map/TopologyView";
import { VlanPanel } from "@/components/network-map/VlanEditor";
import type { UseNetworkMap } from "@/hooks/useNetworkMap";

/**
 * Conteneurs pour les trois onglets de la page (site / overview / detailed).
 * Chaque onglet juxtapose la barre `MapToolbar` (actions) à `TopologyView`
 * (ReactFlow) et délègue toute la logique au hook `useNetworkMap`.
 */
interface TabsAreaProps {
  map: UseNetworkMap;
  rfColorMode: "light" | "dark";
  siteFlowRef: RefObject<HTMLDivElement | null>;
  overviewFlowRef: RefObject<HTMLDivElement | null>;
  detailedFlowRef: RefObject<HTMLDivElement | null>;
}

export function TabsArea({
  map,
  rfColorMode,
  siteFlowRef,
  overviewFlowRef,
  detailedFlowRef,
}: TabsAreaProps) {
  const { context, data, layout, reload, site, overviewFlow, detailed } = map;
  const openLink = () => {
    map.linkForm.reset();
    map.linkForm.setOpen(true);
  };

  return (
    <>
      <TabsContent value="site" className="space-y-4">
        <MapToolbar
          tab="site"
          layoutDirection={layout.layoutDirection}
          onAutoLayout={(dir) => layout.handleAutoLayout(dir)}
          onToggleDirection={layout.toggleLayoutDirection}
          onSaveLayout={layout.handleSaveLayout}
          onAddLink={openLink}
          onReload={() => {
            if (context.selectedSiteId) reload.loadSiteMap(context.selectedSiteId);
          }}
          onExportPng={() => {
            if (siteFlowRef.current) exportDiagramPng(siteFlowRef.current, site.nodes);
          }}
          onExportSvg={() => {
            if (siteFlowRef.current) exportDiagramSvg(siteFlowRef.current, site.nodes);
          }}
        />
        <TopologyView
          ref={siteFlowRef}
          nodes={site.nodes}
          edges={site.edges}
          onNodesChange={site.onNodesChange}
          onEdgesChange={site.onEdgesChange}
          onConnect={site.onConnect}
          onNodeDoubleClick={site.onNodeDoubleClick}
          onEdgeDoubleClick={site.onEdgeDoubleClick}
          colorMode={rfColorMode}
        />
      </TabsContent>

      <TabsContent value="overview" className="space-y-4">
        <MapToolbar
          tab="overview"
          layoutDirection={layout.layoutDirection}
          onAutoLayout={(dir) => layout.handleAutoLayout(dir)}
          onToggleDirection={layout.toggleLayoutDirection}
          onSaveLayout={layout.handleSaveLayout}
          onAddLink={openLink}
          onReload={() => {
            if (context.selectedEntrepriseId) reload.loadOverview(context.selectedEntrepriseId);
          }}
          onExportPng={() => {
            if (overviewFlowRef.current)
              exportDiagramPng(overviewFlowRef.current, overviewFlow.nodes);
          }}
          onExportSvg={() => {
            if (overviewFlowRef.current)
              exportDiagramSvg(overviewFlowRef.current, overviewFlow.nodes);
          }}
          onAddSiteConnection={() => {
            map.siteConnForm.reset();
            map.siteConnForm.setOpen(true);
          }}
        />
        <TopologyView
          ref={overviewFlowRef}
          nodes={overviewFlow.nodes}
          edges={overviewFlow.edges}
          onNodesChange={overviewFlow.onNodesChange}
          onEdgesChange={overviewFlow.onEdgesChange}
          onEdgeDoubleClick={overviewFlow.onEdgeDoubleClick}
          colorMode={rfColorMode}
          nodesDraggable
          nodesConnectable={false}
          elementsSelectable
        />
        {data.overview && (
          <div className="text-sm text-muted-foreground flex items-center gap-2">
            <Globe className="h-4 w-4" />
            {data.overview.nodes.length} site(s), {data.overview.edges.length} connexion(s)
            inter-sites
          </div>
        )}
      </TabsContent>

      <TabsContent value="detailed" className="space-y-4">
        <MapToolbar
          tab="detailed"
          layoutDirection={layout.layoutDirection}
          onAutoLayout={(dir) => layout.handleAutoLayout(dir)}
          onToggleDirection={layout.toggleLayoutDirection}
          onSaveLayout={layout.handleSaveLayout}
          onAddLink={openLink}
          onReload={() => {
            if (context.selectedSiteId) reload.loadSiteMap(context.selectedSiteId);
          }}
          onExportPng={() => {
            if (siteFlowRef.current) exportDiagramPng(siteFlowRef.current, site.nodes);
          }}
          onExportSvg={() => {
            if (siteFlowRef.current) exportDiagramSvg(siteFlowRef.current, site.nodes);
          }}
          onAutoLayoutDetailed={layout.handleAutoLayoutDetailed}
          onSaveDetailedLayout={() => layout.handleSaveDetailedLayout()}
          onReloadDetailed={() => {
            if (!context.selectedSiteId) {
              toast.error("Aucun site sélectionné");
              return;
            }
            reload.loadDetailedView(context.selectedSiteId);
          }}
          onExportDetailedPng={() => {
            if (detailedFlowRef.current)
              exportDiagramPng(detailedFlowRef.current, detailed.nodes);
          }}
          onExportDetailedSvg={() => {
            if (detailedFlowRef.current)
              exportDiagramSvg(detailedFlowRef.current, detailed.nodes);
          }}
        />
        <TopologyView
          ref={detailedFlowRef}
          nodes={detailed.nodes}
          edges={detailed.edges}
          onNodesChange={detailed.onNodesChange}
          onEdgesChange={detailed.onEdgesChange}
          onNodeDragStop={detailed.onNodeDragStop}
          onNodeDoubleClick={detailed.onNodeDoubleClick}
          colorMode={rfColorMode}
          nodesDraggable
          nodesConnectable={false}
          elementsSelectable
        />
        <VlanPanel
          siteVlans={data.siteVlans}
          expanded={map.vlanEditor.panelExpanded}
          setExpanded={map.vlanEditor.setPanelExpanded}
          onOpenEditor={() => map.vlanEditor.setOpen(true)}
        />
        {data.siteMap && (
          <div className="text-sm text-muted-foreground flex items-center gap-2">
            <Network className="h-4 w-4" />
            {detailed.nodes.length} équipement(s), {detailed.edges.length} lien(s)
          </div>
        )}
        <InlinePortEditor inlinePort={map.inlinePort} siteVlans={data.siteVlans} />
      </TabsContent>
    </>
  );
}
