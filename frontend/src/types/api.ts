// ── Types API AssistantAudit ──────────────────────────────────────

// ── Pagination ──
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ── Auth ──
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: "admin" | "auditeur" | "lecteur";
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name: string;
  role: "admin" | "auditeur" | "lecteur";
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

// ── Entreprise ──
export interface Contact {
  id?: number;
  nom: string;
  role: string;
  email: string;
  telephone: string;
  is_main_contact: boolean;
}

export interface Entreprise {
  id: number;
  nom: string;
  adresse: string | null;
  secteur_activite: string | null;
  siret: string | null;
  presentation_desc: string | null;
  contraintes_reglementaires: string | null;
  contacts: Contact[];
  created_at: string;
  updated_at: string;
}

export interface EntrepriseCreate {
  nom: string;
  adresse?: string;
  secteur_activite?: string;
  siret?: string;
  presentation_desc?: string;
  contraintes_reglementaires?: string;
  contacts?: Contact[];
}

// ── Audit ──
export type AuditStatus = "NOUVEAU" | "EN_COURS" | "TERMINE" | "ARCHIVE";

export interface Audit {
  id: number;
  nom_projet: string;
  entreprise_id: number;
  objectifs: string | null;
  limites: string | null;
  hypotheses: string | null;
  risques_initiaux: string | null;
  status: AuditStatus;
  date_debut: string;
  lettre_mission_path: string | null;
  contrat_path: string | null;
  planning_path: string | null;
  total_campaigns: number;
  entreprise_nom?: string | null;
}

export interface AuditCreate {
  nom_projet: string;
  entreprise_id: number;
  objectifs?: string;
  limites?: string;
  hypotheses?: string;
  risques_initiaux?: string;
}

// ── Site ──
export interface Site {
  id: number;
  nom: string;
  description: string | null;
  adresse: string | null;
  entreprise_id: number;
  equipement_count: number;
}

export interface SiteCreate {
  nom: string;
  description?: string;
  adresse?: string;
  entreprise_id: number;
}

// ── Equipement ──
export type TypeEquipement = "reseau" | "serveur" | "firewall" | "equipement";
export type StatusAudit = "A_AUDITER" | "EN_COURS" | "CONFORME" | "NON_CONFORME";

