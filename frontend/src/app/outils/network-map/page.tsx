"use client";

import { useCallback, useEffect, useMemo, useRef, useState, memo } from "react";
import dagre from "@dagrejs/dagre";
import {
  Background,
  BaseEdge,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  getNodesBounds,
  getViewportForBounds,
  type Connection,
  type Edge,
  type EdgeProps,
  type EdgeTypes,
  type Node,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Cloud,
  Cpu,
  Download,
  Globe,
  HardDrive,
  Map as MapIcon,
  Monitor,
  Network,
  Phone,
  Printer,
  Radio,
  Router,
  Server,
  Shield,
  Video,
  Wifi,
} from "lucide-react";
import { toPng, toSvg } from "html-to-image";
import { toast } from "sonner";
import { useTheme } from "next-themes";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { entreprisesApi, equipementsApi, networkMapApi, sitesApi, toolsApi } from "@/services/api";
import {
  EQUIPEMENT_TYPE_LABELS,
  EQUIPEMENT_TYPE_ICONS,
  EQUIPEMENT_STATUS_LABELS,
  EQUIPEMENT_STATUS_VARIANTS,
} from "@/lib/constants";
import type {
  Entreprise,
  Equipement,
  MultiSiteOverview,
  NetworkLink,
  NetworkLinkCreate,
  NetworkMap,
  PortDefinition,
  Site,
  SiteConnection,
  SiteConnectionCreate,
  TypeEquipement,
} from "@/types";

type FlowNodeData = Record<string, unknown> & {
  label: string;
  ip: string;
  type: TypeEquipement;
};

export type DetailedNodeData = FlowNodeData & {
  ports: PortDefinition[];
  connectedPortIds: string[];
};

type DeviceNodeType = Node<FlowNodeData, "device">;
type DetailedNodeType = Node<DetailedNodeData, "detailed">;

const iconByType: Record<TypeEquipement, typeof Server> = {
  reseau: Network,
  serveur: Monitor,
  firewall: Shield,
  equipement: Server,
  switch: Network,
  router: Router,
  access_point: Wifi,
  printer: Printer,
  camera: Video,
  nas: HardDrive,
  hyperviseur: Cpu,
  telephone: Phone,
  iot: Radio,
  cloud_gateway: Cloud,
};

const edgeStyleByLinkType: Record<string, { stroke: string; strokeDasharray?: string }> = {
  ethernet: { stroke: "#6b7280" },
  fiber: { stroke: "#f59e0b" },
  wifi: { stroke: "#3b82f6", strokeDasharray: "6 3" },
  vpn: { stroke: "#22c55e", strokeDasharray: "6 3" },
  wan: { stroke: "#a855f7" },
  mpls: { stroke: "#0ea5e9" },
  sdwan: { stroke: "#f472b6" },
  serial: { stroke: "#78716c" },
  other: { stroke: "#9ca3af", strokeDasharray: "4 4" },
};

const nodeColorByType: Record<TypeEquipement, string> = {
  firewall: "#ef4444",
  switch: "#3b82f6",
  reseau: "#3b82f6",
  router: "#8b5cf6",
  serveur: "#22c55e",
  access_point: "#06b6d4",
  printer: "#78716c",
  camera: "#f59e0b",
  nas: "#14b8a6",
  hyperviseur: "#6366f1",
  telephone: "#ec4899",
  iot: "#f97316",
  cloud_gateway: "#0ea5e9",
  equipement: "#6b7280",
};

const bandwidthShort: Record<string, string> = {
  "100 Mbps": "100M",
  "1 Gbps": "1G",
  "2.5 Gbps": "2.5G",
  "5 Gbps": "5G",
  "10 Gbps": "10G",
  "25 Gbps": "25G",
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toPosition(value: unknown): { x: number; y: number } | undefined {
  if (!isObject(value)) return undefined;
  const x = value.x;
  const y = value.y;
  if (typeof x !== "number" || typeof y !== "number") return undefined;
  return { x, y };
}

function toFlowNodes(map: NetworkMap): Node<FlowNodeData>[] {
  return map.nodes.map((n) => {
    const saved = toPosition(n.position);
    return {
      id: n.id,
      type: "device",
      data: {
        label: n.label,
        ip: n.ip_address,
        type: n.type_equipement,
      },
      position: saved ?? { x: 0, y: 0 },
    };
  });
}

function toFlowEdges(map: NetworkMap): Edge[] {
  return map.edges.map((e) => {
    const srcIf = typeof e.metadata.source_interface === "string" ? e.metadata.source_interface : "";
    const tgtIf = typeof e.metadata.target_interface === "string" ? e.metadata.target_interface : "";
    const linkType = typeof e.metadata.link_type === "string" ? e.metadata.link_type : "ethernet";
    const bw = typeof e.metadata.bandwidth === "string" ? e.metadata.bandwidth : "";

    const parts: string[] = [];
    if (srcIf && tgtIf) {
      parts.push(`${srcIf} ↔ ${tgtIf}`);
    } else if (srcIf || tgtIf) {
      parts.push(srcIf || tgtIf);
    }
    if (bw) {
      parts.push(bandwidthShort[bw] ?? bw);
    }
    const label = parts.length > 0 ? parts.join(" • ") : linkType;

    const edgeStyle = edgeStyleByLinkType[linkType] ?? edgeStyleByLinkType.other;

    return {
      id: e.id,
      source: e.source,
      target: e.target,
      type: "parallel",
      label,
      style: { stroke: edgeStyle.stroke, strokeWidth: 2, strokeDasharray: edgeStyle.strokeDasharray },
      data: { linkId: e.link_id },
    };
  });
}

function autoLayout(nodes: Node<FlowNodeData>[], edges: Edge[], direction: "TB" | "LR" = "TB"): Node<FlowNodeData>[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, ranksep: 90, nodesep: 70 });

  nodes.forEach((node) => {
    g.setNode(node.id, { width: 180, height: 64 });
  });
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });
  dagre.layout(g);

  return nodes.map((node) => {
    const p = g.node(node.id);
    if (!p || typeof p.x !== "number" || typeof p.y !== "number") return node;
    return {
      ...node,
      position: { x: p.x - 90, y: p.y - 32 },
    };
  });
}

function DeviceNode({ data }: NodeProps<DeviceNodeType>) {
  const nodeData = data as FlowNodeData;
  const Icon = iconByType[nodeData.type] ?? Server;
  const borderColor = nodeColorByType[nodeData.type] ?? "#6b7280";
  return (
    <div
      className="rounded-md border bg-card px-3 py-2 shadow-sm min-w-[180px] relative"
      style={{ borderLeftWidth: 4, borderLeftColor: borderColor }}
    >
      <Handle type="target" position={Position.Top} className="!w-2 !h-2" />
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4" style={{ color: borderColor }} />
        <span className="text-sm font-medium truncate">{nodeData.label}</span>
      </div>
      <div className="text-xs text-muted-foreground mt-1 font-mono">{nodeData.ip}</div>
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2" />
    </div>
  );
}

