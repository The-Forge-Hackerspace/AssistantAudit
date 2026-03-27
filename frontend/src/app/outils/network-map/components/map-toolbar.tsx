"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface MapToolbarProps {
  tab: "site" | "overview" | "detailed";
  layoutDirection: "TB" | "LR";
  onAutoLayout: (dir?: "TB" | "LR") => void;
  onToggleDirection: () => void;
  onSaveLayout: () => void;
  onAddLink: () => void;
  onReload: () => void;
  onExportPng: () => void;
  onExportSvg: () => void;
  onAddSiteConnection?: () => void;
  onAutoLayoutDetailed?: () => void;
  onSaveDetailedLayout?: () => void;
  onReloadDetailed?: () => void;
  onExportDetailedPng?: () => void;
  onExportDetailedSvg?: () => void;
}

export function MapToolbar({
  tab,
  layoutDirection,
  onAutoLayout,
  onToggleDirection,
  onSaveLayout,
  onAddLink,
  onReload,
  onExportPng,
  onExportSvg,
  onAddSiteConnection,
  onAutoLayoutDetailed,
  onSaveDetailedLayout,
  onReloadDetailed,
  onExportDetailedPng,
  onExportDetailedSvg,
}: MapToolbarProps) {
  if (tab === "site") {
    return (
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => onAutoLayout()}>Auto-layout</Button>
        <Button
          variant="outline"
          onClick={onToggleDirection}
        >
          {layoutDirection === "TB" ? "\u2193 Vertical" : "\u2192 Horizontal"}
        </Button>
        <Button variant="outline" onClick={onSaveLayout}>Sauvegarder layout</Button>
        <Button onClick={onAddLink}>Ajouter un lien</Button>
        <Button variant="outline" onClick={onReload}>
          Recharger
        </Button>
        <Button variant="outline" onClick={onExportPng}>
          <Download className="h-4 w-4 mr-2" />
          Export PNG
        </Button>
        <Button variant="outline" onClick={onExportSvg}>
          <Download className="h-4 w-4 mr-2" />
          Export SVG
        </Button>
      </div>
    );
  }

  if (tab === "overview") {
    return (
      <div className="flex flex-wrap gap-2">
        {onAddSiteConnection && (
          <Button onClick={onAddSiteConnection}>Ajouter une connexion</Button>
        )}
        <Button variant="outline" onClick={onReload}>
          Recharger
        </Button>
        <Button variant="outline" onClick={onExportPng}>
          <Download className="h-4 w-4 mr-2" />
          Export PNG
        </Button>
        <Button variant="outline" onClick={onExportSvg}>
          <Download className="h-4 w-4 mr-2" />
          Export SVG
        </Button>
      </div>
    );
  }

  if (tab === "detailed") {
    return (
      <div className="flex flex-wrap gap-2">
        {onAutoLayoutDetailed && (
          <Button onClick={onAutoLayoutDetailed}>Auto-layout</Button>
        )}
        {onSaveDetailedLayout && (
          <Button variant="outline" onClick={onSaveDetailedLayout}>
            Sauvegarder layout
          </Button>
        )}
        {onReloadDetailed && (
          <Button variant="outline" onClick={onReloadDetailed}>
            Recharger
          </Button>
        )}
        {onExportDetailedPng && (
          <Button variant="outline" onClick={onExportDetailedPng}>
            <Download className="h-4 w-4 mr-2" />
            Exporter PNG
          </Button>
        )}
        {onExportDetailedSvg && (
          <Button variant="outline" onClick={onExportDetailedSvg}>
            <Download className="h-4 w-4 mr-2" />
            Exporter SVG
          </Button>
        )}
      </div>
    );
  }

  return null;
}
