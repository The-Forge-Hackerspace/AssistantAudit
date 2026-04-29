"use client";

import { forwardRef } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { Card, CardContent } from "@/components/ui/card";
import { nodeTypes, edgeTypes } from "@/app/outils/network-map/components/custom-nodes";
import type {
  DetailedNodeData,
  FlowNodeData,
} from "@/app/outils/network-map/components/map-utils";

/**
 * Vue ReactFlow générique utilisée par les trois onglets de la page :
 * topologie de site, vue multi-site, vue détaillée. Chaque consommateur
 * injecte ses propres callbacks et options pour respecter le comportement
 * d'origine.
 */
type AnyNode = Node<FlowNodeData | DetailedNodeData>;

interface TopologyViewProps {
  nodes: AnyNode[];
  edges: Edge[];
  onNodesChange: (changes: NodeChange<AnyNode>[]) => void;
  onEdgesChange: (changes: EdgeChange<Edge>[]) => void;
  onConnect?: (params: Edge | Connection) => void;
  onNodeDoubleClick?: (event: React.MouseEvent, node: Node<FlowNodeData>) => void;
  onEdgeDoubleClick?: (event: React.MouseEvent, edge: Edge) => void;
  onNodeDragStop?: (event: React.MouseEvent, node: Node, nodes: Node[]) => void;
  colorMode: "light" | "dark";
  nodesConnectable?: boolean;
  nodesDraggable?: boolean;
  elementsSelectable?: boolean;
}

export const TopologyView = forwardRef<HTMLDivElement, TopologyViewProps>(function TopologyView(
  {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    onNodeDoubleClick,
    onEdgeDoubleClick,
    onNodeDragStop,
    colorMode,
    nodesConnectable,
    nodesDraggable,
    elementsSelectable,
  },
  ref,
) {
  return (
    <div ref={ref}>
      <Card>
        <CardContent className="h-[70vh] p-0">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDoubleClick={
              onNodeDoubleClick as ((event: React.MouseEvent, node: Node) => void) | undefined
            }
            onEdgeDoubleClick={onEdgeDoubleClick}
            onNodeDragStop={onNodeDragStop}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            colorMode={colorMode}
            zoomOnDoubleClick={false}
            fitView
            nodesConnectable={nodesConnectable}
            nodesDraggable={nodesDraggable}
            elementsSelectable={elementsSelectable}
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </CardContent>
      </Card>
    </div>
  );
});