function DetailedEquipmentNode({ data }: NodeProps<DetailedNodeType>) {
  const nodeData = data as DetailedNodeData;
  const Icon = iconByType[nodeData.type] ?? Server;
  const borderColor = nodeColorByType[nodeData.type] ?? "#6b7280";

  const portsRow0 = (nodeData.ports || []).filter(p => p.row === 0).sort((a, b) => a.index - b.index);
  const portsRow1 = (nodeData.ports || []).filter(p => p.row === 1).sort((a, b) => a.index - b.index);
  
  const cols = Math.max(portsRow0.length, portsRow1.length);

  const portColorMap: Record<string, string> = {
    ethernet: "#6b7280",
    sfp: "#3b82f6",
    "sfp+": "#8b5cf6",
    console: "#f97316",
    mgmt: "#22c55e",
  };

  const renderPort = (port: PortDefinition) => {
    const isConnected = nodeData.connectedPortIds?.includes(port.id);
    const bgColor = portColorMap[port.type] ?? "#6b7280";
    
    return (
      <div 
        key={port.id}
        title={port.name}
        className={`w-[28px] h-[22px] rounded-[2px] relative transition-colors ${isConnected ? "ring-2 ring-primary z-10" : ""}`}
        style={{ backgroundColor: bgColor }}
      >
        <Handle type="target" id={`port-${port.id}-in`} position={Position.Top} className="!w-1 !h-1 !min-w-0 !min-h-0 opacity-0" />
        <Handle type="source" id={`port-${port.id}`} position={Position.Bottom} className="!w-1 !h-1 !min-w-0 !min-h-0 opacity-0" />
      </div>
    );
  };

  return (
    <div
      className="rounded-md border bg-card p-3 shadow-sm min-w-[180px] flex flex-col gap-3"
      style={{ borderLeftWidth: 4, borderLeftColor: borderColor }}
    >
      <div>
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4" style={{ color: borderColor }} />
          <span className="text-sm font-medium truncate">{nodeData.label}</span>
        </div>
        <div className="text-xs text-muted-foreground mt-1 font-mono">{nodeData.ip}</div>
      </div>

      <div className="flex flex-col gap-1 mx-auto bg-muted/30 p-1.5 rounded-md border border-border/50">
        {portsRow0.length > 0 && (
          <div className="grid gap-1 justify-center" style={{ gridTemplateColumns: `repeat(${cols}, 28px)` }}>
            {portsRow0.map(renderPort)}
          </div>
        )}
        {portsRow1.length > 0 && (
          <div className="grid gap-1 justify-center" style={{ gridTemplateColumns: `repeat(${cols}, 28px)` }}>
            {portsRow1.map(renderPort)}
          </div>
        )}
      </div>
    </div>
  );
}

const PARALLEL_EDGE_SPACING = 35;

function ParallelEdge({
  id,
  source,
  target,
  sourceX,
  sourceY,
  targetX,
  targetY,
  label,
  markerEnd,
  style,
}: EdgeProps) {
  const { getEdges } = useReactFlow();

  const { path, labelX, labelY } = useMemo(() => {
    const siblings = getEdges().filter(
      (e) =>
        (e.source === source && e.target === target) ||
        (e.source === target && e.target === source),
    );

    let offset = 0;
    if (siblings.length > 1) {
      const sorted = siblings.map((e) => e.id).sort();
      const idx = sorted.indexOf(id);
      const mid = (siblings.length - 1) / 2;
      offset = (idx - mid) * PARALLEL_EDGE_SPACING;
    }

    const dx = targetX - sourceX;
    const dy = targetY - sourceY;
    const len = Math.sqrt(dx * dx + dy * dy) || 1;
    const nx = -dy / len;
    const ny = dx / len;

    const cx = (sourceX + targetX) / 2 + nx * offset;
    const cy = (sourceY + targetY) / 2 + ny * offset;

    const d = `M ${sourceX},${sourceY} Q ${cx},${cy} ${targetX},${targetY}`;

    const t = 0.5;
    const lx = (1 - t) * (1 - t) * sourceX + 2 * (1 - t) * t * cx + t * t * targetX;
    const ly = (1 - t) * (1 - t) * sourceY + 2 * (1 - t) * t * cy + t * t * targetY;

    return { path: d, labelX: lx, labelY: ly };
  }, [id, source, target, sourceX, sourceY, targetX, targetY, getEdges]);

  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} />
      {label && (
        <foreignObject
          x={labelX - 60}
          y={labelY - 10}
          width={120}
          height={20}
          className="pointer-events-none overflow-visible"
        >
          <div className="flex items-center justify-center h-full">
            <span className="bg-background/90 border border-border rounded px-1.5 py-0.5 text-[10px] font-medium text-foreground whitespace-nowrap leading-none">
              {label}
            </span>
          </div>
        </foreignObject>
      )}
    </>
  );
}

const nodeTypes: NodeTypes = { device: DeviceNode, detailed: memo(DetailedEquipmentNode) };
const edgeTypes: EdgeTypes = { parallel: ParallelEdge };

/**
 * Generates pre-configured port arrays for common network equipment.
 * Port IDs auto-generate as: {type_short}-{row}-{index}
 * Port names auto-generate as: {TypeLabel} {global_index+1}
 * 
 * Supported presets:
 * - "24×GigE+4×SFP+" → 24 GigE 1Gbps + 4 SFP+ 10Gbps (28 total)
 * - "48×GigE+4×SFP+" → 48 GigE 1Gbps + 4 SFP+ 10Gbps (52 total)
 * - "8×SFP+10G" → 8 SFP+ 10Gbps (8 total)
 * - "4×SFP28-25G" → 4 SFP+ 25Gbps (4 total, all row 0)
 */
function generatePortPreset(presetType: string): PortDefinition[] {
  const ports: PortDefinition[] = [];
  
  switch (presetType) {
    case "24×GigE+4×SFP+": {
      // 24× GigE 1Gbps: 12 on row 0, 12 on row 1
      let globalIdx = 1;
      for (let row = 0; row < 2; row++) {
        for (let i = 0; i < 12; i++) {
          ports.push({
            id: `ge-${row}-${i}`,
            name: `GigE ${globalIdx}`,
            type: "ethernet",
            speed: "1 Gbps",
            row,
            index: i,
          });
          globalIdx++;
        }
      }
      // 4× SFP+ 10Gbps: 2 on row 0 indices 12-13, 2 on row 1 indices 12-13
      ports.push({
        id: "sfp-0-12",
        name: "SFP+ 25",
        type: "sfp+",
        speed: "10 Gbps",
        row: 0,
        index: 12,
      });
      ports.push({
        id: "sfp-0-13",
        name: "SFP+ 26",
        type: "sfp+",
        speed: "10 Gbps",
        row: 0,
        index: 13,
      });
      ports.push({
        id: "sfp-1-12",
        name: "SFP+ 27",
        type: "sfp+",
        speed: "10 Gbps",
        row: 1,
        index: 12,
      });
      ports.push({
        id: "sfp-1-13",
        name: "SFP+ 28",
        type: "sfp+",
        speed: "10 Gbps",
        row: 1,
        index: 13,
      });
      break;
    }
    
    case "48×GigE+4×SFP+": {
      // 48× GigE 1Gbps: 24 on row 0, 24 on row 1
      let globalIdx = 1;
      for (let row = 0; row < 2; row++) {
        for (let i = 0; i < 24; i++) {
          ports.push({
            id: `ge-${row}-${i}`,
            name: `GigE ${globalIdx}`,
            type: "ethernet",
            speed: "1 Gbps",
            row,
            index: i,
          });
          globalIdx++;
        }
      }
      // 4× SFP+ 10Gbps: 2 on row 0 indices 24-25, 2 on row 1 indices 24-25
      ports.push({
        id: "sfp-0-24",
        name: "SFP+ 49",
        type: "sfp+",
        speed: "10 Gbps",
        row: 0,
        index: 24,
      });
      ports.push({
        id: "sfp-0-25",
        name: "SFP+ 50",
        type: "sfp+",
        speed: "10 Gbps",
        row: 0,
        index: 25,
      });
      ports.push({
        id: "sfp-1-24",
        name: "SFP+ 51",
        type: "sfp+",
        speed: "10 Gbps",
        row: 1,
        index: 24,
      });
      ports.push({
        id: "sfp-1-25",
        name: "SFP+ 52",
        type: "sfp+",
        speed: "10 Gbps",
        row: 1,
        index: 25,
      });
      break;
    }
    
    case "8×SFP+10G": {
      // 8× SFP+ 10Gbps: 4 on row 0, 4 on row 1
      let globalIdx = 1;
      for (let row = 0; row < 2; row++) {
        for (let i = 0; i < 4; i++) {
          ports.push({
            id: `sfp-${row}-${i}`,
            name: `SFP+ ${globalIdx}`,
            type: "sfp+",
            speed: "10 Gbps",
            row,
            index: i,
          });
          globalIdx++;
        }
      }
      break;
    }
    
    case "4×SFP28-25G": {
      // 4× SFP+ 25Gbps: all on row 0
      for (let i = 0; i < 4; i++) {
        ports.push({
          id: `sfp-0-${i}`,
          name: `SFP+ ${i + 1}`,
          type: "sfp+",
          speed: "25 Gbps",
          row: 0,
          index: i,
        });
      }
      break;
    }
    
    default:
      console.warn(`Unknown preset type: ${presetType}`);
  }
  
  return ports;
}

