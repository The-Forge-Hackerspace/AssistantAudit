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

export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: "admin" | "auditeur" | "lecteur";
  is_active?: boolean;
  password?: string;
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
export type TypeEquipement =
  | "reseau"
  | "serveur"
  | "firewall"
  | "equipement"
  | "switch"
  | "router"
  | "access_point"
  | "printer"
  | "camera"
  | "nas"
  | "hyperviseur"
  | "telephone"
  | "iot"
  | "cloud_gateway";
export type StatusAudit = "A_AUDITER" | "EN_COURS" | "CONFORME" | "NON_CONFORME";

export interface PortDefinition {
  id: string;          // unique within equipment, e.g. "ge-0/0/1"
  name: string;        // display name, e.g. "GigE 1"
  type: "ethernet" | "sfp" | "sfp+" | "console" | "mgmt";
  speed: string;       // e.g. "1 Gbps", "10 Gbps"
  row: number;         // visual row (0 = top, 1 = bottom)
  index: number;       // position within row (left to right)
  untaggedVlan?: number | null;  // access/native VLAN ID
  taggedVlans?: number[];        // trunk tagged VLAN IDs
}

export interface VlanDefinition {
  id: number;
  site_id: number;
  vlan_id: number;
  name: string;
  subnet: string | null;
  color: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface VlanDefinitionCreate {
  site_id: number;
  vlan_id: number;
  name: string;
  subnet?: string | null;
  color?: string;
  description?: string | null;
}

export interface VlanDefinitionUpdate {
  vlan_id?: number;
  name?: string;
  subnet?: string | null;
  color?: string;
  description?: string | null;
}

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
  vlan_config: Record<string, unknown> | null;
  ports_status: PortDefinition[] | null;
  firmware_version: string | null;
  // Spécifiques serveur
  os_version_detail: string | null;
  modele_materiel: string | null;
  role_list: Record<string, unknown> | null;
  cpu_ram_info: Record<string, unknown> | null;
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
  source: string | null;
  author: string | null;
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
  source?: string;
  author?: string;
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

// ── Scanner Réseau : supprimé — scan nmap délégué à l'agent distant (voir AgentTask).

export interface NetworkLink {
  id: number;
  site_id: number;
  source_equipement_id: number;
  target_equipement_id: number;
  source_interface: string | null;
  target_interface: string | null;
  link_type: "ethernet" | "fiber" | "wifi" | "vpn" | "wan" | "serial" | "other";
  bandwidth: string | null;
  vlan: string | null;
  network_segment: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface NetworkLinkCreate {
  site_id: number;
  source_equipement_id: number;
  target_equipement_id: number;
  source_interface?: string;
  target_interface?: string;
  link_type?: "ethernet" | "fiber" | "wifi" | "vpn" | "wan" | "serial" | "other";
  bandwidth?: string;
  vlan?: string;
  network_segment?: string;
  description?: string;
}

export interface NetworkMapNode {
  id: string;
  equipement_id: number;
  site_id: number;
  type_equipement: TypeEquipement;
  ip_address: string;
  hostname: string | null;
  label: string;
  metadata: Record<string, unknown>;
  position?: { id: string; x: number; y: number };
}

export interface NetworkMapEdge {
  id: string;
  link_id: number;
  source: string;
  target: string;
  metadata: Record<string, unknown>;
}

export interface NetworkMap {
  site_id: number;
  nodes: NetworkMapNode[];
  edges: NetworkMapEdge[];
  layout_data: {
    nodes?: Array<{ id: string; x: number; y: number }>;
    detailed_nodes?: Array<{ id: string; x: number; y: number }>;
    viewport?: { x: number; y: number; zoom: number };
  };
}

export interface SiteConnection {
  id: number;
  entreprise_id: number;
  source_site_id: number;
  target_site_id: number;
  link_type: "wan" | "vpn" | "mpls" | "sdwan" | "other";
  bandwidth: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface SiteConnectionCreate {
  entreprise_id: number;
  source_site_id: number;
  target_site_id: number;
  link_type?: "wan" | "vpn" | "mpls" | "sdwan" | "other";
  bandwidth?: string;
  description?: string;
}

export interface MultiSiteNode {
  id: string;
  site_id: number;
  site_name: string;
  equipement_count: number;
}

export interface MultiSiteEdge {
  id: string;
  connection_id: number;
  source: string;
  target: string;
  metadata: Record<string, unknown>;
}

export interface MultiSiteOverview {
  entreprise_id: number;
  nodes: MultiSiteNode[];
  edges: MultiSiteEdge[];
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
  config_analysis_id: number | null;
  analysis: ConfigAnalysisResult;
}

// ── Config Analysis (persistée) ──
export interface ConfigAnalysisRead {
  id: number;
  equipement_id: number;
  filename: string;
  vendor: string;
  device_type: string;
  hostname: string | null;
  firmware_version: string | null;
  serial_number: string | null;
  interfaces: InterfaceInfo[];
  firewall_rules: FirewallRuleInfo[];
  findings: SecurityFinding[];
  summary: Record<string, unknown>;
  created_at: string;
}

export interface ConfigAnalysisSummary {
  id: number;
  equipement_id: number;
  filename: string;
  vendor: string;
  hostname: string | null;
  firmware_version: string | null;
  findings_count: number;
  created_at: string;
}

export interface PrefillDetail {
  control_ref: string;
  control_title: string;
  status: string;
  findings_count: number;
}

export interface PrefillResult {
  controls_prefilled: number;
  controls_compliant: number;
  controls_non_compliant: number;
  controls_partial: number;
  details: PrefillDetail[];
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

// ── Collecte SSH / WinRM ──
export interface CollectCreate {
  equipement_id: number;
  agent_uuid: string;
  method: "ssh" | "winrm";
  device_profile?: string;
  target_host: string;
  target_port: number;
  username: string;
  password?: string;
  private_key?: string;
  passphrase?: string;
  use_ssl?: boolean;
  transport?: string;
}

export type CollectStatus = "running" | "success" | "failed";

export interface CollectResultSummary {
  id: number;
  equipement_id: number;
  method: string;
  device_profile: string | null;
  status: CollectStatus;
  target_host: string;
  target_port: number;
  username: string;
  hostname_collected: string | null;
  summary: CollectSummary | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface CollectSummary {
  os_type: string;
  os_name: string;
  os_version: string;
  hostname: string;
  device_profile?: string;
  total_checks: number;
  compliant: number;
  non_compliant: number;
  compliance_score: number | null;
  firewall_rules_count?: number;
}

export interface CollectResultRead extends CollectResultSummary {
  os_info: Record<string, unknown> | null;
  network: Record<string, unknown> | null;
  users: Record<string, unknown> | null;
  services: Record<string, unknown> | null;
  security: Record<string, unknown> | null;
  storage: Record<string, unknown> | null;
  updates: Record<string, unknown> | null;
  findings: CollectFinding[] | null;
}

export interface CollectFinding {
  control_ref: string;
  title: string;
  description: string;
  severity: string;
  category: string;
  remediation: string;
  status: string;
}

// ── Audit Active Directory ──
export interface ADAuditCreate {
  target_host: string;
  target_port?: number;
  use_ssl?: boolean;
  username: string;
  password: string;
  domain: string;
  auth_method?: "ntlm" | "simple";
  equipement_id?: number;
}

export type ADAuditStatus = "running" | "success" | "failed";

export interface ADAuditSummary {
  total_controls: number;
  compliant: number;
  non_compliant: number;
  partial: number;
  info: number;
  compliance_score: number;
}

export interface ADAuditFinding {
  control_ref: string;
  title: string;
  description: string;
  severity: string;
  category: string;
  status: string;
  evidence: string;
  remediation: string;
  details: Record<string, unknown> | null;
}

export interface ADAuditResultSummary {
  id: number;
  equipement_id: number | null;
  status: ADAuditStatus;
  target_host: string;
  target_port: number;
  domain: string | null;
  domain_name: string | null;
  summary: ADAuditSummary | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface ADAuditResultRead extends ADAuditResultSummary {
  username: string | null;
  domain_functional_level: string | null;
  forest_functional_level: string | null;
  total_users: number | null;
  enabled_users: number | null;
  disabled_users: number | null;
  dc_list: Record<string, unknown>[] | null;
  domain_admins: Record<string, unknown>[] | null;
  enterprise_admins: Record<string, unknown>[] | null;
  schema_admins: Record<string, unknown>[] | null;
  inactive_users: Record<string, unknown>[] | null;
  never_expire_password: Record<string, unknown>[] | null;
  never_logged_in: Record<string, unknown>[] | null;
  admin_account_status: Record<string, unknown> | null;
  password_policy: Record<string, unknown> | null;
  fine_grained_policies: Record<string, unknown>[] | null;
  gpo_list: Record<string, unknown>[] | null;
  laps_deployed: boolean | null;
  findings: ADAuditFinding[] | null;
}

// ── Monkey365 ──
export interface Monkey365Config {
  spo_sites?: string[];
  export_to?: string[];
  device_code?: boolean;
}

export interface Monkey365ScanCreate {
  entreprise_id: number;
  config: Monkey365Config;
}

export interface Monkey365ScanResultSummary {
  id: number;
  entreprise_id: number;
  scan_id: string;
  status: string;
  entreprise_slug?: string | null;
  findings_count?: number | null;
  created_at: string;
  completed_at?: string | null;
  duration_seconds?: number | null;
}

export interface Monkey365ScanResultDetail extends Monkey365ScanResultSummary {
  config_snapshot?: Record<string, unknown> | null;
  output_path?: string | null;
  error_message?: string | null;
}

export interface Monkey365ScanLogs {
  lines: string[];
  total_lines: number;
}

export interface Monkey365ImportRequest {
  audit_id: number;
}

export interface Monkey365ImportResult {
  campaign_id: number;
  assessment_id: number;
  controls_mapped: number;
  controls_total: number;
}

// ── Agents ──
export type AgentStatus = "pending" | "active" | "revoked" | "offline";

export interface Agent {
  id: number;
  agent_uuid: string;
  name: string;
  status: AgentStatus;
  last_seen: string | null;
  last_ip: string | null;
  allowed_tools: string[];
  os_info: string | null;
  agent_version: string | null;
  owner_name: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface AgentCreateRequest {
  name: string;
  allowed_tools?: string[];
  target_user_id?: number | null;
}

export interface AgentCreateResponse {
  agent_uuid: string;
  enrollment_code: string;
  expires_at: string;
}

export type AgentTaskStatus = "pending" | "dispatched" | "running" | "completed" | "failed" | "cancelled";

export interface AgentTask {
  id: number;
  task_uuid: string;
  agent_id: number;
  owner_id: number;
  audit_id: number | null;
  tool: string;
  parameters: Record<string, unknown>;
  status: AgentTaskStatus;
  progress: number;
  status_message: string | null;
  result_summary: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  dispatched_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  // Enrichis par le serveur (resolus depuis parameters.site_id)
  site_name?: string;
  entreprise_name?: string;
}

export interface TaskArtifact {
  id: number;
  file_uuid: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  uploaded_at: string;
  download_url: string;
}

// ── Checklists ──
export interface ChecklistTemplate {
  id: number;
  name: string;
  description: string | null;
  category: string;
  is_predefined: boolean;
}

export interface ChecklistTemplateDetail extends ChecklistTemplate {
  sections: ChecklistSection[];
}

export interface ChecklistSection {
  id: number;
  name: string;
  description: string | null;
  order: number;
  items: ChecklistItem[];
}

export interface ChecklistItem {
  id: number;
  label: string;
  description: string | null;
  order: number;
  ref_code: string | null;
}

export interface ChecklistInstance {
  id: number;
  template_id: number;
  audit_id: number;
  site_id: number | null;
  filled_by: number | null;
  status: "draft" | "in_progress" | "completed";
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ChecklistInstanceDetail extends ChecklistInstance {
  responses: ChecklistResponse[];
  template_name: string;
}

export interface ChecklistResponse {
  id: number;
  instance_id: number;
  item_id: number;
  status: "OK" | "NOK" | "NA" | "UNCHECKED";
  note: string | null;
  responded_by: number | null;
  responded_at: string | null;
}

export interface ChecklistProgress {
  total_items: number;
  answered: number;
  ok: number;
  nok: number;
  na: number;
  unchecked: number;
  progress_percent: number;
}

// ── ORADAD ──
export interface DomainEntry {
  server: string;
  port: number;
  domain_name: string;
  username: string;
  user_domain: string;
  password: string;
}

export interface DomainEntryResponse {
  server: string;
  port: number;
  domain_name: string;
  username: string;
  user_domain: string;
}

export interface OradadConfig {
  id: number;
  name: string;
  auto_get_domain: boolean;
  auto_get_trusts: boolean;
  level: number;
  confidential: number;
  process_sysvol: boolean;
  sysvol_filter: string | null;
  output_files: boolean;
  output_mla: boolean;
  sleep_time: number;
  explicit_domains: DomainEntryResponse[] | null;
  created_at: string;
  updated_at: string | null;
}

export interface OradadConfigCreate {
  name: string;
  auto_get_domain?: boolean;
  auto_get_trusts?: boolean;
  level?: number;
  confidential?: number;
  process_sysvol?: boolean;
  sysvol_filter?: string | null;
  output_files?: boolean;
  output_mla?: boolean;
  sleep_time?: number;
  explicit_domains?: DomainEntry[] | null;
}

export interface OradadTask {
  id: number;
  task_uuid: string;
  agent_name: string | null;
  status: AgentTaskStatus;
  progress: number;
  created_at: string | null;
  completed_at: string | null;
  has_report: boolean;
}

export interface AnssiCheckResult {
  vuln_id: string;
  title: string;
  category: string;
  level: number;
  status: "pass" | "fail" | "warning" | "not_checked";
  description: string;
  recommendation: string;
  evidence: string | null;
  details: Record<string, unknown> | null;
}

export interface AnssiReport {
  findings: AnssiCheckResult[];
  score: number;
  level: number;
  stats: {
    total_checks: number;
    passed: number;
    failed: number;
    warning: number;
    not_checked: number;
  };
}

// ── Tags ──
export interface Tag {
  id: number;
  name: string;
  color: string;
  scope: "global" | "audit";
  audit_id: number | null;
  created_by: number | null;
  created_at: string;
}

export interface TagAssociation {
  id: number;
  tag_id: number;
  taggable_type: string;
  taggable_id: number;
  tag: Tag;
}