export interface Equipement {
  id: number;
  site_id: number;
  type_equipement: TypeEquipement;
  ip_address: string;
  hostname: string | null;
  fabricant: string | null;
  os_detected: string | null;
  status_audit: StatusAudit;
  notes_audit: string | null;
  // Spécifiques réseau
  vlan_config: string | null;
  ports_status: string | null;
  firmware_version: string | null;
  // Spécifiques serveur
  os_version_detail: string | null;
  modele_materiel: string | null;
  role_list: Record<string, unknown> | null;
  cpu_ram_info: string | null;
  // Spécifiques firewall
  license_status: string | null;
  vpn_users_count: number | null;
  rules_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface EquipementCreate {
  site_id: number;
  type_equipement: TypeEquipement;
  ip_address: string;
  hostname?: string;
  fabricant?: string;
  os_detected?: string;
  [key: string]: unknown;
}

// ── Framework ──
export interface Control {
  id: number;
  ref_id: string;
  title: string;
  description: string | null;
  severity: "critical" | "high" | "medium" | "low" | "info";
  check_type: string | null;
  remediation: string | null;
  engine_rule_id: string | null;
  cis_reference: string | null;
  evidence_required: boolean;
}

export interface FrameworkCategory {
  id: number;
  name: string;
  description: string | null;
  controls: Control[];
}

export interface FrameworkSummary {
  id: number;
  ref_id: string;
  name: string;
  version: string;
  engine: string | null;
  engine_config: Record<string, unknown> | null;
  is_active: boolean;
  total_controls: number;
  parent_version_id: number | null;
}

export interface Framework extends FrameworkSummary {
  description: string | null;
  categories: FrameworkCategory[];
}

export interface ControlCreate {
  ref_id: string;
  title: string;
  description?: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  check_type: string;
  remediation?: string;
  engine_rule_id?: string;
  cis_reference?: string;
  evidence_required?: boolean;
}

export interface CategoryCreate {
  name: string;
  description?: string;
  controls: ControlCreate[];
}

export interface FrameworkCreatePayload {
  ref_id: string;
  name: string;
  description?: string;
  version: string;
  engine?: string;
  engine_config?: Record<string, unknown>;
  categories: CategoryCreate[];
}

// ── Campaign ──
export type CampaignStatus = "draft" | "in_progress" | "review" | "completed" | "archived";

export interface CampaignSummary {
  id: number;
  name: string;
  status: CampaignStatus;
  audit_id: number;
  created_at: string;
  compliance_score: number | null;
  total_assessments: number;
}

export interface Campaign {
  id: number;
  name: string;
  description: string | null;
  audit_id: number;
  status: CampaignStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  compliance_score: number | null;
  assessments: Assessment[];
}

export interface CampaignCreate {
  name: string;
  description?: string;
  audit_id: number;
}

// ── Assessment ──
export type ComplianceStatus = "not_assessed" | "compliant" | "non_compliant" | "partially_compliant" | "not_applicable";

export interface ControlResult {
  id: number;
  assessment_id: number;
  control_id: number;
  status: ComplianceStatus;
  score: number | null;
  evidence: string | null;
  evidence_file_path: string | null;
  comment: string | null;
  remediation_note: string | null;
  auto_result: string | null;
  is_auto_assessed: boolean;
  assessed_at: string | null;
  assessed_by: string | null;
  control_ref_id: string | null;
  control_title: string | null;
  control_severity: string | null;
  control_category_name: string | null;
  control_category_id: number | null;
  control_description: string | null;
  control_remediation: string | null;
  control_check_type: string | null;
}

export interface Assessment {
  id: number;
  campaign_id: number;
  equipement_id: number;
  framework_id: number;
  score: number | null;
  notes: string | null;
  created_at: string;
  assessed_by: string | null;
  results: ControlResult[];
  equipement_ip: string | null;
  equipement_hostname: string | null;
  framework_name: string | null;
  compliance_score: number | null;
}

export interface AssessmentCreate {
  equipement_id: number;
  framework_id: number;
  notes?: string;
}

export interface Score {
  assessment_id?: number;
  campaign_id?: number;
  total_controls: number;
  assessed_controls: number;
  compliant: number;
  non_compliant: number;
  partially_compliant: number;
  not_applicable: number;
  not_assessed: number;
  compliance_score: number;
  by_severity?: Record<string, Record<string, number>>;
}

// ── Messages ──
export interface MessageResponse {
  message: string;
  detail?: string | null;
}

// ── Attachments ──
export interface Attachment {
  id: number;
  control_result_id: number;
  original_filename: string;
  stored_filename: string;
  file_path: string;
  mime_type: string;
  file_size: number;
  description: string | null;
  uploaded_at: string;
  uploaded_by: string | null;
  download_url: string | null;
  preview_url: string | null;
}

// ── Scanner Réseau ──
export interface ScanCreate {
  nom?: string;
  site_id: number;
  target: string;
  scan_type?: "discovery" | "port_scan" | "full" | "custom";
  custom_args?: string;
  notes?: string;
  timeout?: number;
}

export interface ScanPort {
  id: number;
  port_number: number;
  protocol: string | null;
  state: string | null;
  service_name: string | null;
  product: string | null;
  version: string | null;
}

export type HostDecision = "pending" | "kept" | "ignored";

export interface ScanHost {
  id: number;
  ip_address: string;
  hostname: string | null;
  mac_address: string | null;
  vendor: string | null;
  os_guess: string | null;
  status: string | null;
  ports_open_count: number;
  decision: HostDecision;
  chosen_type: TypeEquipement | null;
  equipement_id: number | null;
  date_decouverte: string;
  ports: ScanPort[];
}

export interface Scan {
  id: number;
  site_id: number;
  nom: string | null;
  date_scan: string;
  type_scan: string | null;
  nmap_command: string | null;
  nombre_hosts_trouves: number;
  nombre_ports_ouverts: number;
  duree_scan_secondes: number | null;
  notes: string | null;
  hosts: ScanHost[];
}

export interface ScanSummary {
  id: number;
  site_id: number;
  nom: string | null;
  date_scan: string;
  type_scan: string | null;
  nmap_command: string | null;
  nombre_hosts_trouves: number;
  nombre_ports_ouverts: number;
  duree_scan_secondes: number | null;
  notes: string | null;
}

export interface ScanHostDecision {
  decision: HostDecision;
  chosen_type?: TypeEquipement;
  hostname_override?: string;
  create_equipement?: boolean;
}

// ── Config Parser ──
export interface InterfaceInfo {
  name: string;
  ip_address: string | null;
  netmask: string | null;
  vlan: number | null;
  status: string;
  allowed_access: string[];
  description: string | null;
}

export interface FirewallRuleInfo {
  rule_id: string;
  name: string | null;
  source_interface: string | null;
  dest_interface: string | null;
  source_address: string | null;
  dest_address: string | null;
  service: string | null;
  action: string;
  schedule: string | null;
  enabled: boolean;
  log_traffic: boolean;
}

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface SecurityFinding {
  severity: Severity;
  category: string;
  title: string;
  description: string;
  remediation: string | null;
  reference: string | null;
}

export interface ConfigAnalysisResult {
  vendor: string;
  device_type: string;
  hostname: string | null;
  firmware_version: string | null;
  serial_number: string | null;
  interfaces: InterfaceInfo[];
  firewall_rules: FirewallRuleInfo[];
  findings: SecurityFinding[];
  summary: Record<string, unknown>;
}

export interface ConfigUploadResponse {
  filename: string;
  vendor: string;
  equipement_id: number | null;
  analysis: ConfigAnalysisResult;
}

export interface VendorInfo {
  id: string;
  name: string;
  format: string;
  description: string;
}

// ── SSL/TLS Checker ──
export interface SSLCheckRequest {
  host: string;
  port?: number;
  timeout?: number;
}

export interface CertificateInfo {
  subject: string;
  issuer: string;
  organization: string;
  not_before: string | null;
  not_after: string | null;
  days_remaining: number;
  is_expired: boolean;
  self_signed: boolean;
  is_trusted: boolean;
  san: string[];
  serial_number: string;
  version: number;
  signature_algorithm: string;
  error: string | null;
}

export interface ProtocolInfo {
  name: string;
  supported: boolean;
  is_secure: boolean;
}

export interface SSLCheckResult {
  host: string;
  port: number;
  certificate: CertificateInfo | null;
  protocols: ProtocolInfo[];
  findings: SecurityFinding[];
}