async function exportDiagramPng(flowElement: HTMLElement, nodes: Node[]): Promise<void> {
  const imageWidth = 1024;
  const imageHeight = 768;
  const padding = 50;

  const nodesBounds = getNodesBounds(nodes);
  const viewport = getViewportForBounds(
    nodesBounds,
    imageWidth,
    imageHeight,
    0.5,
    2,
    padding / 100
  );

  const viewportElement = flowElement.querySelector(".react-flow__viewport") as HTMLElement;
  if (!viewportElement) {
    console.error("React Flow viewport element not found");
    return;
  }

  try {
    const dataUrl = await toPng(viewportElement, {
      width: imageWidth,
      height: imageHeight,
      style: {
        width: String(imageWidth),
        height: String(imageHeight),
        transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
      },
    });

    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = `network-diagram-${new Date().toISOString().split("T")[0]}.png`;
    link.click();
  } catch (error) {
    console.error("Error exporting PNG:", error);
    toast.error("Erreur lors de l'export PNG");
  }
}

async function exportDiagramSvg(flowElement: HTMLElement, nodes: Node[]): Promise<void> {
  const imageWidth = 1024;
  const imageHeight = 768;
  const padding = 50;

  const nodesBounds = getNodesBounds(nodes);
  const viewport = getViewportForBounds(
    nodesBounds,
    imageWidth,
    imageHeight,
    0.5,
    2,
    padding / 100
  );

  const viewportElement = flowElement.querySelector(".react-flow__viewport") as HTMLElement;
  if (!viewportElement) {
    console.error("React Flow viewport element not found");
    return;
  }

  try {
    const dataUrl = await toSvg(viewportElement, {
      width: imageWidth,
      height: imageHeight,
      style: {
        width: String(imageWidth),
        height: String(imageHeight),
        transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
      },
    });

    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = `network-diagram-${new Date().toISOString().split("T")[0]}.svg`;
    link.click();
  } catch (error) {
    console.error("Error exporting SVG:", error);
    toast.error("Erreur lors de l'export SVG");
  }
}

