import dagre from "@dagrejs/dagre";
import { getNodesBounds, getViewportForBounds, type Edge, type Node } from "@xyflow/react";
import { toPng, toSvg } from "html-to-image";
import { toast } from "sonner";

import type { NetworkMap, PortDefinition, TypeEquipement } from "@/types";

export type FlowNodeData = Record<string, unknown> & {
  label: string;
  ip: string;
  type: TypeEquipement;
};

export type DetailedNodeData = FlowNodeData & {
  equipementId: number;
  ports: PortDefinition[];
  connectedPortIds: string[];
  portConnectionInfo: Record<string, { equipName: string; portName: string }>;
  vlanColorMap?: Record<number, string>;
  onPortClick?: (equipementId: number, port: PortDefinition, position?: { x: number; y: number }) => void;
};

export const edgeStyleByLinkType: Record<string, { stroke: string; strokeDasharray?: string }> = {
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

export const nodeColorByType: Record<TypeEquipement, string> = {
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

export const bandwidthShort: Record<string, string> = {
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

export function toFlowNodes(map: NetworkMap): Node<FlowNodeData>[] {
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

export function toFlowEdges(map: NetworkMap): Edge[] {
  return map.edges.map((e) => {
    const srcIf = typeof e.metadata.source_interface === "string" ? e.metadata.source_interface : "";
    const tgtIf = typeof e.metadata.target_interface === "string" ? e.metadata.target_interface : "";
    const linkType = typeof e.metadata.link_type === "string" ? e.metadata.link_type : "ethernet";
    const bw = typeof e.metadata.bandwidth === "string" ? e.metadata.bandwidth : "";

    const parts: string[] = [];
    if (srcIf && tgtIf) {
      parts.push(`${srcIf} \u2194 ${tgtIf}`);
    } else if (srcIf || tgtIf) {
      parts.push(srcIf || tgtIf);
    }
    if (bw) {
      parts.push(bandwidthShort[bw] ?? bw);
    }
    const label = parts.length > 0 ? parts.join(" \u2022 ") : linkType;

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

export function autoLayout(nodes: Node<FlowNodeData>[], edges: Edge[], direction: "TB" | "LR" = "TB"): Node<FlowNodeData>[] {
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

export function autoLayoutWithCustomDimensions(
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

export function generatePortPreset(presetType: string): PortDefinition[] {
  const ports: PortDefinition[] = [];

  switch (presetType) {
    case "24\u00d7GigE+4\u00d7SFP+": {
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
      ports.push({ id: "sfp-0-12", name: "SFP+ 25", type: "sfp+", speed: "10 Gbps", row: 0, index: 12 });
      ports.push({ id: "sfp-0-13", name: "SFP+ 26", type: "sfp+", speed: "10 Gbps", row: 0, index: 13 });
      ports.push({ id: "sfp-1-12", name: "SFP+ 27", type: "sfp+", speed: "10 Gbps", row: 1, index: 12 });
      ports.push({ id: "sfp-1-13", name: "SFP+ 28", type: "sfp+", speed: "10 Gbps", row: 1, index: 13 });
      break;
    }

    case "48\u00d7GigE+4\u00d7SFP+": {
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
      ports.push({ id: "sfp-0-24", name: "SFP+ 49", type: "sfp+", speed: "10 Gbps", row: 0, index: 24 });
      ports.push({ id: "sfp-0-25", name: "SFP+ 50", type: "sfp+", speed: "10 Gbps", row: 0, index: 25 });
      ports.push({ id: "sfp-1-24", name: "SFP+ 51", type: "sfp+", speed: "10 Gbps", row: 1, index: 24 });
      ports.push({ id: "sfp-1-25", name: "SFP+ 52", type: "sfp+", speed: "10 Gbps", row: 1, index: 25 });
      break;
    }

    case "8\u00d7SFP+10G": {
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

    case "4\u00d7SFP28-25G": {
      for (let i = 0; i < 4; i++) {
        ports.push({ id: `sfp-0-${i}`, name: `SFP+ ${i + 1}`, type: "sfp+", speed: "25 Gbps", row: 0, index: i });
      }
      break;
    }

    case "1\u00d7Ethernet": {
      ports.push({ id: "eth-0-0", name: "Eth 1", type: "ethernet", speed: "1 Gbps", row: 0, index: 0 });
      break;
    }

    case "2\u00d7Ethernet": {
      for (let i = 0; i < 2; i++) {
        ports.push({ id: `eth-0-${i}`, name: `Eth ${i + 1}`, type: "ethernet", speed: "1 Gbps", row: 0, index: i });
      }
      break;
    }

    case "4\u00d7Ethernet": {
      for (let i = 0; i < 4; i++) {
        ports.push({ id: `eth-0-${i}`, name: `Eth ${i + 1}`, type: "ethernet", speed: "1 Gbps", row: 0, index: i });
      }
      break;
    }

    case "2\u00d7Ethernet+1\u00d7Mgmt": {
      for (let i = 0; i < 2; i++) {
        ports.push({ id: `eth-0-${i}`, name: `Eth ${i + 1}`, type: "ethernet", speed: "1 Gbps", row: 0, index: i });
      }
      ports.push({ id: "mgmt-0-2", name: "Mgmt", type: "mgmt", speed: "1 Gbps", row: 0, index: 2 });
      break;
    }

    case "4\u00d7Ethernet+1\u00d7Mgmt": {
      for (let i = 0; i < 4; i++) {
        ports.push({ id: `eth-0-${i}`, name: `Eth ${i + 1}`, type: "ethernet", speed: "1 Gbps", row: 0, index: i });
      }
      ports.push({ id: "mgmt-0-4", name: "Mgmt", type: "mgmt", speed: "1 Gbps", row: 0, index: 4 });
      break;
    }

    case "8\u00d7Ethernet+1\u00d7Mgmt": {
      for (let i = 0; i < 4; i++) {
        ports.push({ id: `eth-0-${i}`, name: `Eth ${i + 1}`, type: "ethernet", speed: "1 Gbps", row: 0, index: i });
      }
      for (let i = 0; i < 4; i++) {
        ports.push({ id: `eth-1-${i}`, name: `Eth ${i + 5}`, type: "ethernet", speed: "1 Gbps", row: 1, index: i });
      }
      ports.push({ id: "mgmt-0-4", name: "Mgmt", type: "mgmt", speed: "1 Gbps", row: 0, index: 4 });
      break;
    }

    case "2\u00d7Ethernet+2\u00d7SFP+": {
      for (let i = 0; i < 2; i++) {
        ports.push({ id: `eth-0-${i}`, name: `Eth ${i + 1}`, type: "ethernet", speed: "1 Gbps", row: 0, index: i });
      }
      for (let i = 0; i < 2; i++) {
        ports.push({ id: `sfp-0-${i + 2}`, name: `SFP+ ${i + 1}`, type: "sfp+", speed: "10 Gbps", row: 0, index: i + 2 });
      }
      break;
    }

    default:
      console.warn(`Unknown preset type: ${presetType}`);
  }

  return ports;
}

export async function exportDiagramPng(flowElement: HTMLElement, nodes: Node[]): Promise<void> {
  const imageWidth = 1024;
  const imageHeight = 768;
  const padding = 50;

  const nodesBounds = getNodesBounds(nodes);
  const viewport = getViewportForBounds(nodesBounds, imageWidth, imageHeight, 0.5, 2, padding / 100);

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

export async function exportDiagramSvg(flowElement: HTMLElement, nodes: Node[]): Promise<void> {
  const imageWidth = 1024;
  const imageHeight = 768;
  const padding = 50;

  const nodesBounds = getNodesBounds(nodes);
  const viewport = getViewportForBounds(nodesBounds, imageWidth, imageHeight, 0.5, 2, padding / 100);

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
