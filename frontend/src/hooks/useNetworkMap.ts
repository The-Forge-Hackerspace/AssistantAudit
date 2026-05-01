"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import { toast } from "sonner";

import {
  toFlowNodes,
  toFlowEdges,
  autoLayout,
  autoLayoutWithCustomDimensions,
  generatePortPreset,
  bandwidthShort,
  edgeStyleByLinkType,
  type FlowNodeData,
  type DetailedNodeData,
} from "@/app/outils/network-map/components/map-utils";
import {
  entreprisesApi,
  equipementsApi,
  networkMapApi,
  sitesApi,
  toolsApi,
  vlansApi,
} from "@/services/api";
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
  VlanDefinition,
} from "@/types";

/**
 * Hook central — état + actions de la cartographie réseau.
 * Toute la logique métier de la page est encapsulée ici afin que les
 * composants présentationnels (TopologyView, ConnectionForm, etc.) ne
 * voient que des slices ciblés.
 */
export function useNetworkMap() {
  // ---------------------------------------------------------------------------
  // Données distantes (entreprises / sites / cartes)
  // ---------------------------------------------------------------------------
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedEntrepriseId, setSelectedEntrepriseId] = useState<number | null>(null);
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null);
  const [siteMap, setSiteMap] = useState<NetworkMap | null>(null);
  const [overview, setOverview] = useState<MultiSiteOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"site" | "overview" | "detailed">("site");
  const [layoutDirection, setLayoutDirection] = useState<"TB" | "LR">("TB");

  // ---------------------------------------------------------------------------
  // Détail équipement / ports
  // ---------------------------------------------------------------------------
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
  const [inlineEditPort, setInlineEditPort] = useState<PortDefinition | null>(null);
  const [inlineEditEquipId, setInlineEditEquipId] = useState<number | null>(null);
  const [inlineEditPosition, setInlineEditPosition] = useState<{ x: number; y: number } | null>(null);
  const [vlanPanelExpanded, setVlanPanelExpanded] = useState(false);

  // ---------------------------------------------------------------------------
  // VLANs
  // ---------------------------------------------------------------------------
  const [siteVlans, setSiteVlans] = useState<VlanDefinition[]>([]);
  const [vlanDialogOpen, setVlanDialogOpen] = useState(false);
  const [savingVlan, setSavingVlan] = useState(false);
  const [newVlanId, setNewVlanId] = useState("");
  const [newVlanName, setNewVlanName] = useState("");
  const [newVlanSubnet, setNewVlanSubnet] = useState("");
  const [newVlanColor, setNewVlanColor] = useState("#6b7280");
  const [newVlanDescription, setNewVlanDescription] = useState("");

  // ---------------------------------------------------------------------------
  // Formulaire lien intra-site
  // ---------------------------------------------------------------------------
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
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

  // ---------------------------------------------------------------------------
  // Formulaire connexion inter-site
  // ---------------------------------------------------------------------------
  const [siteConnDialogOpen, setSiteConnDialogOpen] = useState(false);
  const [editingSiteConnId, setEditingSiteConnId] = useState<number | null>(null);
  const [connSourceSiteId, setConnSourceSiteId] = useState<string>("");
  const [connTargetSiteId, setConnTargetSiteId] = useState<string>("");
  const [connLinkType, setConnLinkType] = useState<SiteConnection["link_type"]>("wan");
  const [connBandwidth, setConnBandwidth] = useState("");
  const [connDescription, setConnDescription] = useState("");
  const [connSaving, setConnSaving] = useState(false);

  // ---------------------------------------------------------------------------
  // Flow states (3 vues ReactFlow)
  // ---------------------------------------------------------------------------
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<FlowNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [overviewNodes, setOverviewNodes, onOverviewNodesChange] = useNodesState<Node<FlowNodeData>>([]);
  const [overviewEdges, setOverviewEdges, onOverviewEdgesChange] = useEdgesState<Edge>([]);
  const [detailedNodes, setDetailedNodes, onDetailedNodesChange] = useNodesState<Node<DetailedNodeData | FlowNodeData>>([]);
  const [detailedEdges, setDetailedEdges, onDetailedEdgesChange] = useEdgesState<Edge>([]);

  const detailedSaveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ---------------------------------------------------------------------------
  // Effets — édition inline / detail dialog
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (detailEquipement) {
      setEditingPorts(detailEquipement.ports_status || []);
    } else {
      setEditingPorts([]);
    }
  }, [detailEquipement]);

  // ---------------------------------------------------------------------------
  // Ports — préréglages, ajout, suppression, sauvegarde
  // ---------------------------------------------------------------------------
  const handleAddPort = useCallback(() => {
    if (!newPortName.trim()) return;
    const id = newPortName.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
    const maxIndex = Math.max(-1, ...editingPorts.filter((p) => p.row === newPortRow).map((p) => p.index));
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

  const handleApplyPreset = useCallback(
    (preset: string) => {
      if (editingPorts.length > 0) {
        setPendingPreset(preset);
        setIsPortPresetConfirmOpen(true);
      } else {
        setEditingPorts(generatePortPreset(preset));
      }
    },
    [editingPorts.length],
  );

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
      setDetailEquipement((prev) => (prev ? { ...prev, ports_status: editingPorts } : null));
    } catch (error) {
      console.error(error);
      toast.error("Impossible de sauvegarder les ports");
    } finally {
      setSavingPorts(false);
    }
  }, [detailEquipement, editingPorts]);

  // ---------------------------------------------------------------------------
  // VLANs — CRUD
  // ---------------------------------------------------------------------------
  const loadVlans = useCallback(async (siteId: number) => {
    try {
      const vlans = await vlansApi.list(siteId);
      setSiteVlans(vlans);
    } catch {
      /* table VLAN éventuellement absente */
    }
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
  }, [
    selectedSiteId,
    newVlanId,
    newVlanName,
    newVlanSubnet,
    newVlanColor,
    newVlanDescription,
    loadVlans,
  ]);

  const handleDeleteVlan = useCallback(
    async (vlanDefId: number) => {
      if (!selectedSiteId) return;
      try {
        await vlansApi.delete(vlanDefId);
        toast.success("VLAN supprimé");
        await loadVlans(Number(selectedSiteId));
      } catch {
        toast.error("Impossible de supprimer le VLAN");
      }
    },
    [selectedSiteId, loadVlans],
  );

  // ---------------------------------------------------------------------------
  // Édition inline d'un port
  // ---------------------------------------------------------------------------
  const handlePortClick = useCallback(
    (equipementId: number, port: PortDefinition, position?: { x: number; y: number }) => {
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
    },
    [siteVlans.length, selectedSiteId, loadVlans],
  );

  const handlePortClickRef = useRef(handlePortClick);
  handlePortClickRef.current = handlePortClick;

  const closeInlineEdit = useCallback(() => {
    setInlineEditPort(null);
    setInlineEditEquipId(null);
    setInlineEditPosition(null);
  }, []);

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
  }, [
    inlineEditPort,
    inlineEditEquipId,
    setDetailedNodes,
    siteVlans,
    detailEquipement,
    closeInlineEdit,
  ]);

  // Cleanup du timeout de sauvegarde du layout détaillé
  useEffect(() => {
    return () => {
      if (detailedSaveTimeoutRef.current) {
        clearTimeout(detailedSaveTimeoutRef.current);
      }
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Liste des équipements du site (utilisée par le formulaire de lien)
  // ---------------------------------------------------------------------------
  const siteEquipements = useMemo(() => {
    if (!siteMap) return [];
    return siteMap.nodes;
  }, [siteMap]);

  // ---------------------------------------------------------------------------
  // Chargements
  // ---------------------------------------------------------------------------
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

  const loadSiteMap = useCallback(
    async (siteId: number) => {
      const data = await networkMapApi.getSiteMap(siteId);
      setSiteMap(data);
      const nextNodes = toFlowNodes(data);
      const nextEdges = toFlowEdges(data);
      const hasSavedPositions = nextNodes.some((n) => n.position.x !== 0 || n.position.y !== 0);
      setNodes(hasSavedPositions ? nextNodes : autoLayout(nextNodes, nextEdges, layoutDirection));
      setEdges(nextEdges);
    },
    [setEdges, setNodes, layoutDirection],
  );

  const loadOverview = useCallback(
    async (entrepriseId: number) => {
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
    },
    [setOverviewEdges, setOverviewNodes],
  );

  const loadDetailedView = useCallback(
    async (siteId: number) => {
      const data = await networkMapApi.getSiteMap(siteId);
      setSiteMap(data);

      const links = await networkMapApi.listLinks(siteId);
      let vlans: VlanDefinition[] = [];
      try {
        vlans = await vlansApi.list(siteId);
        setSiteVlans(vlans);
      } catch {
        /* VLANs non disponibles */
      }

      const equipmentDetailsResults = await Promise.allSettled(
        data.nodes.map((node) => equipementsApi.get(node.equipement_id)),
      );

      const equipmentMap = new Map<number, Equipement>();
      equipmentDetailsResults.forEach((result) => {
        if (result.status === "fulfilled") {
          equipmentMap.set(result.value.id, result.value);
        }
      });

      const connectedPortIds = new Set<string>();
      const portConnectionInfoByEquipId = new Map<
        number,
        Record<string, { equipName: string; portName: string }>
      >();

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
          const tgtPortName =
            tgtPorts.find((p) => p.id === link.target_interface)?.name ?? link.target_interface ?? "";
          portConnectionInfoByEquipId.get(link.source_equipement_id)![link.source_interface] = {
            equipName: tgtEquip.hostname || tgtEquip.ip_address,
            portName: tgtPortName,
          };
        }
        if (link.target_interface && srcEquip) {
          if (!portConnectionInfoByEquipId.has(link.target_equipement_id)) {
            portConnectionInfoByEquipId.set(link.target_equipement_id, {});
          }
          const srcPortName =
            srcPorts.find((p) => p.id === link.source_interface)?.name ?? link.source_interface ?? "";
          portConnectionInfoByEquipId.get(link.target_equipement_id)![link.target_interface] = {
            equipName: srcEquip.hostname || srcEquip.ip_address,
            portName: srcPortName,
          };
        }
      });

      const vlanColors = vlans.reduce((acc, v) => {
        acc[v.vlan_id] = v.color;
        return acc;
      }, {} as Record<number, string>);
      const detailedPositions = new Map(
        (data.layout_data?.detailed_nodes || []).map((n) => [n.id, { x: n.x, y: n.y }]),
      );
      const topologyPositions = new Map(
        (data.layout_data?.nodes || []).map((n) => [n.id, { x: n.x, y: n.y }]),
      );

      const detailedNodesArray: Node<DetailedNodeData | FlowNodeData>[] = data.nodes.map((node) => {
        const equipment = equipmentMap.get(node.equipement_id);
        const ports = equipment?.ports_status || [];
        const hasPorts = ports.length > 0;

        const equipmentConnectedPortIds = ports
          .map((p: PortDefinition) => p.id)
          .filter((id: string) => connectedPortIds.has(id));

        const saved =
          detailedPositions.get(node.id) ?? topologyPositions.get(node.id) ?? { x: 0, y: 0 };

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

      const nodeByEquipId = new Map(data.nodes.map((n) => [n.equipement_id, n]));

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
        (n) => n.position.x !== 0 || n.position.y !== 0,
      );

      const layoutedNodes = hasSavedPositions
        ? detailedNodesArray
        : autoLayoutWithCustomDimensions(detailedNodesArray, detailedEdgesArray, layoutDirection);

      setDetailedNodes(layoutedNodes);
      setDetailedEdges(detailedEdgesArray);
    },
    [setDetailedNodes, setDetailedEdges, layoutDirection],
  );

  // ---------------------------------------------------------------------------
  // Effets de chargement initial / cascade entreprise → site → carte
  // ---------------------------------------------------------------------------
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
    return () => {
      cancelled = true;
    };
  }, [selectedSiteId, activeTab, loadDetailedView]);

  // Chargement des ports source/cible quand un équipement est choisi
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
    return () => {
      cancelled = true;
    };
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
    return () => {
      cancelled = true;
    };
  }, [targetEquipementId]);

  // ---------------------------------------------------------------------------
  // Layout — auto, sauvegarde, drag stop détaillé
  // ---------------------------------------------------------------------------
  const handleAutoLayout = useCallback(
    (dir?: "TB" | "LR") => {
      const d = dir ?? layoutDirection;
      setNodes((curr) => autoLayout(curr, edges, d));
    },
    [edges, layoutDirection, setNodes],
  );

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

  const handleSaveDetailedLayout = useCallback(
    async (nodesToSave?: Node<DetailedNodeData | FlowNodeData>[]) => {
      if (!selectedSiteId) return;
      const currentNodes = nodesToSave ?? detailedNodes;
      const existingLayoutData = siteMap?.layout_data ?? {};
      try {
        await networkMapApi.saveSiteLayout(selectedSiteId, {
          ...existingLayoutData,
          detailed_nodes: currentNodes.map((n) => ({
            id: n.id,
            x: n.position.x,
            y: n.position.y,
          })),
        });
        toast.success("Layout détaillé sauvegardé");
      } catch (error) {
        console.error(error);
        toast.error("Échec de sauvegarde du layout détaillé");
      }
    },
    [selectedSiteId, detailedNodes, siteMap],
  );

  const onDetailedNodeDragStop = useCallback(
    (_: React.MouseEvent, __: Node, nodesAfterDrag: Node[]) => {
      if (detailedSaveTimeoutRef.current) {
        clearTimeout(detailedSaveTimeoutRef.current);
      }
      detailedSaveTimeoutRef.current = setTimeout(() => {
        handleSaveDetailedLayout(nodesAfterDrag as Node<DetailedNodeData | FlowNodeData>[]);
      }, 500);
    },
    [handleSaveDetailedLayout],
  );

  const handleAutoLayoutDetailed = useCallback(() => {
    const layoutedNodes = autoLayoutWithCustomDimensions(
      detailedNodes,
      detailedEdges,
      layoutDirection,
    );
    setDetailedNodes(layoutedNodes);
  }, [detailedNodes, detailedEdges, layoutDirection, setDetailedNodes]);

  // ---------------------------------------------------------------------------
  // Liens — création / édition / suppression
  // ---------------------------------------------------------------------------
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

  // ---------------------------------------------------------------------------
  // Handlers ReactFlow
  // ---------------------------------------------------------------------------
  const onConnect = useCallback(
    (params: Edge | Connection) => {
      if (!selectedSiteId || !params.source || !params.target) return;
      const sourceId = params.source.startsWith("eq-") ? Number(params.source.slice(3)) : null;
      const targetId = params.target.startsWith("eq-") ? Number(params.target.slice(3)) : null;
      if (!sourceId || !targetId) return;

      resetLinkForm();
      setSourceEquipementId(String(sourceId));
      setTargetEquipementId(String(targetId));
      setLinkDialogOpen(true);
    },
    [selectedSiteId, resetLinkForm],
  );

  const onNodeDoubleClick = useCallback(
    async (_event: React.MouseEvent, node: Node<FlowNodeData>) => {
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
    },
    [selectedSiteId, loadVlans],
  );

  const onEdgeDoubleClick = useCallback(
    async (_event: React.MouseEvent, edge: Edge) => {
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
    },
    [resetLinkForm],
  );

  // ---------------------------------------------------------------------------
  // Connexions inter-sites
  // ---------------------------------------------------------------------------
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
      toast.error(
        editingSiteConnId
          ? "Impossible de mettre à jour la connexion"
          : "Impossible de créer la connexion",
      );
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

  const onOverviewEdgeDoubleClick = useCallback(
    async (_event: React.MouseEvent, edge: Edge) => {
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
    },
    [resetSiteConnForm],
  );

  // ---------------------------------------------------------------------------
  // Toggle direction (utilisé par chaque toolbar de tab)
  // ---------------------------------------------------------------------------
  const toggleLayoutDirection = useCallback(() => {
    const next = layoutDirection === "TB" ? "LR" : "TB";
    setLayoutDirection(next);
    handleAutoLayout(next);
  }, [layoutDirection, handleAutoLayout]);

  // ---------------------------------------------------------------------------
  // API publique (groupée par domaine)
  // ---------------------------------------------------------------------------
  return {
    // navigation / contexte
    context: {
      entreprises,
      sites,
      selectedEntrepriseId,
      selectedSiteId,
      setSelectedEntrepriseId,
      setSelectedSiteId,
      activeTab,
      setActiveTab,
      loading,
    },
    // données chargées
    data: {
      siteMap,
      overview,
      siteEquipements,
      siteVlans,
    },
    // layout / actions communes
    layout: {
      layoutDirection,
      setLayoutDirection,
      toggleLayoutDirection,
      handleAutoLayout,
      handleSaveLayout,
      handleAutoLayoutDetailed,
      handleSaveDetailedLayout,
    },
    // rechargements
    reload: {
      loadSiteMap,
      loadOverview,
      loadDetailedView,
      loadVlans,
    },
    // ReactFlow — tab "site"
    site: {
      nodes,
      edges,
      onNodesChange,
      onEdgesChange,
      onConnect,
      onNodeDoubleClick,
      onEdgeDoubleClick,
    },
    // ReactFlow — tab "overview"
    overviewFlow: {
      nodes: overviewNodes,
      edges: overviewEdges,
      onNodesChange: onOverviewNodesChange,
      onEdgesChange: onOverviewEdgesChange,
      onEdgeDoubleClick: onOverviewEdgeDoubleClick,
    },
    // ReactFlow — tab "detailed"
    detailed: {
      nodes: detailedNodes,
      edges: detailedEdges,
      setNodes: setDetailedNodes,
      onNodesChange: onDetailedNodesChange,
      onEdgesChange: onDetailedEdgesChange,
      onNodeDragStop: onDetailedNodeDragStop,
      onNodeDoubleClick,
    },
    // formulaire lien intra-site
    linkForm: {
      open: linkDialogOpen,
      setOpen: setLinkDialogOpen,
      sourceEquipementId,
      setSourceEquipementId,
      targetEquipementId,
      setTargetEquipementId,
      sourceInterface,
      setSourceInterface,
      targetInterface,
      setTargetInterface,
      linkType,
      setLinkType,
      bandwidth,
      setBandwidth,
      vlan,
      setVlan,
      networkSegment,
      setNetworkSegment,
      linkDescription,
      setLinkDescription,
      editingLinkId,
      saving: linkSaving,
      sourceEquipPorts,
      targetEquipPorts,
      selectedSourcePortId,
      setSelectedSourcePortId,
      selectedTargetPortId,
      setSelectedTargetPortId,
      reset: resetLinkForm,
      save: handleSaveLink,
      remove: handleDeleteLink,
    },
    // formulaire connexion inter-site
    siteConnForm: {
      open: siteConnDialogOpen,
      setOpen: setSiteConnDialogOpen,
      sourceSiteId: connSourceSiteId,
      setSourceSiteId: setConnSourceSiteId,
      targetSiteId: connTargetSiteId,
      setTargetSiteId: setConnTargetSiteId,
      linkType: connLinkType,
      setLinkType: setConnLinkType,
      bandwidth: connBandwidth,
      setBandwidth: setConnBandwidth,
      description: connDescription,
      setDescription: setConnDescription,
      editingSiteConnId,
      saving: connSaving,
      reset: resetSiteConnForm,
      save: handleSaveSiteConn,
      remove: handleDeleteSiteConn,
    },
    // détail équipement / ports
    detail: {
      open: detailOpen,
      setOpen: setDetailOpen,
      equipement: detailEquipement,
      assessments: detailAssessments,
      loading: detailLoading,
      editingPorts,
      setEditingPorts,
      newPortName,
      setNewPortName,
      newPortType,
      setNewPortType,
      newPortSpeed,
      setNewPortSpeed,
      newPortRow,
      setNewPortRow,
      handleAddPort,
      handleRemovePort,
      handleApplyPreset,
      handleSavePorts,
      savingPorts,
      isPortPresetConfirmOpen,
      setIsPortPresetConfirmOpen,
      pendingPreset,
      setPendingPreset,
      confirmPreset,
    },
    // édition inline d'un port
    inlinePort: {
      port: inlineEditPort,
      setPort: setInlineEditPort,
      equipementId: inlineEditEquipId,
      position: inlineEditPosition,
      close: closeInlineEdit,
      save: handleSaveInlinePort,
    },
    // VLANs
    vlanEditor: {
      open: vlanDialogOpen,
      setOpen: setVlanDialogOpen,
      saving: savingVlan,
      newVlanId,
      setNewVlanId,
      newVlanName,
      setNewVlanName,
      newVlanSubnet,
      setNewVlanSubnet,
      newVlanColor,
      setNewVlanColor,
      newVlanDescription,
      setNewVlanDescription,
      create: handleCreateVlan,
      remove: handleDeleteVlan,
      panelExpanded: vlanPanelExpanded,
      setPanelExpanded: setVlanPanelExpanded,
    },
  };
}

export type UseNetworkMap = ReturnType<typeof useNetworkMap>;