export default function NetworkMapPage() {
  const { resolvedTheme } = useTheme();
  const rfColorMode = resolvedTheme === "dark" ? "dark" : "light";
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedEntrepriseId, setSelectedEntrepriseId] = useState<number | null>(null);
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null);
  const [siteMap, setSiteMap] = useState<NetworkMap | null>(null);
  const [overview, setOverview] = useState<MultiSiteOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"site" | "overview" | "detailed">("site");
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const [layoutDirection, setLayoutDirection] = useState<"TB" | "LR">("TB");

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailEquipement, setDetailEquipement] = useState<Equipement | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailAssessments, setDetailAssessments] = useState<
    { id: number; campaign_id: number; framework_id: number; framework_name: string; created_at: string }[]
  >([]);

  const [editingPorts, setEditingPorts] = useState<PortDefinition[]>([]);
  const [newPortName, setNewPortName] = useState("");
  const [newPortType, setNewPortType] = useState<PortDefinition["type"]>("ethernet");
  const [newPortSpeed, setNewPortSpeed] = useState("1 Gbps");
  const [newPortRow, setNewPortRow] = useState<number>(0);
  const [isPortPresetConfirmOpen, setIsPortPresetConfirmOpen] = useState(false);
  const [pendingPreset, setPendingPreset] = useState<string | null>(null);
  const [savingPorts, setSavingPorts] = useState(false);

  useEffect(() => {
    if (detailEquipement) {
      setEditingPorts(detailEquipement.ports_status || []);
    } else {
      setEditingPorts([]);
    }
  }, [detailEquipement]);

  const handleAddPort = useCallback(() => {
    if (!newPortName.trim()) return;
    const id = newPortName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    const maxIndex = Math.max(-1, ...editingPorts.filter(p => p.row === newPortRow).map(p => p.index));
    const newPort: PortDefinition = {
      id,
      name: newPortName.trim(),
      type: newPortType,
      speed: newPortSpeed,
      row: newPortRow,
      index: maxIndex + 1,
    };
    setEditingPorts((prev) => [...prev, newPort]);
    setNewPortName("");
  }, [editingPorts, newPortName, newPortRow, newPortSpeed, newPortType]);

  const handleRemovePort = useCallback((id: string) => {
    setEditingPorts((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const handleApplyPreset = useCallback((preset: string) => {
    if (editingPorts.length > 0) {
      setPendingPreset(preset);
      setIsPortPresetConfirmOpen(true);
    } else {
      setEditingPorts(generatePortPreset(preset));
    }
  }, [editingPorts.length]);

  const confirmPreset = useCallback(() => {
    if (pendingPreset) {
      setEditingPorts(generatePortPreset(pendingPreset));
    }
    setIsPortPresetConfirmOpen(false);
    setPendingPreset(null);
  }, [pendingPreset]);

  const handleSavePorts = useCallback(async () => {
    if (!detailEquipement) return;
    setSavingPorts(true);
    try {
      await equipementsApi.update(detailEquipement.id, { ports_status: editingPorts });
      toast.success("Ports sauvegardés");
      setDetailEquipement(prev => prev ? { ...prev, ports_status: editingPorts } : null);
    } catch (error) {
      console.error(error);
      toast.error("Impossible de sauvegarder les ports");
    } finally {
      setSavingPorts(false);
    }
  }, [detailEquipement, editingPorts]);

  const [sourceEquipementId, setSourceEquipementId] = useState<string>("");
  const [targetEquipementId, setTargetEquipementId] = useState<string>("");
  const [sourceInterface, setSourceInterface] = useState("");
  const [targetInterface, setTargetInterface] = useState("");
  const [linkType, setLinkType] = useState<NetworkLinkCreate["link_type"]>("ethernet");
  const [bandwidth, setBandwidth] = useState("");
  const [vlan, setVlan] = useState("");
  const [networkSegment, setNetworkSegment] = useState("");
  const [linkDescription, setLinkDescription] = useState("");
  const [editingLinkId, setEditingLinkId] = useState<number | null>(null);
  const [linkSaving, setLinkSaving] = useState(false);

  const [sourceEquipPorts, setSourceEquipPorts] = useState<PortDefinition[]>([]);
  const [targetEquipPorts, setTargetEquipPorts] = useState<PortDefinition[]>([]);
  const [selectedSourcePortId, setSelectedSourcePortId] = useState<string>("");
  const [selectedTargetPortId, setSelectedTargetPortId] = useState<string>("");

  const [siteConnDialogOpen, setSiteConnDialogOpen] = useState(false);
  const [editingSiteConnId, setEditingSiteConnId] = useState<number | null>(null);
  const [connSourceSiteId, setConnSourceSiteId] = useState<string>("");
  const [connTargetSiteId, setConnTargetSiteId] = useState<string>("");
  const [connLinkType, setConnLinkType] = useState<SiteConnection["link_type"]>("wan");
  const [connBandwidth, setConnBandwidth] = useState("");
  const [connDescription, setConnDescription] = useState("");
  const [connSaving, setConnSaving] = useState(false);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node<FlowNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const [overviewNodes, setOverviewNodes, onOverviewNodesChange] = useNodesState<Node<FlowNodeData>>([]);
  const [overviewEdges, setOverviewEdges, onOverviewEdgesChange] = useEdgesState<Edge>([]);

  const [detailedNodes, setDetailedNodes, onDetailedNodesChange] = useNodesState<Node<DetailedNodeData | FlowNodeData>>([]);
  const [detailedEdges, setDetailedEdges, onDetailedEdgesChange] = useEdgesState<Edge>([]);

  const siteFlowRef = useRef<HTMLDivElement>(null);
  const overviewFlowRef = useRef<HTMLDivElement>(null);
  const detailedFlowRef = useRef<HTMLDivElement>(null);

  const siteEquipements = useMemo(() => {
    if (!siteMap) return [];
    return siteMap.nodes;
  }, [siteMap]);

  const loadEntreprises = useCallback(async () => {
    const res = await entreprisesApi.list(1, 100);
    setEntreprises(res.items);
    if (res.items.length > 0 && selectedEntrepriseId === null) {
      setSelectedEntrepriseId(res.items[0].id);
    }
  }, [selectedEntrepriseId]);

  const loadSites = useCallback(async (entrepriseId: number) => {
    const res = await sitesApi.list(1, 100, entrepriseId);
    setSites(res.items);
    if (res.items.length > 0) {
      setSelectedSiteId(res.items[0].id);
    } else {
      setSelectedSiteId(null);
    }
  }, []);

   const loadSiteMap = useCallback(async (siteId: number) => {
    const data = await networkMapApi.getSiteMap(siteId);
    setSiteMap(data);
    const nextNodes = toFlowNodes(data);
    const nextEdges = toFlowEdges(data);
    // Only auto-layout if no saved positions exist
    const hasSavedPositions = nextNodes.some(
      (n) => n.position.x !== 0 || n.position.y !== 0
    );
    setNodes(hasSavedPositions ? nextNodes : autoLayout(nextNodes, nextEdges, layoutDirection));
    setEdges(nextEdges);
  }, [setEdges, setNodes, layoutDirection]);

  const loadOverview = useCallback(async (entrepriseId: number) => {
    const data = await networkMapApi.getOverview(entrepriseId);
    setOverview(data);
    const oNodes: Node<FlowNodeData>[] = data.nodes.map((n) => ({
      id: n.id,
      type: "device",
      data: {
        label: `${n.site_name} (${n.equipement_count})`,
        ip: `site-${n.site_id}`,
        type: "cloud_gateway",
      },
      position: { x: 0, y: 0 },
    }));
    const oEdges: Edge[] = data.edges.map((e) => {
      const lt = typeof e.metadata.link_type === "string" ? e.metadata.link_type : "wan";
      const bw = typeof e.metadata.bandwidth === "string" ? e.metadata.bandwidth : "";
      const edgeStyle = edgeStyleByLinkType[lt] ?? edgeStyleByLinkType.other;

      const parts: string[] = [lt.toUpperCase()];
      if (bw) {
        parts.push(bandwidthShort[bw] ?? bw);
      }
      const label = parts.join(" • ");

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        type: "parallel",
        label,
        style: { stroke: edgeStyle.stroke, strokeWidth: 2, strokeDasharray: edgeStyle.strokeDasharray },
        data: { connectionId: e.connection_id },
      };
    });
    setOverviewNodes(autoLayout(oNodes, oEdges));
    setOverviewEdges(oEdges);
  }, [setOverviewEdges, setOverviewNodes]);

  const loadDetailedView = useCallback(async (siteId: number) => {
    const data = await networkMapApi.getSiteMap(siteId);
    setSiteMap(data);

    const links = await networkMapApi.listLinks(siteId);

    const equipmentDetailsPromises = data.nodes.map((node) => 
      equipementsApi.get(node.equipement_id)
    );
    const equipmentDetails = await Promise.all(equipmentDetailsPromises);

    const equipmentMap = new Map<number, Equipement>();
    equipmentDetails.forEach((eq) => {
      equipmentMap.set(eq.id, eq);
    });

    const connectedPortIds = new Set<string>();
    links.forEach((link) => {
      if (link.source_interface) connectedPortIds.add(link.source_interface);
      if (link.target_interface) connectedPortIds.add(link.target_interface);
    });

    const detailedNodesArray: Node<DetailedNodeData | FlowNodeData>[] = data.nodes.map((node) => {
      const equipment = equipmentMap.get(node.equipement_id);
      const ports = equipment?.ports_status || [];
      const hasPorts = ports.length > 0;

      const equipmentConnectedPortIds = ports
        .map((p: PortDefinition) => p.id)
        .filter((id: string) => connectedPortIds.has(id));

      const saved = toPosition(node.position);

      if (hasPorts) {
        return {
          id: node.id,
          type: "detailed",
          data: {
            label: node.label,
            ip: node.ip_address,
            type: node.type_equipement,
            ports,
            connectedPortIds: equipmentConnectedPortIds,
          },
          position: saved ?? { x: 0, y: 0 },
        } as Node<DetailedNodeData>;
      } else {
        return {
          id: node.id,
          type: "device",
          data: {
            label: node.label,
            ip: node.ip_address,
            type: node.type_equipement,
          },
          position: saved ?? { x: 0, y: 0 },
        } as Node<FlowNodeData>;
      }
    });

    const nodeByEquipId = new Map(data.nodes.map(n => [n.equipement_id, n]));

    const detailedEdgesArray: Edge[] = links
      .map((link): Edge | null => {
        const lt = link.link_type;
        const bw = link.bandwidth ?? "";
        const edgeStyle = edgeStyleByLinkType[lt] ?? edgeStyleByLinkType.other;

        const parts: string[] = [lt.toUpperCase()];
        if (bw) {
          parts.push(bandwidthShort[bw] ?? bw);
        }
        const label = parts.join(" • ");

        const sourceNode = nodeByEquipId.get(link.source_equipement_id);
        const targetNode = nodeByEquipId.get(link.target_equipement_id);

        if (!sourceNode || !targetNode) return null;

        return {
          id: String(link.id),
          source: sourceNode.id,
          target: targetNode.id,
          sourceHandle: link.source_interface ? `port-${link.source_interface}` : undefined,
          targetHandle: link.target_interface ? `port-${link.target_interface}-in` : undefined,
          type: "parallel",
          label,
          style: { stroke: edgeStyle.stroke, strokeWidth: 2, strokeDasharray: edgeStyle.strokeDasharray },
          data: { linkId: link.id },
        };
      })
      .filter((edge): edge is Edge => edge !== null);

    const hasSavedPositions = detailedNodesArray.some(
      (n) => n.position.x !== 0 || n.position.y !== 0
    );

    const layoutedNodes = hasSavedPositions 
      ? detailedNodesArray 
      : autoLayoutWithCustomDimensions(detailedNodesArray, detailedEdgesArray, layoutDirection);

                 setDetailedNodes(layoutedNodes);
    setDetailedEdges(detailedEdgesArray);
  }, [setDetailedNodes, setDetailedEdges, layoutDirection]);

  function autoLayoutWithCustomDimensions(
    nodes: Node<DetailedNodeData | FlowNodeData>[],
    edges: Edge[],
    direction: "TB" | "LR" = "TB"
  ): Node<DetailedNodeData | FlowNodeData>[] {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: direction, ranksep: 120, nodesep: 80 });

    nodes.forEach((node) => {
      if (node.type === "detailed") {
        g.setNode(node.id, { width: 250, height: 180 });
      } else {
        g.setNode(node.id, { width: 180, height: 80 });
      }
    });
    edges.forEach((edge) => {
      g.setEdge(edge.source, edge.target);
    });
    dagre.layout(g);

    return nodes.map((node) => {
      const p = g.node(node.id);
      if (!p || typeof p.x !== "number" || typeof p.y !== "number") return node;
      return {
        ...node,
        position: { x: p.x, y: p.y },
      };
    });
  }

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      try {
        await loadEntreprises();
      } catch (error) {
        console.error(error);
        toast.error("Impossible de charger les entreprises");
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [loadEntreprises]);

  useEffect(() => {
    if (!selectedEntrepriseId) return;
    const run = async () => {
      try {
        await loadSites(selectedEntrepriseId);
        await loadOverview(selectedEntrepriseId);
      } catch (error) {
        console.error(error);
        toast.error("Impossible de charger les sites et la vue globale");
      }
    };
    run();
  }, [selectedEntrepriseId, loadSites, loadOverview]);

  useEffect(() => {
    if (!selectedSiteId) return;
    const run = async () => {
      try {
        await loadSiteMap(selectedSiteId);
      } catch (error) {
        console.error(error);
        toast.error("Impossible de charger la carte réseau du site");
      }
    };
    run();
  }, [selectedSiteId, loadSiteMap]);

  useEffect(() => {
    if (!selectedSiteId || activeTab !== "detailed") return;
    let cancelled = false;
    const run = async () => {
      try {
        await loadDetailedView(selectedSiteId);
      } catch (error) {
        if (!cancelled) {
          console.error(error);
          toast.error("Impossible de charger la vue détaillée");
        }
      }
    };
    run();
    return () => { cancelled = true; };
  }, [selectedSiteId, activeTab, loadDetailedView]);

  useEffect(() => {
    if (!sourceEquipementId) {
      setSourceEquipPorts([]);
      setSelectedSourcePortId("");
      return;
    }
    let cancelled = false;
    const fetchPorts = async () => {
      try {
        const eq = await equipementsApi.get(Number(sourceEquipementId));
        if (!cancelled) setSourceEquipPorts(eq.ports_status || []);
      } catch (error) {
        console.error("Error fetching source equipment ports:", error);
        if (!cancelled) setSourceEquipPorts([]);
      }
    };
    fetchPorts();
    return () => { cancelled = true; };
  }, [sourceEquipementId]);

  useEffect(() => {
    if (!targetEquipementId) {
      setTargetEquipPorts([]);
      setSelectedTargetPortId("");
      return;
    }
    let cancelled = false;
    const fetchPorts = async () => {
      try {
        const eq = await equipementsApi.get(Number(targetEquipementId));
        if (!cancelled) setTargetEquipPorts(eq.ports_status || []);
      } catch (error) {
        console.error("Error fetching target equipment ports:", error);
        if (!cancelled) setTargetEquipPorts([]);
      }
    };
    fetchPorts();
    return () => { cancelled = true; };
  }, [targetEquipementId]);

  const handleAutoLayout = useCallback((dir?: "TB" | "LR") => {
    const d = dir ?? layoutDirection;
    setNodes((curr) => autoLayout(curr, edges, d));
  }, [edges, layoutDirection, setNodes]);

  const handleSaveLayout = useCallback(async () => {
    if (!selectedSiteId) return;
    try {
      await networkMapApi.saveSiteLayout(selectedSiteId, {
        nodes: nodes.map((n) => ({ id: n.id, x: n.position.x, y: n.position.y })),
      });
      toast.success("Layout sauvegardé");
    } catch (error) {
      console.error(error);
      toast.error("Échec de sauvegarde du layout");
    }
  }, [nodes, selectedSiteId]);

  const resetLinkForm = useCallback(() => {
    setSourceEquipementId("");
    setTargetEquipementId("");
    setSourceInterface("");
    setTargetInterface("");
    setLinkType("ethernet");
    setBandwidth("");
    setVlan("");
    setNetworkSegment("");
    setLinkDescription("");
    setEditingLinkId(null);
    setSourceEquipPorts([]);
    setTargetEquipPorts([]);
    setSelectedSourcePortId("");
    setSelectedTargetPortId("");
  }, []);

  const handleSaveLink = useCallback(async () => {
    if (!selectedSiteId || !sourceEquipementId || !targetEquipementId) {
      toast.error("Veuillez sélectionner la source et la cible");
      return;
    }
    setLinkSaving(true);
    try {
      const payload = {
        source_interface: sourceInterface || undefined,
        target_interface: targetInterface || undefined,
        link_type: linkType,
        bandwidth: bandwidth || undefined,
        vlan: vlan || undefined,
        network_segment: networkSegment || undefined,
        description: linkDescription || undefined,
      };
      if (editingLinkId) {
        await networkMapApi.updateLink(editingLinkId, payload);
        toast.success("Lien mis à jour");
      } else {
        await networkMapApi.createLink({
          site_id: selectedSiteId,
          source_equipement_id: Number(sourceEquipementId),
          target_equipement_id: Number(targetEquipementId),
          ...payload,
        });
        toast.success("Lien ajouté");
      }
      setLinkDialogOpen(false);
      resetLinkForm();
      await loadSiteMap(selectedSiteId);
    } catch (error) {
      console.error(error);
      toast.error(editingLinkId ? "Impossible de mettre à jour le lien" : "Impossible d'ajouter le lien");
    } finally {
      setLinkSaving(false);
    }
  }, [
    bandwidth,
    editingLinkId,
    linkDescription,
    linkType,
    loadSiteMap,
    networkSegment,
    resetLinkForm,
    selectedSiteId,
    sourceEquipementId,
    sourceInterface,
    targetEquipementId,
    targetInterface,
    vlan,
  ]);

  const handleDeleteLink = useCallback(async () => {
    if (!editingLinkId || !selectedSiteId) return;
    setLinkSaving(true);
    try {
      await networkMapApi.deleteLink(editingLinkId);
      setLinkDialogOpen(false);
      resetLinkForm();
      await loadSiteMap(selectedSiteId);
      toast.success("Lien supprimé");
    } catch (error) {
      console.error(error);
      toast.error("Impossible de supprimer le lien");
    } finally {
      setLinkSaving(false);
    }
  }, [editingLinkId, loadSiteMap, resetLinkForm, selectedSiteId]);

  const onConnect = useCallback((params: Edge | Connection) => {
    if (!selectedSiteId || !params.source || !params.target) return;
    const sourceId = params.source.startsWith("eq-") ? Number(params.source.slice(3)) : null;
    const targetId = params.target.startsWith("eq-") ? Number(params.target.slice(3)) : null;
    if (!sourceId || !targetId) return;

    resetLinkForm();
    setSourceEquipementId(String(sourceId));
    setTargetEquipementId(String(targetId));
    setLinkDialogOpen(true);
  }, [selectedSiteId, resetLinkForm]);

  const onNodeDoubleClick = useCallback(async (_event: React.MouseEvent, node: Node<FlowNodeData>) => {
    const eqId = node.id.startsWith("eq-") ? Number(node.id.slice(3)) : null;
    if (!eqId || Number.isNaN(eqId)) return;
    setDetailOpen(true);
    setDetailEquipement(null);
    setDetailAssessments([]);
    setDetailLoading(true);
    try {
      const [eq, assessments] = await Promise.all([
        equipementsApi.get(eqId),
        toolsApi.listAssessmentsForEquipment(eqId),
      ]);
      setDetailEquipement(eq);
      setDetailAssessments(assessments);
    } catch (error) {
      console.error(error);
      toast.error("Impossible de charger les détails de l'équipement");
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const onEdgeDoubleClick = useCallback(async (_event: React.MouseEvent, edge: Edge) => {
    const linkId = (edge.data as Record<string, unknown> | undefined)?.linkId;
    if (typeof linkId !== "number") return;
    resetLinkForm();
    setLinkDialogOpen(true);
    setLinkSaving(true);
    try {
      const link: NetworkLink = await networkMapApi.getLink(linkId);
      setEditingLinkId(link.id);
      setSourceEquipementId(String(link.source_equipement_id));
      setTargetEquipementId(String(link.target_equipement_id));
      setSourceInterface(link.source_interface ?? "");
      setTargetInterface(link.target_interface ?? "");
      setLinkType(link.link_type);
      setBandwidth(link.bandwidth ?? "");
      setVlan(link.vlan ?? "");
      setNetworkSegment(link.network_segment ?? "");
      setLinkDescription(link.description ?? "");
    } catch (error) {
      console.error(error);
      toast.error("Impossible de charger les détails du lien");
      setLinkDialogOpen(false);
    } finally {
      setLinkSaving(false);
    }
  }, [resetLinkForm]);

  const resetSiteConnForm = useCallback(() => {
    setConnSourceSiteId("");
    setConnTargetSiteId("");
    setConnLinkType("wan");
    setConnBandwidth("");
    setConnDescription("");
    setEditingSiteConnId(null);
  }, []);

  const handleSaveSiteConn = useCallback(async () => {
    if (!selectedEntrepriseId || !connSourceSiteId || !connTargetSiteId) {
      toast.error("Veuillez sélectionner le site source et le site cible");
      return;
    }
    setConnSaving(true);
    try {
      const payload = {
        link_type: connLinkType,
        bandwidth: connBandwidth || undefined,
        description: connDescription || undefined,
      };
      if (editingSiteConnId) {
        await networkMapApi.updateSiteConnection(editingSiteConnId, payload);
        toast.success("Connexion inter-site mise à jour");
      } else {
        await networkMapApi.createSiteConnection({
          entreprise_id: selectedEntrepriseId,
          source_site_id: Number(connSourceSiteId),
          target_site_id: Number(connTargetSiteId),
          ...payload,
        });
        toast.success("Connexion inter-site créée");
      }
      setSiteConnDialogOpen(false);
      resetSiteConnForm();
      await loadOverview(selectedEntrepriseId);
    } catch (error) {
      console.error(error);
      toast.error(editingSiteConnId ? "Impossible de mettre à jour la connexion" : "Impossible de créer la connexion");
    } finally {
      setConnSaving(false);
    }
  }, [
    connBandwidth,
    connDescription,
    connLinkType,
    connSourceSiteId,
    connTargetSiteId,
    editingSiteConnId,
    loadOverview,
    resetSiteConnForm,
    selectedEntrepriseId,
  ]);

  const handleDeleteSiteConn = useCallback(async () => {
    if (!editingSiteConnId || !selectedEntrepriseId) return;
    setConnSaving(true);
    try {
      await networkMapApi.deleteSiteConnection(editingSiteConnId);
      setSiteConnDialogOpen(false);
      resetSiteConnForm();
      await loadOverview(selectedEntrepriseId);
      toast.success("Connexion inter-site supprimée");
    } catch (error) {
      console.error(error);
      toast.error("Impossible de supprimer la connexion");
    } finally {
      setConnSaving(false);
    }
  }, [editingSiteConnId, loadOverview, resetSiteConnForm, selectedEntrepriseId]);

  const onOverviewEdgeDoubleClick = useCallback(async (_event: React.MouseEvent, edge: Edge) => {
    const connectionId = (edge.data as Record<string, unknown> | undefined)?.connectionId;
    if (typeof connectionId !== "number") return;
    resetSiteConnForm();
    setSiteConnDialogOpen(true);
    setConnSaving(true);
    try {
      const conn: SiteConnection = await networkMapApi.getSiteConnection(connectionId);
      setEditingSiteConnId(conn.id);
      setConnSourceSiteId(String(conn.source_site_id));
      setConnTargetSiteId(String(conn.target_site_id));
      setConnLinkType(conn.link_type);
      setConnBandwidth(conn.bandwidth ?? "");
      setConnDescription(conn.description ?? "");
    } catch (error) {
      console.error(error);
      toast.error("Impossible de charger les détails de la connexion");
      setSiteConnDialogOpen(false);
    } finally {
      setConnSaving(false);
    }
  }, [resetSiteConnForm]);

  if (loading) {
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
                onValueChange={(value) => setSelectedEntrepriseId(Number(value))}
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
                onValueChange={(value) => setSelectedSiteId(Number(value))}
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

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "site" | "overview" | "detailed")}>
          <TabsList>
            <TabsTrigger value="site">Topologie site</TabsTrigger>
            <TabsTrigger value="overview">Vue multi-site</TabsTrigger>
            <TabsTrigger value="detailed">Vue détaillée</TabsTrigger>
          </TabsList>

          <TabsContent value="site" className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => handleAutoLayout()}>Auto-layout</Button>
              <Button
                variant="outline"
                onClick={() => {
                  const next = layoutDirection === "TB" ? "LR" : "TB";
                  setLayoutDirection(next);
                  handleAutoLayout(next);
                }}
              >
                {layoutDirection === "TB" ? "↓ Vertical" : "→ Horizontal"}
              </Button>
              <Button variant="outline" onClick={handleSaveLayout}>Sauvegarder layout</Button>
              <Button onClick={() => { resetLinkForm(); setLinkDialogOpen(true); }}>Ajouter un lien</Button>
               {selectedSiteId && (
                 <Button variant="outline" onClick={() => loadSiteMap(selectedSiteId)}>
                   Recharger
                 </Button>
               )}
               <Button
                 variant="outline"
                 onClick={() => {
                   if (siteFlowRef.current) exportDiagramPng(siteFlowRef.current, nodes);
                 }}
               >
                 <Download className="h-4 w-4 mr-2" />
                 Export PNG
               </Button>
               <Button
                 variant="outline"
                 onClick={() => {
                   if (siteFlowRef.current) exportDiagramSvg(siteFlowRef.current, nodes);
                 }}
               >
                 <Download className="h-4 w-4 mr-2" />
                 Export SVG
               </Button>
            </div>

            <div ref={siteFlowRef}>
              <Card>
                <CardContent className="h-[70vh] p-0">
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onNodeDoubleClick={onNodeDoubleClick}
                    onEdgeDoubleClick={onEdgeDoubleClick}
                    nodeTypes={nodeTypes}
                    edgeTypes={edgeTypes}
                    colorMode={rfColorMode}
                    zoomOnDoubleClick={false}
                    fitView
                  >
                    <Background />
                    <Controls />
                    <MiniMap />
                  </ReactFlow>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="overview" className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => { resetSiteConnForm(); setSiteConnDialogOpen(true); }}>Ajouter une connexion</Button>
              {selectedEntrepriseId && (
                <Button variant="outline" onClick={() => loadOverview(selectedEntrepriseId)}>
                  Recharger
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => {
                  if (overviewFlowRef.current) exportDiagramPng(overviewFlowRef.current, overviewNodes);
                }}
              >
                <Download className="h-4 w-4 mr-2" />
                Export PNG
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  if (overviewFlowRef.current) exportDiagramSvg(overviewFlowRef.current, overviewNodes);
                }}
              >
                <Download className="h-4 w-4 mr-2" />
                Export SVG
              </Button>
            </div>

            <div ref={overviewFlowRef}>
              <Card>
                <CardContent className="h-[70vh] p-0">
                  <ReactFlow
                    nodes={overviewNodes}
                    edges={overviewEdges}
                    onNodesChange={onOverviewNodesChange}
                    onEdgesChange={onOverviewEdgesChange}
                    onEdgeDoubleClick={onOverviewEdgeDoubleClick}
                    nodeTypes={nodeTypes}
                    edgeTypes={edgeTypes}
                    colorMode={rfColorMode}
                    zoomOnDoubleClick={false}
                    fitView
                    nodesDraggable
                    nodesConnectable={false}
                    elementsSelectable
                  >
                    <Background />
                    <Controls />
                    <MiniMap />
                  </ReactFlow>
                </CardContent>
              </Card>
            </div>
            {overview && (
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <Globe className="h-4 w-4" />
                {overview.nodes.length} site(s), {overview.edges.length} connexion(s) inter-sites
              </div>
            )}
          </TabsContent>

          <TabsContent value="detailed" className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => {
                const layoutedNodes = autoLayoutWithCustomDimensions(detailedNodes, detailedEdges, layoutDirection);
    setDetailedNodes(layoutedNodes);
              }}>
                Auto-layout
              </Button>
              <Button variant="outline" onClick={() => {
                if (!selectedSiteId) {
                  toast.error("Aucun site sélectionné");
                  return;
                }
                loadDetailedView(selectedSiteId);
              }}>
                Recharger
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  if (detailedFlowRef.current) exportDiagramPng(detailedFlowRef.current, detailedNodes);
                }}
              >
                <Download className="h-4 w-4 mr-2" />
                Exporter PNG
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  if (detailedFlowRef.current) exportDiagramSvg(detailedFlowRef.current, detailedNodes);
                }}
              >
                <Download className="h-4 w-4 mr-2" />
                Exporter SVG
              </Button>
            </div>

            <div ref={detailedFlowRef}>
              <Card>
                <CardContent className="h-[70vh] p-0">
                  <ReactFlow
                    nodes={detailedNodes}
                    edges={detailedEdges}
                    onNodesChange={onDetailedNodesChange}
                    onEdgesChange={onDetailedEdgesChange}
                    nodeTypes={nodeTypes}
                    edgeTypes={edgeTypes}
                    colorMode={rfColorMode}
                    zoomOnDoubleClick={false}
                    fitView
                    nodesDraggable
                    nodesConnectable={false}
                    elementsSelectable
                  >
                    <Background />
                    <Controls />
                    <MiniMap />
                  </ReactFlow>
                </CardContent>
              </Card>
            </div>
            {siteMap && (
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <Network className="h-4 w-4" />
                {detailedNodes.length} équipement(s), {detailedEdges.length} lien(s)
              </div>
            )}
          </TabsContent>
        </Tabs>

        <Dialog open={linkDialogOpen} onOpenChange={(open) => { if (!open) resetLinkForm(); setLinkDialogOpen(open); }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingLinkId ? "Modifier le lien" : "Nouveau lien"}</DialogTitle>
              <DialogDescription>
                {editingLinkId ? "Modifier les propriétés du lien" : "Relier deux équipements du site"}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3">
              <div>
                <Label>Source</Label>
                <Select value={sourceEquipementId} onValueChange={setSourceEquipementId} disabled={!!editingLinkId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Équipement source" />
                  </SelectTrigger>
                  <SelectContent>
                    {siteEquipements.map((eq) => (
                      <SelectItem key={eq.equipement_id} value={String(eq.equipement_id)}>
                        {eq.label} ({eq.ip_address})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Cible</Label>
                <Select value={targetEquipementId} onValueChange={setTargetEquipementId} disabled={!!editingLinkId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Équipement cible" />
                  </SelectTrigger>
                  <SelectContent>
                    {siteEquipements.map((eq) => (
                      <SelectItem key={eq.equipement_id} value={String(eq.equipement_id)}>
                        {eq.label} ({eq.ip_address})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label>Interface source</Label>
                  <Input value={sourceInterface} onChange={(e) => setSourceInterface(e.target.value)} placeholder="Gi0/1" />
                </div>
                <div>
                  <Label>Interface cible</Label>
                  <Input value={targetInterface} onChange={(e) => setTargetInterface(e.target.value)} placeholder="eth0" />
                </div>
              </div>
              {sourceEquipPorts.length > 0 && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label>Port source</Label>
                    <Select 
                      value={selectedSourcePortId} 
                      onValueChange={(value) => {
                        setSelectedSourcePortId(value);
                        if (value) {
                          const port = sourceEquipPorts.find(p => p.id === value);
                          if (port) setSourceInterface(port.id);
                        } else {
                          setSourceInterface("");
                        }
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Aucun" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">Aucun</SelectItem>
                        {sourceEquipPorts.map(port => (
                          <SelectItem key={port.id} value={port.id}>
                            {port.name} ({port.type}, {port.speed})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {targetEquipPorts.length > 0 && (
                    <div>
                      <Label>Port cible</Label>
                      <Select 
                        value={selectedTargetPortId} 
                        onValueChange={(value) => {
                          setSelectedTargetPortId(value);
                          if (value) {
                            const port = targetEquipPorts.find(p => p.id === value);
                            if (port) setTargetInterface(port.id);
                          } else {
                            setTargetInterface("");
                          }
                        }}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Aucun" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">Aucun</SelectItem>
                          {targetEquipPorts.map(port => (
                            <SelectItem key={port.id} value={port.id}>
                              {port.name} ({port.type}, {port.speed})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>
              )}
              {sourceEquipPorts.length === 0 && targetEquipPorts.length > 0 && (
                <div>
                  <Label>Port cible</Label>
                  <Select 
                    value={selectedTargetPortId} 
                    onValueChange={(value) => {
                      setSelectedTargetPortId(value);
                      if (value) {
                        const port = targetEquipPorts.find(p => p.id === value);
                        if (port) setTargetInterface(port.id);
                      } else {
                        setTargetInterface("");
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Aucun" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Aucun</SelectItem>
                      {targetEquipPorts.map(port => (
                        <SelectItem key={port.id} value={port.id}>
                          {port.name} ({port.type}, {port.speed})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              <div>
                <Label>Type de lien</Label>
                <Select value={linkType} onValueChange={(value) => setLinkType(value as NetworkLinkCreate["link_type"])}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ethernet">Ethernet</SelectItem>
                    <SelectItem value="fiber">Fibre</SelectItem>
                    <SelectItem value="wifi">Wi-Fi</SelectItem>
                    <SelectItem value="vpn">VPN</SelectItem>
                    <SelectItem value="wan">WAN</SelectItem>
                    <SelectItem value="serial">Série</SelectItem>
                    <SelectItem value="other">Autre</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label>Débit</Label>
                  <Select value={bandwidth} onValueChange={setBandwidth}>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="100 Mbps">100 Mbps</SelectItem>
                      <SelectItem value="1 Gbps">1 Gbps</SelectItem>
                      <SelectItem value="2.5 Gbps">2.5 Gbps</SelectItem>
                      <SelectItem value="5 Gbps">5 Gbps</SelectItem>
                      <SelectItem value="10 Gbps">10 Gbps</SelectItem>
                      <SelectItem value="25 Gbps">25 Gbps</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>VLAN</Label>
                  <Input value={vlan} onChange={(e) => setVlan(e.target.value)} placeholder="VLAN 10" />
                </div>
              </div>
              <div>
                <Label>Segment réseau</Label>
                <Input value={networkSegment} onChange={(e) => setNetworkSegment(e.target.value)} placeholder="DMZ" />
              </div>
              <div>
                <Label>Description</Label>
                <Input value={linkDescription} onChange={(e) => setLinkDescription(e.target.value)} placeholder="LAGG trunk, uplink…" />
              </div>
            </div>
            <DialogFooter className={editingLinkId ? "flex !justify-between" : ""}>
              {editingLinkId && (
                <Button variant="destructive" onClick={handleDeleteLink} disabled={linkSaving}>
                  Supprimer
                </Button>
              )}
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setLinkDialogOpen(false)}>Annuler</Button>
                <Button onClick={handleSaveLink} disabled={linkSaving}>
                  {editingLinkId ? "Enregistrer" : "Créer le lien"}
                </Button>
              </div>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={siteConnDialogOpen} onOpenChange={(open) => { if (!open) resetSiteConnForm(); setSiteConnDialogOpen(open); }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingSiteConnId ? "Modifier la connexion inter-site" : "Nouvelle connexion inter-site"}</DialogTitle>
              <DialogDescription>
                {editingSiteConnId ? "Modifier les propriétés de la connexion" : "Relier deux sites de l'entreprise"}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3">
              <div>
                <Label>Site source</Label>
                <Select value={connSourceSiteId} onValueChange={setConnSourceSiteId} disabled={!!editingSiteConnId}>
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
              <div>
                <Label>Site cible</Label>
                <Select value={connTargetSiteId} onValueChange={setConnTargetSiteId} disabled={!!editingSiteConnId}>
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
              <div>
                <Label>Type de connexion</Label>
                <Select value={connLinkType} onValueChange={(value) => setConnLinkType(value as SiteConnection["link_type"])}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="wan">WAN</SelectItem>
                    <SelectItem value="vpn">VPN</SelectItem>
                    <SelectItem value="mpls">MPLS</SelectItem>
                    <SelectItem value="sdwan">SD-WAN</SelectItem>
                    <SelectItem value="other">Autre</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Débit</Label>
                <Select value={connBandwidth} onValueChange={setConnBandwidth}>
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="100 Mbps">100 Mbps</SelectItem>
                    <SelectItem value="1 Gbps">1 Gbps</SelectItem>
                    <SelectItem value="2.5 Gbps">2.5 Gbps</SelectItem>
                    <SelectItem value="5 Gbps">5 Gbps</SelectItem>
                    <SelectItem value="10 Gbps">10 Gbps</SelectItem>
                    <SelectItem value="25 Gbps">25 Gbps</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Description</Label>
                <Input value={connDescription} onChange={(e) => setConnDescription(e.target.value)} placeholder="IPsec tunnel, MPLS VRF…" />
              </div>
            </div>
            <DialogFooter className={editingSiteConnId ? "flex !justify-between" : ""}>
              {editingSiteConnId && (
                <Button variant="destructive" onClick={handleDeleteSiteConn} disabled={connSaving}>
                  Supprimer
                </Button>
              )}
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setSiteConnDialogOpen(false)}>Annuler</Button>
                <Button onClick={handleSaveSiteConn} disabled={connSaving}>
                  {editingSiteConnId ? "Enregistrer" : "Créer la connexion"}
                </Button>
              </div>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {detailEquipement && (() => {
                  const Icon = EQUIPEMENT_TYPE_ICONS[detailEquipement.type_equipement];
                  return <Icon className="h-5 w-5 text-primary" />;
                })()}
                {detailEquipement?.hostname || detailEquipement?.ip_address || "Chargement…"}
              </DialogTitle>
            </DialogHeader>

            {detailLoading && (
              <div className="flex items-center justify-center py-8">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              </div>
            )}

            {detailEquipement && !detailLoading && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Type</p>
                    <div className="flex items-center gap-2 mt-1">
                      {(() => {
                        const Icon = EQUIPEMENT_TYPE_ICONS[detailEquipement.type_equipement];
                        return <Icon className="h-4 w-4 text-primary" />;
                      })()}
                      <span className="text-sm font-medium">
                        {EQUIPEMENT_TYPE_LABELS[detailEquipement.type_equipement]}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Statut audit</p>
                    <Badge variant={EQUIPEMENT_STATUS_VARIANTS[detailEquipement.status_audit]} className="mt-1">
                      {EQUIPEMENT_STATUS_LABELS[detailEquipement.status_audit]}
                    </Badge>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Adresse IP</p>
                    <p className="text-sm mt-1 font-mono">{detailEquipement.ip_address}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Hostname</p>
                    <p className="text-sm mt-1">{detailEquipement.hostname || "Non renseigné"}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Site</p>
                    <Badge variant="outline" className="mt-1">
                      {sites.find((s) => s.id === detailEquipement.site_id)?.nom || `#${detailEquipement.site_id}`}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Fabricant</p>
                    <p className="text-sm mt-1">{detailEquipement.fabricant || "Non renseigné"}</p>
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-muted-foreground">OS détecté</p>
                  <p className="text-sm mt-1">{detailEquipement.os_detected || "Non renseigné"}</p>
                </div>

                {detailEquipement.type_equipement === "reseau" && detailEquipement.firmware_version && (
                  <div className="border-t pt-4">
                    <p className="text-sm font-medium text-muted-foreground mb-2">Détails réseau</p>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Firmware</p>
                      <p className="text-sm mt-1">{detailEquipement.firmware_version}</p>
                    </div>
                  </div>
                )}

                {detailEquipement.type_equipement === "serveur" && (
                  <div className="border-t pt-4 space-y-3">
                    <p className="text-sm font-medium text-muted-foreground">Détails serveur</p>
                    {detailEquipement.os_version_detail && (
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Version OS détaillée</p>
                        <p className="text-sm mt-1">{detailEquipement.os_version_detail}</p>
                      </div>
                    )}
                    {detailEquipement.modele_materiel && (
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Modèle matériel</p>
                        <p className="text-sm mt-1">{detailEquipement.modele_materiel}</p>
                      </div>
                    )}
                  </div>
                )}

                {detailEquipement.type_equipement === "firewall" && (
                  <div className="border-t pt-4 space-y-3">
                    <p className="text-sm font-medium text-muted-foreground">Détails firewall</p>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Licence</p>
                        <p className="text-sm mt-1">{detailEquipement.license_status || "—"}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Users VPN</p>
                        <p className="text-sm mt-1">{detailEquipement.vpn_users_count ?? 0}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Règles</p>
                        <p className="text-sm mt-1">{detailEquipement.rules_count ?? 0}</p>
                      </div>
                    </div>
                  </div>
                )}

                {detailEquipement.notes_audit && (
                  <div className="border-t pt-4">
                    <p className="text-sm font-medium text-muted-foreground">Notes d&apos;audit</p>
                    <p className="text-sm mt-1 whitespace-pre-wrap">{detailEquipement.notes_audit}</p>
                  </div>
                )}

                {detailAssessments.length > 0 && (
                  <div className="border-t pt-4">
                    <p className="text-sm font-medium text-muted-foreground mb-2">
                      Évaluations ({detailAssessments.length})
                    </p>
                    <div className="space-y-2">
                      {detailAssessments.map((a) => (
                        <div key={a.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                          <div>
                            <p className="text-sm font-medium">{a.framework_name}</p>
                            <p className="text-xs text-muted-foreground">
                              {a.created_at ? new Date(a.created_at).toLocaleDateString("fr-FR") : "—"}
                            </p>
                          </div>
                          <Badge variant="outline">#{a.id}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {["reseau", "switch", "router", "access_point"].includes(detailEquipement.type_equipement) && (
                  <div className="border-t pt-4 space-y-4">
                    <p className="text-sm font-medium text-muted-foreground">Configuration des ports</p>
                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">Préréglages</p>
                      <div className="flex flex-wrap gap-2">
                        <Button variant="outline" size="sm" onClick={() => handleApplyPreset("24×GigE+4×SFP+")}>24×GigE+4×SFP+</Button>
                        <Button variant="outline" size="sm" onClick={() => handleApplyPreset("48×GigE+4×SFP+")}>48×GigE+4×SFP+</Button>
                        <Button variant="outline" size="sm" onClick={() => handleApplyPreset("8×SFP+10G")}>8×SFP+10G</Button>
                        <Button variant="outline" size="sm" onClick={() => handleApplyPreset("4×SFP28-25G")}>4×SFP28-25G</Button>
                      </div>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Nom</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Vitesse</TableHead>
                            <TableHead>Rangée</TableHead>
                            <TableHead className="w-10">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {editingPorts.map((port) => (
                            <TableRow key={port.id}>
                              <TableCell>{port.name}</TableCell>
                              <TableCell>{port.type}</TableCell>
                              <TableCell>{port.speed}</TableCell>
                              <TableCell>{port.row === 0 ? "Haut (0)" : "Bas (1)"}</TableCell>
                              <TableCell>
                                <Button variant="ghost" size="sm" className="text-destructive h-8 w-8 p-0" onClick={() => handleRemovePort(port.id)}>
                                  &times;
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                          {editingPorts.length === 0 && (
                            <TableRow>
                              <TableCell colSpan={5} className="text-center text-muted-foreground py-4">
                                Aucun port configuré
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>

                    <div className="flex items-end gap-2 border p-3 rounded-md bg-muted/50">
                      <div className="grid grid-cols-4 gap-2 flex-1">
                        <div>
                          <Label className="text-xs">Nom</Label>
                          <Input className="h-8" value={newPortName} onChange={e => setNewPortName(e.target.value)} placeholder="ex: GigE 1" />
                        </div>
                        <div>
                          <Label className="text-xs">Type</Label>
                          <Select value={newPortType} onValueChange={(v) => setNewPortType(v as PortDefinition["type"])}>
                            <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="ethernet">Ethernet</SelectItem>
                              <SelectItem value="sfp">SFP</SelectItem>
                              <SelectItem value="sfp+">SFP+</SelectItem>
                              <SelectItem value="console">Console</SelectItem>
                              <SelectItem value="mgmt">Mgmt</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Vitesse</Label>
                          <Select value={newPortSpeed} onValueChange={setNewPortSpeed}>
                            <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="100 Mbps">100 Mbps</SelectItem>
                              <SelectItem value="1 Gbps">1 Gbps</SelectItem>
                              <SelectItem value="10 Gbps">10 Gbps</SelectItem>
                              <SelectItem value="25 Gbps">25 Gbps</SelectItem>
                              <SelectItem value="40 Gbps">40 Gbps</SelectItem>
                              <SelectItem value="100 Gbps">100 Gbps</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Rangée</Label>
                          <Select value={String(newPortRow)} onValueChange={v => setNewPortRow(Number(v))}>
                            <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="0">Haut (0)</SelectItem>
                              <SelectItem value="1">Bas (1)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <Button size="sm" className="h-8" onClick={handleAddPort}>Ajouter</Button>
                    </div>
                    <div className="flex justify-end pt-2">
                      <Button onClick={handleSavePorts} disabled={savingPorts}>
                        Sauvegarder les ports
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setDetailOpen(false)}>
                Fermer
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={isPortPresetConfirmOpen} onOpenChange={setIsPortPresetConfirmOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Remplacer les ports existants ?</DialogTitle>
              <DialogDescription>
                Vous êtes sur le point d&apos;appliquer un préréglage. Cela effacera les {editingPorts.length} ports actuellement configurés. Voulez-vous continuer ?
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => { setIsPortPresetConfirmOpen(false); setPendingPreset(null); }}>Annuler</Button>
              <Button variant="destructive" onClick={confirmPreset}>Remplacer</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ReactFlowProvider>
  );
}
