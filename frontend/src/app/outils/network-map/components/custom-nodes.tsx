"use client";

import { useMemo, memo } from "react";
import {
  BaseEdge,
  Handle,
  Position,
  useReactFlow,
  type EdgeProps,
  type EdgeTypes,
  type Node,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import {
  Cloud,
  Cpu,
  HardDrive,
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

import type { PortDefinition, TypeEquipement } from "@/types";
import { nodeColorByType, type DetailedNodeData, type FlowNodeData } from "./map-utils";

type DeviceNodeType = Node<FlowNodeData, "device">;
type DetailedNodeType = Node<DetailedNodeData, "detailed">;

export const iconByType: Record<TypeEquipement, typeof Server> = {
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

const PARALLEL_EDGE_SPACING = 35;

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

  const portColorMap: Record<string, string> = {
    ethernet: "#6b7280",
    sfp: "#3b82f6",
    "sfp+": "#8b5cf6",
    console: "#f97316",
    mgmt: "#22c55e",
  };

  const renderPort = (port: PortDefinition) => {
    const isConnected = nodeData.connectedPortIds?.includes(port.id);
    let bgColor = portColorMap[port.type] ?? "#6b7280";
    const connInfo = nodeData.portConnectionInfo?.[port.id];

    let title = connInfo
      ? `${port.name} \u2192 ${connInfo.equipName}${connInfo.portName ? ` (${connInfo.portName})` : ""}`
      : port.name;

    const vlanColors = nodeData.vlanColorMap || {};
    let borderStyle = isConnected ? "ring-2 ring-primary z-10" : "";
    const extraStyle: React.CSSProperties = {};

    if (port.untaggedVlan) {
      title += `\nVLAN natif: ${port.untaggedVlan}`;
    }
    if (port.taggedVlans && port.taggedVlans.length > 0) {
      title += `\nVLANs tagg\u00e9s: ${port.taggedVlans.join(", ")}`;
    }

    if (port.taggedVlans && port.taggedVlans.length > 0) {
      const colors = port.taggedVlans.map(v => vlanColors[v] || "#ccc");
      if (colors.length === 1) {
        extraStyle.backgroundImage = `repeating-linear-gradient(45deg, ${colors[0]}, ${colors[0]} 4px, transparent 4px, transparent 8px)`;
      } else {
        const stops = colors.map((c, i) => `${c} ${(i * 100) / colors.length}%, ${c} ${((i + 1) * 100) / colors.length}%`).join(", ");
        extraStyle.backgroundImage = `linear-gradient(to right, ${stops})`;
      }
      bgColor = "transparent";
      if (port.untaggedVlan) {
         borderStyle = "border-2 z-10";
         extraStyle.borderColor = vlanColors[port.untaggedVlan] || "#000";
      }
    } else if (port.untaggedVlan) {
      bgColor = vlanColors[port.untaggedVlan] || "#ccc";
    }

    const innerLabel = connInfo
      ? `${connInfo.equipName}${connInfo.portName ? ` \u00b7 ${connInfo.portName}` : ""}`
      : null;

    return (
      <div
        key={port.id}
        title={title}
        className={`nodrag rounded-[2px] flex items-center justify-center overflow-hidden transition-colors ${borderStyle}`}
        style={{
          backgroundColor: bgColor,
          minWidth: 28,
          height: 22,
          padding: innerLabel ? "0 3px" : 0,
          width: innerLabel ? "auto" : 28,
          cursor: "pointer",
          ...extraStyle
        }}
        onClick={(e) => {
          e.stopPropagation();
          nodeData.onPortClick?.(nodeData.equipementId, port, { x: e.clientX, y: e.clientY });
        }}
      >
        <Handle type="target" id={`port-${port.id}-in`} position={Position.Top} className="!w-1 !h-1 !min-w-0 !min-h-0 opacity-0" />
        <Handle type="source" id={`port-${port.id}`} position={Position.Bottom} className="!w-1 !h-1 !min-w-0 !min-h-0 opacity-0" />
        {innerLabel && (
          <span className="text-[6px] leading-tight text-white font-medium whitespace-nowrap select-none pointer-events-none">
            {innerLabel}
          </span>
        )}
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
          <div className="flex gap-1 justify-center flex-wrap">
            {portsRow0.map(renderPort)}
          </div>
        )}
        {portsRow1.length > 0 && (
          <div className="flex gap-1 justify-center flex-wrap">
            {portsRow1.map(renderPort)}
          </div>
        )}
      </div>
    </div>
  );
}

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

    const midY = (sourceY + targetY) / 2 + offset;
    const r = 8;

    const dy1 = midY - sourceY;
    const dy2 = targetY - midY;
    const dxMid = targetX - sourceX;

    let d: string;
    if (Math.abs(dxMid) < 1 && Math.abs(offset) < 1) {
      d = `M ${sourceX},${sourceY} L ${targetX},${targetY}`;
    } else if (Math.abs(dxMid) < 1) {
      const jog = offset > 0 ? PARALLEL_EDGE_SPACING : -PARALLEL_EDGE_SPACING;
      const cr = Math.min(r, Math.abs(dy1) / 2, Math.abs(dy2) / 2, Math.abs(jog) / 2);
      const signJ = jog > 0 ? 1 : -1;
      const signY1 = dy1 > 0 ? 1 : -1;
      const signY2 = dy2 > 0 ? 1 : -1;
      d = [
        `M ${sourceX},${sourceY}`,
        `L ${sourceX},${midY - signY1 * cr}`,
        `Q ${sourceX},${midY} ${sourceX + signJ * cr},${midY}`,
        `L ${sourceX + jog - signJ * cr},${midY}`,
        `Q ${sourceX + jog},${midY} ${sourceX + jog},${midY + signY2 * cr}`,
        `L ${sourceX + jog},${midY + (targetY - midY) / 2 - signY2 * cr}`,
        `Q ${sourceX + jog},${midY + (targetY - midY) / 2} ${sourceX + jog - signJ * cr},${midY + (targetY - midY) / 2}`,
        `L ${targetX + signJ * cr},${midY + (targetY - midY) / 2}`,
        `Q ${targetX},${midY + (targetY - midY) / 2} ${targetX},${midY + (targetY - midY) / 2 + signY2 * cr}`,
        `L ${targetX},${targetY}`,
      ].join(" ");
    } else {
      const cr = Math.min(r, Math.abs(dy1) / 2, Math.abs(dy2) / 2, Math.abs(dxMid) / 2);
      const signX = dxMid > 0 ? 1 : -1;
      const signY1 = dy1 > 0 ? 1 : -1;
      const signY2 = dy2 > 0 ? 1 : -1;

      d = [
        `M ${sourceX},${sourceY}`,
        `L ${sourceX},${midY - signY1 * cr}`,
        `Q ${sourceX},${midY} ${sourceX + signX * cr},${midY}`,
        `L ${targetX - signX * cr},${midY}`,
        `Q ${targetX},${midY} ${targetX},${midY + signY2 * cr}`,
        `L ${targetX},${targetY}`,
      ].join(" ");
    }

    const lx = (sourceX + targetX) / 2;
    const ly = midY;

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

export const nodeTypes: NodeTypes = { device: DeviceNode, detailed: memo(DetailedEquipmentNode) };
export const edgeTypes: EdgeTypes = { parallel: ParallelEdge };
