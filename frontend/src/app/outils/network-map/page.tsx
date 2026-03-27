"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  ChevronDown,
  ChevronUp,
  Globe,
  Map as MapIcon,
  Network,
  Settings2,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { useTheme } from "next-themes";

import { nodeTypes, edgeTypes, iconByType } from "./components/custom-nodes";
import {
  toFlowNodes,
  toFlowEdges,
  autoLayout,
  autoLayoutWithCustomDimensions,
  generatePortPreset,
  bandwidthShort,
  edgeStyleByLinkType,
  nodeColorByType,
  exportDiagramPng,
  exportDiagramSvg,
  type FlowNodeData,
  type DetailedNodeData,
} from "./components/map-utils";
import { MapToolbar } from "./components/map-toolbar";

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
import { entreprisesApi, equipementsApi, networkMapApi, sitesApi, toolsApi, vlansApi } from "@/services/api";
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
  VlanDefinition,
  VlanDefinitionCreate,
} from "@/types";


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

  const [siteVlans, setSiteVlans] = useState<VlanDefinition[]>([]);
  const [vlanDialogOpen, setVlanDialogOpen] = useState(false);
  const [savingVlan, setSavingVlan] = useState(false);
  const [newVlanId, setNewVlanId] = useState("");
  const [newVlanName, setNewVlanName] = useState("");
  const [newVlanSubnet, setNewVlanSubnet] = useState("");
  const [newVlanColor, setNewVlanColor] = useState("#6b7280");
  const [newVlanDescription, setNewVlanDescription] = useState("");

  const [newPortName, setNewPortName] = useState("");
  const [newPortType, setNewPortType] = useState<PortDefinition["type"]>("ethernet");
  const [newPortSpeed, setNewPortSpeed] = useState("1 Gbps");
  const [newPortRow, setNewPortRow] = useState<number>(0);
  const [isPortPresetConfirmOpen, setIsPortPresetConfirmOpen] = useState(false);
  const [pendingPreset, setPendingPreset] = useState<string | null>(null);
  const [savingPorts, setSavingPorts] = useState(false);
  const [inlineEditPort, setInlineEditPort] = useState<PortDefinition | null>(null);
  const [inlineEditEquipId, setInlineEditEquipId] = useState<number | null>(null);
  const [inlineEditPosition, setInlineEditPosition] = useState<{ x: number; y: number } | null>(null);
  const [vlanPanelExpanded, setVlanPanelExpanded] = useState(false);

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

  const loadVlans = useCallback(async (siteId: number) => {
    try {
      const vlans = await vlansApi.list(siteId);
      setSiteVlans(vlans);
    } catch { /* VLANs table may not exist yet */ }
  }, []);

  const handleCreateVlan = useCallback(async () => {
    if (!selectedSiteId || !newVlanId || !newVlanName) return;
    setSavingVlan(true);
    try {
      await vlansApi.create({
        site_id: Number(selectedSiteId),
        vlan_id: parseInt(newVlanId),
        name: newVlanName,
        subnet: newVlanSubnet || null,
        color: newVlanColor,
        description: newVlanDescription || null,
      });
      toast.success("VLAN créé");
      setNewVlanId("");
      setNewVlanName("");
      setNewVlanSubnet("");
      setNewVlanColor("#6b7280");
      setNewVlanDescription("");
      await loadVlans(Number(selectedSiteId));
    } catch {
      toast.error("Impossible de créer le VLAN");
    } finally {
      setSavingVlan(false);
    }
  }, [selectedSiteId, newVlanId, newVlanName, newVlanSubnet, newVlanColor, newVlanDescription, loadVlans]);

  const handleDeleteVlan = useCallback(async (vlanDefId: number) => {
    if (!selectedSiteId) return;
    try {
      await vlansApi.delete(vlanDefId);
      toast.success("VLAN supprimé");
      await loadVlans(Number(selectedSiteId));
    } catch {
      toast.error("Impossible de supprimer le VLAN");
    }
  }, [selectedSiteId, loadVlans]);

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
  const detailedSaveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handlePortClick = useCallback((equipementId: number, port: PortDefinition, position?: { x: number; y: number }) => {
    setInlineEditPort({
      ...port,
      untaggedVlan: port.untaggedVlan ?? null,
      taggedVlans: [...(port.taggedVlans || [])],
    });
    setInlineEditEquipId(equipementId);
    setInlineEditPosition(position ?? null);
    if (siteVlans.length === 0 && selectedSiteId) {
      loadVlans(selectedSiteId);
    }
  }, [siteVlans.length, selectedSiteId, loadVlans]);

  const handlePortClickRef = useRef(handlePortClick);
  handlePortClickRef.current = handlePortClick;

  const closeInlineEdit = useCallback(() => {
    setInlineEditPort(null);
    setInlineEditEquipId(null);
    setInlineEditPosition(null);
  }, []);

  const handleSaveDetailedLayout = useCallback(async (nodesToSave?: Node<DetailedNodeData | FlowNodeData>[]) => {
    if (!selectedSiteId) return;
    const currentNodes = nodesToSave ?? detailedNodes;
    const existingLayoutData = siteMap?.layout_data ?? {};
    try {
      await networkMapApi.saveSiteLayout(selectedSiteId, {
        ...existingLayoutData,
        detailed_nodes: currentNodes.map((n) => ({ id: n.id, x: n.position.x, y: n.position.y })),
      });
      toast.success("Layout détaillé sauvegardé");
    } catch (error) {
      console.error(error);
      toast.error("Échec de sauvegarde du layout détaillé");
    }
  }, [selectedSiteId, detailedNodes, siteMap]);

  const onDetailedNodeDragStop = useCallback((_: React.MouseEvent, __: Node, nodesAfterDrag: Node[]) => {
    if (detailedSaveTimeoutRef.current) {
      clearTimeout(detailedSaveTimeoutRef.current);
    }
    detailedSaveTimeoutRef.current = setTimeout(() => {
      handleSaveDetailedLayout(nodesAfterDrag as Node<DetailedNodeData | FlowNodeData>[]);
    }, 500);
  }, [handleSaveDetailedLayout]);

  const handleSaveInlinePort = useCallback(async () => {
    if (!inlineEditPort || !inlineEditEquipId) return;
    try {
      const equipment = await equipementsApi.get(inlineEditEquipId);
      const currentPorts = equipment.ports_status || [];
      const updatedPorts = currentPorts.map((port) => {
        if (port.id !== inlineEditPort.id) return port;
        return {
          ...port,
          untaggedVlan: inlineEditPort.untaggedVlan ?? null,
          taggedVlans: [...(inlineEditPort.taggedVlans || [])],
        };
      });

      await equipementsApi.update(inlineEditEquipId, { ports_status: updatedPorts });

      setDetailedNodes((curr) =>
        curr.map((node) => {
          if (node.type !== "detailed") return node;
          const data = node.data as DetailedNodeData;
          if (data.equipementId !== inlineEditEquipId) return node;
          return {
            ...node,
            data: {
              ...data,
              ports: updatedPorts,
              vlanColorMap: siteVlans.reduce((acc, v) => {
                acc[v.vlan_id] = v.color;
                return acc;
              }, {} as Record<number, string>),
            },
          };
        }),
      );

      setDetailEquipement((prev) => {
        if (!prev || prev.id !== inlineEditEquipId) return prev;
        return { ...prev, ports_status: updatedPorts };
      });
      setEditingPorts((prev) => {
        if (!detailEquipement || detailEquipement.id !== inlineEditEquipId) return prev;
        return updatedPorts;
      });

      toast.success("Port mis à jour");
      closeInlineEdit();
    } catch (error) {
      console.error(error);
      toast.error("Impossible de mettre à jour le port");
    }
  }, [inlineEditPort, inlineEditEquipId, setDetailedNodes, siteVlans, detailEquipement, closeInlineEdit]);

  useEffect(() => {
    return () => {
      if (detailedSaveTimeoutRef.current) {
        clearTimeout(detailedSaveTimeoutRef.current);
      }
    };
  }, []);

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
    let vlans: VlanDefinition[] = [];
    try { vlans = await vlansApi.list(siteId); setSiteVlans(vlans); } catch { /* VLANs not available yet */ }

    const equipmentDetailsResults = await Promise.allSettled(
      data.nodes.map((node) => equipementsApi.get(node.equipement_id))
    );

    const equipmentMap = new Map<number, Equipement>();
    equipmentDetailsResults.forEach((result) => {
      if (result.status === "fulfilled") {
        equipmentMap.set(result.value.id, result.value);
      }
    });

    const connectedPortIds = new Set<string>();
    const portConnectionInfoByEquipId = new Map<number, Record<string, { equipName: string; portName: string }>>();

    links.forEach((link) => {
      if (link.source_interface) connectedPortIds.add(link.source_interface);
      if (link.target_interface) connectedPortIds.add(link.target_interface);

      const srcEquip = equipmentMap.get(link.source_equipement_id);
      const tgtEquip = equipmentMap.get(link.target_equipement_id);
      const srcPorts: PortDefinition[] = srcEquip?.ports_status || [];
      const tgtPorts: PortDefinition[] = tgtEquip?.ports_status || [];

      if (link.source_interface && tgtEquip) {
        if (!portConnectionInfoByEquipId.has(link.source_equipement_id)) {
          portConnectionInfoByEquipId.set(link.source_equipement_id, {});
        }
        const tgtPortName = tgtPorts.find(p => p.id === link.target_interface)?.name ?? link.target_interface ?? "";
        portConnectionInfoByEquipId.get(link.source_equipement_id)![link.source_interface] = {
          equipName: tgtEquip.hostname || tgtEquip.ip_address,
          portName: tgtPortName,
        };
      }
      if (link.target_interface && srcEquip) {
        if (!portConnectionInfoByEquipId.has(link.target_equipement_id)) {
          portConnectionInfoByEquipId.set(link.target_equipement_id, {});
        }
        const srcPortName = srcPorts.find(p => p.id === link.source_interface)?.name ?? link.source_interface ?? "";
        portConnectionInfoByEquipId.get(link.target_equipement_id)![link.target_interface] = {
          equipName: srcEquip.hostname || srcEquip.ip_address,
          portName: srcPortName,
        };
      }
    });

    const vlanColors = vlans.reduce((acc, v) => { acc[v.vlan_id] = v.color; return acc; }, {} as Record<number, string>);
    const detailedPositions = new Map((data.layout_data?.detailed_nodes || []).map((n) => [n.id, { x: n.x, y: n.y }]));
    const topologyPositions = new Map((data.layout_data?.nodes || []).map((n) => [n.id, { x: n.x, y: n.y }]));

    const detailedNodesArray: Node<DetailedNodeData | FlowNodeData>[] = data.nodes.map((node) => {
      const equipment = equipmentMap.get(node.equipement_id);
      const ports = equipment?.ports_status || [];
      const hasPorts = ports.length > 0;

      const equipmentConnectedPortIds = ports
        .map((p: PortDefinition) => p.id)
        .filter((id: string) => connectedPortIds.has(id));

      const saved = detailedPositions.get(node.id) ?? topologyPositions.get(node.id) ?? { x: 0, y: 0 };

      if (hasPorts) {
        return {
          id: node.id,
          type: "detailed",
          data: {
            label: node.label,
            ip: node.ip_address,
            type: node.type_equipement,
            equipementId: node.equipement_id,
            ports,
            connectedPortIds: equipmentConnectedPortIds,
            portConnectionInfo: portConnectionInfoByEquipId.get(node.equipement_id) ?? {},
            vlanColorMap: vlanColors,
            onPortClick: handlePortClickRef.current,
          },
          position: saved,
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
          position: saved,
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
    if (selectedSiteId) loadVlans(Number(selectedSiteId));
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
  }, [selectedSiteId, loadVlans]);

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
            <MapToolbar
              tab="site"
              layoutDirection={layoutDirection}
              onAutoLayout={(dir) => handleAutoLayout(dir)}
              onToggleDirection={() => {
                const next = layoutDirection === "TB" ? "LR" : "TB";
                setLayoutDirection(next);
                handleAutoLayout(next);
              }}
              onSaveLayout={handleSaveLayout}
              onAddLink={() => { resetLinkForm(); setLinkDialogOpen(true); }}
              onReload={() => { if (selectedSiteId) loadSiteMap(selectedSiteId); }}
              onExportPng={() => { if (siteFlowRef.current) exportDiagramPng(siteFlowRef.current, nodes); }}
              onExportSvg={() => { if (siteFlowRef.current) exportDiagramSvg(siteFlowRef.current, nodes); }}
            />

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
            <MapToolbar
              tab="overview"
              layoutDirection={layoutDirection}
              onAutoLayout={(dir) => handleAutoLayout(dir)}
              onToggleDirection={() => {
                const next = layoutDirection === "TB" ? "LR" : "TB";
                setLayoutDirection(next);
                handleAutoLayout(next);
              }}
              onSaveLayout={handleSaveLayout}
              onAddLink={() => { resetLinkForm(); setLinkDialogOpen(true); }}
              onReload={() => { if (selectedEntrepriseId) loadOverview(selectedEntrepriseId); }}
              onExportPng={() => { if (overviewFlowRef.current) exportDiagramPng(overviewFlowRef.current, overviewNodes); }}
              onExportSvg={() => { if (overviewFlowRef.current) exportDiagramSvg(overviewFlowRef.current, overviewNodes); }}
              onAddSiteConnection={() => { resetSiteConnForm(); setSiteConnDialogOpen(true); }}
            />

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
            <MapToolbar
              tab="detailed"
              layoutDirection={layoutDirection}
              onAutoLayout={(dir) => handleAutoLayout(dir)}
              onToggleDirection={() => {
                const next = layoutDirection === "TB" ? "LR" : "TB";
                setLayoutDirection(next);
                handleAutoLayout(next);
              }}
              onSaveLayout={handleSaveLayout}
              onAddLink={() => { resetLinkForm(); setLinkDialogOpen(true); }}
              onReload={() => { if (selectedSiteId) loadSiteMap(selectedSiteId); }}
              onExportPng={() => { if (siteFlowRef.current) exportDiagramPng(siteFlowRef.current, nodes); }}
              onExportSvg={() => { if (siteFlowRef.current) exportDiagramSvg(siteFlowRef.current, nodes); }}
              onAutoLayoutDetailed={() => {
                const layoutedNodes = autoLayoutWithCustomDimensions(detailedNodes, detailedEdges, layoutDirection);
                setDetailedNodes(layoutedNodes);
              }}
              onSaveDetailedLayout={() => handleSaveDetailedLayout()}
              onReloadDetailed={() => {
                if (!selectedSiteId) {
                  toast.error("Aucun site sélectionné");
                  return;
                }
                loadDetailedView(selectedSiteId);
              }}
              onExportDetailedPng={() => { if (detailedFlowRef.current) exportDiagramPng(detailedFlowRef.current, detailedNodes); }}
              onExportDetailedSvg={() => { if (detailedFlowRef.current) exportDiagramSvg(detailedFlowRef.current, detailedNodes); }}
            />

            <div ref={detailedFlowRef}>
              <Card>
                <CardContent className="h-[70vh] p-0">
                  <ReactFlow
                    nodes={detailedNodes}
                    edges={detailedEdges}
                    onNodesChange={onDetailedNodesChange}
                    onEdgesChange={onDetailedEdgesChange}
                    onNodeDragStop={onDetailedNodeDragStop}
                    onNodeDoubleClick={onNodeDoubleClick}
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
            <div className="rounded-md border bg-card">
              <button
                type="button"
                className="w-full flex items-center justify-between px-3 py-2 text-sm"
                onClick={() => setVlanPanelExpanded((prev) => !prev)}
              >
                <span className="font-medium">VLANs ({siteVlans.length})</span>
                {vlanPanelExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
              </button>
              {vlanPanelExpanded && (
                <div className="border-t px-3 py-3 space-y-3">
                  {siteVlans.length > 0 ? (
                    <div className="space-y-2">
                      {siteVlans.map((v) => (
                        <div key={v.id} className="grid grid-cols-[16px_56px_minmax(120px,1fr)_minmax(120px,1fr)] gap-3 items-start text-xs">
                          <div className="w-4 h-4 rounded-sm border" style={{ backgroundColor: v.color }} />
                          <span className="font-mono font-bold leading-4">{v.vlan_id}</span>
                          <div>
                            <div className="font-medium text-foreground">{v.name}</div>
                            {v.description && <div className="text-muted-foreground">{v.description}</div>}
                          </div>
                          <div className="font-mono text-muted-foreground">{v.subnet || "—"}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-muted-foreground">Aucun VLAN défini pour ce site.</div>
                  )}
                  <div className="pt-1">
                    <Button variant="outline" size="sm" onClick={() => setVlanDialogOpen(true)}>
                      Gérer les VLANs
                    </Button>
                  </div>
                </div>
              )}
            </div>
            {siteMap && (
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <Network className="h-4 w-4" />
                {detailedNodes.length} équipement(s), {detailedEdges.length} lien(s)
              </div>
            )}

            {inlineEditPort && inlineEditEquipId && inlineEditPosition && (
              <>
                <div className="fixed inset-0 z-40" onClick={closeInlineEdit} />
                <div
                  className="fixed z-50 w-[320px] rounded-md border bg-card p-3 shadow-xl space-y-3"
                  style={{ left: inlineEditPosition.x + 8, top: inlineEditPosition.y + 8 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <div>
                    <p className="text-sm font-medium">{inlineEditPort.name}</p>
                    <p className="text-xs text-muted-foreground">
                      VLAN natif: {inlineEditPort.untaggedVlan ?? "Aucun"}
                      {" · "}
                      VLANs taggés: {(inlineEditPort.taggedVlans || []).length > 0 ? inlineEditPort.taggedVlans?.join(", ") : "Aucun"}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">VLAN natif</Label>
                    <Select
                      value={inlineEditPort.untaggedVlan ? String(inlineEditPort.untaggedVlan) : "none"}
                      onValueChange={(value) => {
                        setInlineEditPort((prev) => {
                          if (!prev) return prev;
                          return {
                            ...prev,
                            untaggedVlan: value === "none" ? null : parseInt(value),
                          };
                        });
                      }}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue placeholder="Aucun" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Aucun</SelectItem>
                        {siteVlans.map((v) => (
                          <SelectItem key={v.vlan_id} value={String(v.vlan_id)}>
                            {v.vlan_id} - {v.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">VLANs taggés</Label>
                    <div className="max-h-28 overflow-auto rounded border p-2 space-y-1">
                      {siteVlans.length > 0 ? siteVlans.map((v) => (
                        <label key={v.vlan_id} className="flex items-center gap-2 text-xs">
                          <input
                            type="checkbox"
                            checked={(inlineEditPort.taggedVlans || []).includes(v.vlan_id)}
                            onChange={(e) => {
                              setInlineEditPort((prev) => {
                                if (!prev) return prev;
                                const current = prev.taggedVlans || [];
                                const taggedVlans = e.target.checked
                                  ? [...current, v.vlan_id]
                                  : current.filter((id) => id !== v.vlan_id);
                                return { ...prev, taggedVlans };
                              });
                            }}
                          />
                          <span>{v.vlan_id} - {v.name}</span>
                        </label>
                      )) : <div className="text-xs text-muted-foreground">Aucun VLAN disponible</div>}
                    </div>
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={closeInlineEdit}>Annuler</Button>
                    <Button size="sm" onClick={handleSaveInlinePort}>Sauvegarder</Button>
                  </div>
                </div>
              </>
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
                      value={selectedSourcePortId || "__none__"} 
                      onValueChange={(value) => {
                        const resolved = value === "__none__" ? "" : value;
                        setSelectedSourcePortId(resolved);
                        if (resolved) {
                          const port = sourceEquipPorts.find(p => p.id === resolved);
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
                        <SelectItem value="__none__">Aucun</SelectItem>
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
                        value={selectedTargetPortId || "__none__"} 
                        onValueChange={(value) => {
                          const resolved = value === "__none__" ? "" : value;
                          setSelectedTargetPortId(resolved);
                          if (resolved) {
                            const port = targetEquipPorts.find(p => p.id === resolved);
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
                          <SelectItem value="__none__">Aucun</SelectItem>
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
                    value={selectedTargetPortId || "__none__"} 
                    onValueChange={(value) => {
                      const resolved = value === "__none__" ? "" : value;
                      setSelectedTargetPortId(resolved);
                      if (resolved) {
                        const port = targetEquipPorts.find(p => p.id === resolved);
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
                      <SelectItem value="__none__">Aucun</SelectItem>
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

                {detailEquipement && (
                  <div className="border-t pt-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-muted-foreground">Configuration des ports</p>
                      <Button variant="outline" size="sm" onClick={() => { if (selectedSiteId) { loadVlans(selectedSiteId); } setVlanDialogOpen(true); }}>
                        Gérer les VLANs
                      </Button>
                    </div>
                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">Préréglages</p>
                      <div className="flex flex-wrap gap-2">
                        {["reseau", "switch", "router", "access_point"].includes(detailEquipement.type_equipement) && (
                          <>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("24×GigE+4×SFP+")}>24×GigE+4×SFP+</Button>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("48×GigE+4×SFP+")}>48×GigE+4×SFP+</Button>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("8×SFP+10G")}>8×SFP+10G</Button>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("4×SFP28-25G")}>4×SFP28-25G</Button>
                          </>
                        )}
                        {["serveur", "hyperviseur", "nas"].includes(detailEquipement.type_equipement) && (
                          <>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("2×Ethernet")}>2×Ethernet</Button>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("4×Ethernet")}>4×Ethernet</Button>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("2×Ethernet+1×Mgmt")}>2×Ethernet+1×Mgmt</Button>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("4×Ethernet+1×Mgmt")}>4×Ethernet+1×Mgmt</Button>
                          </>
                        )}
                        {detailEquipement.type_equipement === "firewall" && (
                          <>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("4×Ethernet+1×Mgmt")}>4×Ethernet+1×Mgmt</Button>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("8×Ethernet+1×Mgmt")}>8×Ethernet+1×Mgmt</Button>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("2×Ethernet+2×SFP+")}>2×Ethernet+2×SFP+</Button>
                          </>
                        )}
                        {["printer", "camera", "telephone", "iot", "cloud_gateway", "equipement"].includes(detailEquipement.type_equipement) && (
                          <>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("1×Ethernet")}>1×Ethernet</Button>
                            <Button variant="outline" size="sm" onClick={() => handleApplyPreset("2×Ethernet")}>2×Ethernet</Button>
                          </>
                        )}
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
                            <TableHead>VLAN Natif</TableHead>
                            <TableHead>VLANs Taggés</TableHead>
                            <TableHead className="w-10">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {editingPorts.map((port, idx) => (
                            <TableRow key={port.id}>
                              <TableCell>{port.name}</TableCell>
                              <TableCell>{port.type}</TableCell>
                              <TableCell>{port.speed}</TableCell>
                              <TableCell>{port.row === 0 ? "Haut (0)" : "Bas (1)"}</TableCell>
                              <TableCell>
                                <Select
                                  value={port.untaggedVlan ? String(port.untaggedVlan) : "none"}
                                  onValueChange={(val) => {
                                    const newPorts = [...editingPorts];
                                    newPorts[idx].untaggedVlan = val === "none" ? null : parseInt(val);
                                    setEditingPorts(newPorts);
                                  }}
                                >
                                  <SelectTrigger className="w-[120px] h-8">
                                    <SelectValue placeholder="Aucun" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="none">Aucun</SelectItem>
                                    {siteVlans.map(v => (
                                      <SelectItem key={v.vlan_id} value={String(v.vlan_id)}>
                                        {v.vlan_id} - {v.name}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </TableCell>
                              <TableCell>
                                <div className="flex flex-wrap gap-2 max-w-[200px]">
                                  {siteVlans.map(v => (
                                    <label key={v.vlan_id} className="flex items-center space-x-1 text-xs whitespace-nowrap">
                                      <input
                                        type="checkbox"
                                        checked={(port.taggedVlans || []).includes(v.vlan_id)}
                                        onChange={(e) => {
                                          const newPorts = [...editingPorts];
                                          const current = newPorts[idx].taggedVlans || [];
                                          if (e.target.checked) {
                                            newPorts[idx].taggedVlans = [...current, v.vlan_id];
                                          } else {
                                            newPorts[idx].taggedVlans = current.filter(id => id !== v.vlan_id);
                                          }
                                          setEditingPorts(newPorts);
                                        }}
                                      />
                                      <span>{v.vlan_id}</span>
                                    </label>
                                  ))}
                                </div>
                              </TableCell>
                              <TableCell>
                                <Button variant="ghost" size="sm" className="text-destructive h-8 w-8 p-0" onClick={() => handleRemovePort(port.id)}>
                                  &times;
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                          {editingPorts.length === 0 && (
                            <TableRow>
                              <TableCell colSpan={7} className="text-center text-muted-foreground py-4">
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

        <Dialog open={vlanDialogOpen} onOpenChange={setVlanDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Gestion des VLANs</DialogTitle>
              <DialogDescription>
                Définir les VLANs disponibles pour ce site. Ils pourront être assignés aux ports des équipements.
              </DialogDescription>
            </DialogHeader>

            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">Couleur</TableHead>
                    <TableHead>ID</TableHead>
                    <TableHead>Nom</TableHead>
                    <TableHead>Sous-réseau</TableHead>
                    <TableHead className="w-10">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {siteVlans.map(v => (
                    <TableRow key={v.id}>
                      <TableCell>
                        <div className="w-5 h-5 rounded border" style={{ backgroundColor: v.color }} />
                      </TableCell>
                      <TableCell className="font-mono">{v.vlan_id}</TableCell>
                      <TableCell>{v.name}</TableCell>
                      <TableCell className="font-mono text-xs">{v.subnet || "—"}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" className="text-destructive h-8 w-8 p-0" onClick={() => handleDeleteVlan(v.id)}>
                          &times;
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {siteVlans.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-4">
                        Aucun VLAN défini
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>

            <div className="flex items-end gap-2 border p-3 rounded-md bg-muted/50">
              <div className="grid grid-cols-5 gap-2 flex-1">
                <div>
                  <Label className="text-xs">ID VLAN</Label>
                  <Input className="h-8" type="number" min={1} max={4094} value={newVlanId} onChange={e => setNewVlanId(e.target.value)} placeholder="10" />
                </div>
                <div>
                  <Label className="text-xs">Nom</Label>
                  <Input className="h-8" value={newVlanName} onChange={e => setNewVlanName(e.target.value)} placeholder="Management" />
                </div>
                <div>
                  <Label className="text-xs">Sous-réseau</Label>
                  <Input className="h-8" value={newVlanSubnet} onChange={e => setNewVlanSubnet(e.target.value)} placeholder="192.168.10.0/24" />
                </div>
                <div>
                  <Label className="text-xs">Couleur</Label>
                  <input type="color" className="h-8 w-full rounded border cursor-pointer" value={newVlanColor} onChange={e => setNewVlanColor(e.target.value)} />
                </div>
                <div>
                  <Label className="text-xs">Description</Label>
                  <Input className="h-8" value={newVlanDescription} onChange={e => setNewVlanDescription(e.target.value)} placeholder="Optionnel" />
                </div>
              </div>
              <Button size="sm" className="h-8" onClick={handleCreateVlan} disabled={savingVlan || !newVlanId || !newVlanName}>
                Ajouter
              </Button>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setVlanDialogOpen(false)}>Fermer</Button>
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
