/**
 * Centralized UI constants for labels, colors, icons, and variants.
 * Import from here instead of duplicating across pages.
 */

import type {
  AuditStatus,
  CampaignStatus,
  ComplianceStatus,
  TypeEquipement,
  StatusAudit,
} from "@/types";
import {
  FileText,
  Play,
  CheckCircle,
  Archive,
  AlertCircle,
  CircleDot,
  Minus,
  ShieldAlert,
  AlertTriangle,
  Shield,
  Info,
  Monitor,
  Wifi,
  Server,
  Network,
  Router,
  Printer,
  Video,
  HardDrive,
  Cpu,
  Phone,
  Radio,
  Cloud,
} from "lucide-react";

// ─── Severity ────────────────────────────────────────────────

export const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;

export const SEVERITY_LABELS: Record<string, string> = {
  critical: "Critique",
  high: "Élevée",
  medium: "Moyenne",
  low: "Faible",
  info: "Info",
};

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-blue-100 text-blue-800 border-blue-200",
  info: "bg-gray-100 text-gray-600 border-gray-200",
};

export const SEVERITY_ICONS: Record<string, typeof ShieldAlert> = {
  critical: ShieldAlert,
  high: AlertTriangle,
  medium: Shield,
  low: Info,
  info: Info,
};

export const SEVERITY_VARIANTS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  critical: "destructive",
  high: "destructive",
  medium: "secondary",
  low: "outline",
  info: "outline",
};

// ─── Compliance ──────────────────────────────────────────────

export const COMPLIANCE_LABELS: Record<ComplianceStatus, string> = {
  not_assessed: "Non évalué",
  compliant: "Conforme",
  non_compliant: "Non conforme",
  partially_compliant: "Partiellement conforme",
  not_applicable: "Non applicable",
};

/** Short compliance labels for compact displays (badges, tables) */
export const COMPLIANCE_LABELS_SHORT: Record<ComplianceStatus, string> = {
  not_assessed: "Non évalué",
  compliant: "Conforme",
  non_compliant: "Non conforme",
  partially_compliant: "Partiellement",
  not_applicable: "N/A",
};

export const COMPLIANCE_COLORS: Record<ComplianceStatus, string> = {
  not_assessed: "bg-gray-100 text-gray-600 border-gray-200",
  compliant: "bg-green-100 text-green-800 border-green-300",
  non_compliant: "bg-red-100 text-red-800 border-red-300",
  partially_compliant: "bg-yellow-100 text-yellow-800 border-yellow-300",
  not_applicable: "bg-gray-50 text-gray-500 border-gray-200",
};

export const COMPLIANCE_ICONS: Record<ComplianceStatus, typeof CheckCircle> = {
  compliant: CheckCircle,
  non_compliant: AlertCircle,
  partially_compliant: CircleDot,
  not_applicable: Minus,
  not_assessed: CircleDot,
};

// ─── Audit Status ────────────────────────────────────────────

export const AUDIT_STATUS_LABELS: Record<AuditStatus, string> = {
  NOUVEAU: "Nouveau",
  EN_COURS: "En cours",
  TERMINE: "Terminé",
  ARCHIVE: "Archivé",
};

export const AUDIT_STATUS_VARIANTS: Record<AuditStatus, "default" | "secondary" | "destructive" | "outline"> = {
  NOUVEAU: "outline",
  EN_COURS: "secondary",
  TERMINE: "default",
  ARCHIVE: "destructive",
};

export const AUDIT_STATUS_ICONS: Record<AuditStatus, typeof FileText> = {
  NOUVEAU: FileText,
  EN_COURS: Play,
  TERMINE: CheckCircle,
  ARCHIVE: Archive,
};

// ─── Campaign Status ─────────────────────────────────────────

export const CAMPAIGN_STATUS_LABELS: Record<CampaignStatus, string> = {
  draft: "Brouillon",
  in_progress: "En cours",
  review: "En revue",
  completed: "Terminée",
  archived: "Archivée",
};

// ─── Combined status colors (audit + campaign) for dashboard ─

export const STATUS_COLORS: Record<string, string> = {
  NOUVEAU: "bg-blue-500/10 text-blue-700",
  EN_COURS: "bg-yellow-500/10 text-yellow-700",
  TERMINE: "bg-green-500/10 text-green-700",
  ARCHIVE: "bg-gray-500/10 text-gray-700",
  draft: "bg-gray-500/10 text-gray-700",
  in_progress: "bg-yellow-500/10 text-yellow-700",
  review: "bg-orange-500/10 text-orange-700",
  completed: "bg-green-500/10 text-green-700",
  archived: "bg-gray-500/10 text-gray-500",
};

export const STATUS_LABELS: Record<string, string> = {
  ...AUDIT_STATUS_LABELS,
  ...CAMPAIGN_STATUS_LABELS,
};

// ─── Check Type ──────────────────────────────────────────────

export const CHECK_TYPE_LABELS: Record<string, string> = {
  manual: "Manuel",
  automatic: "Automatique",
  "semi-automatic": "Semi-auto",
};

// ─── Engine labels (frameworks) ──────────────────────────────

export const ENGINE_LABELS: Record<string, string> = {
  manual: "Manuel",
  monkey365: "Monkey365",
  nmap: "Nmap",
  automatic: "Automatique",
};

// ─── Framework icons ─────────────────────────────────────────

export const FRAMEWORK_ICONS: Record<string, string> = {
  firewall: "🔥",
  switch: "🔀",
  server_windows: "🖥️",
  server_linux: "🐧",
  active_directory: "📁",
  wifi: "📶",
  sauvegarde: "💾",
  peripheriques: "🖨️",
  m365: "☁️",
  messagerie: "📧",
  vpn: "🔒",
  dns_dhcp: "🌐",
};

export function getFrameworkIcon(refId: string): string {
  for (const [key, icon] of Object.entries(FRAMEWORK_ICONS)) {
    if (refId.includes(key)) return icon;
  }
  return "📋";
}

// ─── Equipement ──────────────────────────────────────────────

export const EQUIPEMENT_TYPE_LABELS: Record<TypeEquipement, string> = {
  serveur: "Serveur",
  firewall: "Firewall",
  reseau: "Réseau",
  equipement: "Autre",
  switch: "Switch",
  router: "Routeur",
  access_point: "Point d'accès",
  printer: "Imprimante",
  camera: "Caméra",
  nas: "NAS",
  hyperviseur: "Hyperviseur",
  telephone: "Téléphone",
  iot: "IoT",
  cloud_gateway: "Passerelle cloud",
};

export const EQUIPEMENT_TYPE_ICONS: Record<TypeEquipement, typeof Server> = {
  serveur: Monitor,
  firewall: Shield,
  reseau: Wifi,
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

export const EQUIPEMENT_STATUS_LABELS: Record<StatusAudit, string> = {
  A_AUDITER: "À auditer",
  EN_COURS: "En cours",
  CONFORME: "Conforme",
  NON_CONFORME: "Non conforme",
};

export const EQUIPEMENT_STATUS_VARIANTS: Record<StatusAudit, "default" | "secondary" | "destructive" | "outline"> = {
  A_AUDITER: "outline",
  EN_COURS: "secondary",
  CONFORME: "default",
  NON_CONFORME: "destructive",
};
