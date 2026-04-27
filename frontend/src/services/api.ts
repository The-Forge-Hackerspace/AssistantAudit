import axios from "axios";
import api from "@/lib/api-client";
import type {
  TokenResponse,
  User,
  UserUpdate,
  PaginatedResponse,
  Tag,
  TagAssociation,
  Entreprise,
  EntrepriseCreate,
  Audit,
  AuditCreate,
  AuditReport,
  AuditReportCreate,
  ExecutiveSummary,
  Site,
  SiteCreate,
  Equipement,
  EquipementCreate,
  FrameworkSummary,
  Framework,
  FrameworkCreatePayload,
  CampaignSummary,
  Campaign,
  CampaignCreate,
  Assessment,
  AssessmentCreate,
  Score,
  ControlResult,
  MessageResponse,
  RegisterRequest,
  Attachment,
  ConfigUploadResponse,
  ConfigAnalysisRead,
  ConfigAnalysisSummary,
  PrefillResult,
  SSLCheckRequest,
  SSLCheckResult,
  VendorInfo,
  CollectCreate,
  CollectResultSummary,
  CollectResultRead,
  ADAuditCreate,
  ADAuditResultSummary,
  ADAuditResultRead,
   Monkey365Config,
   Monkey365ScanCreate,
   Monkey365ScanResultSummary,
   Monkey365ScanResultDetail,
   Monkey365ScanLogs,
   NetworkLink,
  NetworkLinkCreate,
  NetworkMap,
  SiteConnection,
  SiteConnectionCreate,
  MultiSiteOverview,
  VlanDefinition,
  VlanDefinitionCreate,
  VlanDefinitionUpdate,
  Agent,
  AgentTask,
  TaskArtifact,
  AgentCreateRequest,
  AgentCreateResponse,
  AgentUpdateRequest,
  AgentRevokeResponse,
  OradadTask,
  OradadConfig,
  OradadConfigCreate,
  AnssiReport,
  ChecklistTemplate,
  ChecklistTemplateDetail,
  ChecklistInstance,
  ChecklistInstanceDetail,
  ChecklistResponse,
  ChecklistProgress,
} from "@/types";

// ── Auth ──
export const authApi = {
  async login(username: string, password: string): Promise<TokenResponse> {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    const { data } = await api.post<TokenResponse>("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    // Tokens poses en cookies httpOnly par le backend ; le body sert pour les clients programmatiques.
    return data;
  },

  async me(): Promise<User> {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },

  async register(payload: RegisterRequest): Promise<User> {
    const { data } = await api.post<User>("/auth/register", payload);
    return data;
  },

  async changePassword(current_password: string, new_password: string) {
    const { data } = await api.post("/auth/change-password", {
      current_password,
      new_password,
    });
    return data;
  },

  async refresh(): Promise<TokenResponse> {
    // Refresh token transmis automatiquement via cookie httpOnly aa_refresh_token.
    // withCredentials necessaire pour que le navigateur envoie le cookie cross-origin.
    const { data } = await axios.post<TokenResponse>(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/auth/refresh`,
      {},
      { withCredentials: true }
    );
    return data;
  },

  async logout() {
    // Endpoint backend qui supprime les cookies httpOnly cote navigateur.
    try {
      await api.post("/auth/logout");
    } catch {
      // logout best-effort : meme en cas d'erreur, l'UI poursuit la deconnexion.
    }
  },
};

// ── Users (admin) ──
export const usersApi = {
  async list(page = 1, pageSize = 20): Promise<PaginatedResponse<User>> {
    const { data } = await api.get("/users/", {
      params: { page, page_size: pageSize },
    });
    return data;
  },

  async create(payload: RegisterRequest): Promise<User> {
    const { data } = await api.post("/users/", payload);
    return data;
  },

  async update(id: number, payload: UserUpdate): Promise<User> {
    const { data } = await api.put(`/users/${id}`, payload);
    return data;
  },

  async delete(id: number): Promise<{ message: string }> {
    const { data } = await api.delete(`/users/${id}`);
    return data;
  },
};

// ── Entreprises ──
export const entreprisesApi = {
  async list(page = 1, pageSize = 20): Promise<PaginatedResponse<Entreprise>> {
    const { data } = await api.get("/entreprises", {
      params: { page, page_size: pageSize },
    });
    return data;
  },

  async get(id: number): Promise<Entreprise> {
    const { data } = await api.get(`/entreprises/${id}`);
    return data;
  },

  async create(payload: EntrepriseCreate): Promise<Entreprise> {
    const { data } = await api.post("/entreprises", payload);
    return data;
  },

  async update(id: number, payload: Partial<EntrepriseCreate>): Promise<Entreprise> {
    const { data } = await api.put(`/entreprises/${id}`, payload);
    return data;
  },

  async delete(id: number): Promise<MessageResponse> {
    const { data } = await api.delete(`/entreprises/${id}`);
    return data;
  },
};

// ── Audits ──
export const auditsApi = {
  async list(page = 1, pageSize = 20, entrepriseId?: number): Promise<PaginatedResponse<Audit>> {
    const { data } = await api.get("/audits", {
      params: { page, page_size: pageSize, entreprise_id: entrepriseId },
    });
    return data;
  },

  async get(id: number): Promise<Audit> {
    const { data } = await api.get(`/audits/${id}`);
    return data;
  },

  async create(payload: AuditCreate): Promise<Audit> {
    const { data } = await api.post("/audits", payload);
    return data;
  },

  async update(id: number, payload: Partial<AuditCreate & { status: string }>): Promise<Audit> {
    const { data } = await api.put(`/audits/${id}`, payload);
    return data;
  },

  async delete(id: number): Promise<MessageResponse> {
    const { data } = await api.delete(`/audits/${id}`);
    return data;
  },

  async getExecutiveSummary(id: number): Promise<ExecutiveSummary> {
    const { data } = await api.get<ExecutiveSummary>(`/audits/${id}/executive-summary`);
    return data;
  },

};

// ── Rapports ──
export const reportsApi = {
  async list(auditId: number): Promise<AuditReport[]> {
    const { data } = await api.get<AuditReport[]>("/reports", {
      params: { audit_id: auditId },
    });
    return data;
  },

  async create(payload: AuditReportCreate): Promise<AuditReport> {
    const { data } = await api.post<AuditReport>("/reports", payload);
    return data;
  },

  async generate(reportId: number): Promise<AuditReport> {
    const { data } = await api.post<AuditReport>(`/reports/${reportId}/generate`, {
      format: "pdf",
    });
    return data;
  },

  async download(reportId: number): Promise<Blob> {
    const { data } = await api.get(`/reports/${reportId}/download`, {
      responseType: "blob",
    });
    return data as Blob;
  },

  async delete(reportId: number): Promise<void> {
    await api.delete(`/reports/${reportId}`);
  },
};


// ── Sites ──
export const sitesApi = {
  async list(page = 1, pageSize = 20, entrepriseId?: number): Promise<PaginatedResponse<Site>> {
    const { data } = await api.get("/sites", {
      params: { page, page_size: pageSize, entreprise_id: entrepriseId },
    });
    return data;
  },

  async get(id: number): Promise<Site> {
    const { data } = await api.get(`/sites/${id}`);
    return data;
  },

  async create(payload: SiteCreate): Promise<Site> {
    const { data } = await api.post("/sites", payload);
    return data;
  },

  async update(id: number, payload: Partial<SiteCreate>): Promise<Site> {
    const { data } = await api.put(`/sites/${id}`, payload);
    return data;
  },

  async delete(id: number): Promise<MessageResponse> {
    const { data } = await api.delete(`/sites/${id}`);
    return data;
  },
};

// ── Équipements ──
export const equipementsApi = {
  async list(
    page = 1,
    pageSize = 20,
    filters?: { site_id?: number; entreprise_id?: number; type_equipement?: string; status_audit?: string }
  ): Promise<PaginatedResponse<Equipement>> {
    const { data } = await api.get("/equipements", {
      params: { page, page_size: pageSize, ...filters },
    });
    return data;
  },

  async get(id: number): Promise<Equipement> {
    const { data } = await api.get(`/equipements/${id}`);
    return data;
  },

  async create(payload: EquipementCreate): Promise<Equipement> {
    const { data } = await api.post("/equipements", payload);
    return data;
  },

  async update(id: number, payload: Partial<EquipementCreate>): Promise<Equipement> {
    const { data } = await api.put(`/equipements/${id}`, payload);
    return data;
  },

  async delete(id: number): Promise<MessageResponse> {
    const { data } = await api.delete(`/equipements/${id}`);
    return data;
  },
};

// ── Frameworks ──
export const frameworksApi = {
  async list(page = 1, pageSize = 20, activeOnly = true): Promise<PaginatedResponse<FrameworkSummary>> {
    const { data } = await api.get("/frameworks", {
      params: { page, page_size: pageSize, active_only: activeOnly },
    });
    return data;
  },

  async get(id: number): Promise<Framework> {
    const { data } = await api.get(`/frameworks/${id}`);
    return data;
  },

  async versions(id: number): Promise<FrameworkSummary[]> {
    const { data } = await api.get(`/frameworks/${id}/versions`);
    return data;
  },

  async clone(id: number, newVersion: string, newName?: string): Promise<Framework> {
    const { data } = await api.post(`/frameworks/${id}/clone`, {
      new_version: newVersion,
      new_name: newName,
    });
    return data;
  },

  async exportYaml(id: number): Promise<Blob> {
    const { data } = await api.get(`/frameworks/${id}/export`, {
      responseType: "blob",
    });
    return data;
  },

  async sync(): Promise<MessageResponse> {
    const { data } = await api.post("/frameworks/sync");
    return data;
  },

  async create(payload: FrameworkCreatePayload): Promise<Framework> {
    const { data } = await api.post("/frameworks", payload);
    return data;
  },

  async update(id: number, payload: FrameworkCreatePayload): Promise<Framework> {
    const { data } = await api.put(`/frameworks/${id}`, payload);
    return data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/frameworks/${id}`);
  },
};

// ── Campaigns ──
export const campaignsApi = {
  async list(page = 1, pageSize = 20, auditId?: number): Promise<PaginatedResponse<CampaignSummary>> {
    const { data } = await api.get("/assessments/campaigns", {
      params: { page, page_size: pageSize, audit_id: auditId },
    });
    return data;
  },

  async get(id: number): Promise<Campaign> {
    const { data } = await api.get(`/assessments/campaigns/${id}`);
    return data;
  },

  async create(payload: CampaignCreate): Promise<CampaignSummary> {
    const { data } = await api.post("/assessments/campaigns", payload);
    return data;
  },

  async update(id: number, payload: { name?: string; description?: string; status?: string }): Promise<CampaignSummary> {
    const { data } = await api.put(`/assessments/campaigns/${id}`, payload);
    return data;
  },

  async start(id: number): Promise<MessageResponse> {
    const { data } = await api.post(`/assessments/campaigns/${id}/start`);
    return data;
  },

  async complete(id: number): Promise<MessageResponse> {
    const { data } = await api.post(`/assessments/campaigns/${id}/complete`);
    return data;
  },

  async score(id: number): Promise<Score> {
    const { data } = await api.get(`/assessments/campaigns/${id}/score`);
    return data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/assessments/campaigns/${id}`);
  },
};

// ── Assessments ──
export const assessmentsApi = {
  async create(campaignId: number, payload: AssessmentCreate): Promise<Assessment> {
    const { data } = await api.post("/assessments", payload, {
      params: { campaign_id: campaignId },
    });
    return data;
  },

  async get(id: number): Promise<Assessment> {
    const { data } = await api.get(`/assessments/${id}`);
    return data;
  },

  async score(id: number): Promise<Score> {
    const { data } = await api.get(`/assessments/${id}/score`);
    return data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/assessments/${id}`);
  },

  async updateResult(
    resultId: number,
    payload: Partial<Pick<ControlResult, "status" | "evidence" | "comment" | "remediation_note">>
  ): Promise<ControlResult> {
    const { data } = await api.put(`/assessments/results/${resultId}`, payload);
    return data;
  },
};

// ── Health ──
export const healthApi = {
  async check(): Promise<{ status: string; service: string; version: string }> {
    const { data } = await api.get("/health");
    return data;
  },
};

// ── Attachments (Pièces jointes) ──
export const attachmentsApi = {
  async list(controlResultId: number): Promise<Attachment[]> {
    const { data } = await api.get(`/attachments/control-result/${controlResultId}`);
    return data;
  },

  async upload(
    controlResultId: number,
    file: File,
    description?: string
  ): Promise<Attachment> {
    const form = new FormData();
    form.append("file", file);
    if (description) form.append("description", description);
    const { data } = await api.post(
      `/attachments/control-result/${controlResultId}/upload`,
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },

  async delete(attachmentId: number): Promise<void> {
    await api.delete(`/attachments/${attachmentId}`);
  },

  downloadUrl(attachmentId: number): string {
    return `/api/v1/attachments/${attachmentId}/download`;
  },

  previewUrl(attachmentId: number): string {
    return `/api/v1/attachments/${attachmentId}/preview`;
  },
};

// scansApi supprime — le scan nmap est deleguee a l'agent distant (agentsApi.dispatch).

export const networkMapApi = {
  async getSiteMap(siteId: number): Promise<NetworkMap> {
    const { data } = await api.get(`/network-map/site/${siteId}`);
    return data;
  },

  async saveSiteLayout(siteId: number, layoutData: NetworkMap["layout_data"]): Promise<{ message: string }> {
    const { data } = await api.put(`/network-map/site/${siteId}/layout`, {
      layout_data: layoutData,
    });
    return data;
  },

  async listLinks(siteId: number): Promise<NetworkLink[]> {
    const { data } = await api.get("/network-map/links", { params: { site_id: siteId } });
    return data;
  },

  async getLink(linkId: number): Promise<NetworkLink> {
    const { data } = await api.get(`/network-map/links/${linkId}`);
    return data;
  },

  async createLink(payload: NetworkLinkCreate): Promise<NetworkLink> {
    const { data } = await api.post("/network-map/links", payload);
    return data;
  },

  async updateLink(linkId: number, payload: Partial<NetworkLinkCreate>): Promise<NetworkLink> {
    const { data } = await api.put(`/network-map/links/${linkId}`, payload);
    return data;
  },

  async deleteLink(linkId: number): Promise<{ message: string }> {
    const { data } = await api.delete(`/network-map/links/${linkId}`);
    return data;
  },

  async getOverview(entrepriseId: number): Promise<MultiSiteOverview> {
    const { data } = await api.get(`/network-map/overview/${entrepriseId}`);
    return data;
  },

  async getSiteConnection(connectionId: number): Promise<SiteConnection> {
    const { data } = await api.get(`/network-map/site-connections/${connectionId}`);
    return data;
  },

  async listSiteConnections(entrepriseId: number): Promise<SiteConnection[]> {
    const { data } = await api.get("/network-map/site-connections", {
      params: { entreprise_id: entrepriseId },
    });
    return data;
  },

  async createSiteConnection(payload: SiteConnectionCreate): Promise<SiteConnection> {
    const { data } = await api.post("/network-map/site-connections", payload);
    return data;
  },

  async updateSiteConnection(connectionId: number, payload: Partial<SiteConnectionCreate>): Promise<SiteConnection> {
    const { data } = await api.put(`/network-map/site-connections/${connectionId}`, payload);
    return data;
  },

  async deleteSiteConnection(connectionId: number): Promise<{ message: string }> {
    const { data } = await api.delete(`/network-map/site-connections/${connectionId}`);
    return data;
  },
};

export const vlansApi = {
  async list(siteId: number): Promise<VlanDefinition[]> {
    const { data } = await api.get("/network-map/vlans", { params: { site_id: siteId } });
    return data;
  },

  async get(vlanDefId: number): Promise<VlanDefinition> {
    const { data } = await api.get(`/network-map/vlans/${vlanDefId}`);
    return data;
  },

  async create(payload: VlanDefinitionCreate): Promise<VlanDefinition> {
    const { data } = await api.post("/network-map/vlans", payload);
    return data;
  },

  async update(vlanDefId: number, payload: VlanDefinitionUpdate): Promise<VlanDefinition> {
    const { data } = await api.put(`/network-map/vlans/${vlanDefId}`, payload);
    return data;
  },

  async delete(vlanDefId: number): Promise<{ message: string }> {
    const { data } = await api.delete(`/network-map/vlans/${vlanDefId}`);
    return data;
  },
};

// ── ORADAD ──
export const oradadApi = {
  async listTasks(): Promise<OradadTask[]> {
    const { data } = await api.get<OradadTask[]>("/oradad/tasks");
    return data;
  },

  async analyze(taskUuid: string): Promise<AnssiReport> {
    const { data } = await api.post<AnssiReport>(`/oradad/analyze/${taskUuid}`);
    return data;
  },

  async getReport(taskUuid: string): Promise<AnssiReport> {
    const { data } = await api.get<AnssiReport>(`/oradad/report/${taskUuid}`);
    return data;
  },

  // Config profiles
  async listConfigs(): Promise<OradadConfig[]> {
    const { data } = await api.get<OradadConfig[]>("/oradad/configs");
    return data;
  },

  async createConfig(payload: OradadConfigCreate): Promise<OradadConfig> {
    const { data } = await api.post<OradadConfig>("/oradad/configs", payload);
    return data;
  },

  async updateConfig(id: number, payload: Partial<OradadConfigCreate>): Promise<OradadConfig> {
    const { data } = await api.put<OradadConfig>(`/oradad/configs/${id}`, payload);
    return data;
  },

  async deleteConfig(id: number): Promise<void> {
    await api.delete(`/oradad/configs/${id}`);
  },
};

// ── Agents ──
export const agentsApi = {
  async list(): Promise<Agent[]> {
    const { data } = await api.get<Agent[]>("/agents/");
    return data;
  },

  async create(payload: AgentCreateRequest): Promise<AgentCreateResponse> {
    const { data } = await api.post<AgentCreateResponse>("/agents/create", payload);
    return data;
  },

  async revoke(agentUuid: string): Promise<AgentRevokeResponse> {
    const { data } = await api.delete<AgentRevokeResponse>(`/agents/${agentUuid}`);
    return data;
  },

  async update(agentUuid: string, payload: AgentUpdateRequest): Promise<Agent> {
    const { data } = await api.patch<Agent>(`/agents/${agentUuid}`, payload);
    return data;
  },

  async getSupportedTools(): Promise<string[]> {
    const { data } = await api.get<{ tools: string[] }>("/agents/supported-tools");
    return data.tools;
  },


  async dispatch(payload: {
    agent_uuid: string;
    tool: string;
    parameters?: Record<string, unknown>;
    audit_id?: number;
  }): Promise<Record<string, unknown>> {
    const { data } = await api.post("/agents/tasks/dispatch", payload);
    return data;
  },

  async listTasks(opts?: { tool?: string; agent_id?: number; limit?: number }): Promise<AgentTask[]> {
    const params: Record<string, string | number> = {};
    if (opts?.tool) params.tool = opts.tool;
    if (opts?.agent_id != null) params.agent_id = opts.agent_id;
    if (opts?.limit != null) params.limit = opts.limit;
    const { data } = await api.get<AgentTask[]>("/agents/tasks", { params });
    return data;
  },

  async deleteTask(taskUuid: string): Promise<{ detail: string }> {
    const { data } = await api.delete<{ detail: string }>(`/agents/tasks/${taskUuid}`);
    return data;
  },

  async getTaskArtifacts(taskUuid: string): Promise<TaskArtifact[]> {
    const { data } = await api.get<TaskArtifact[]>(`/agents/tasks/${taskUuid}/artifacts`);
    return data;
  },
};

// ── Tools (Config Parser + SSL Checker) ──
export const toolsApi = {
  // Config Parser
  async analyzeConfig(
    file: File,
    equipementId?: number
  ): Promise<ConfigUploadResponse> {
    const form = new FormData();
    form.append("file", file);
    if (equipementId) form.append("equipement_id", String(equipementId));
    const { data } = await api.post("/tools/config-analysis", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  async listVendors(): Promise<{ vendors: VendorInfo[] }> {
    const { data } = await api.get("/tools/config-analysis/vendors");
    return data;
  },

  // Config Analyses (persistées)
  async listConfigAnalyses(equipementId?: number): Promise<ConfigAnalysisSummary[]> {
    const params = equipementId ? { equipement_id: equipementId } : {};
    const { data } = await api.get("/tools/config-analyses", { params });
    return data;
  },

  async getConfigAnalysis(configId: number): Promise<ConfigAnalysisRead> {
    const { data } = await api.get(`/tools/config-analyses/${configId}`);
    return data;
  },

  async deleteConfigAnalysis(configId: number): Promise<void> {
    await api.delete(`/tools/config-analyses/${configId}`);
  },

  async prefillAudit(configId: number, assessmentId: number): Promise<PrefillResult> {
    const { data } = await api.post(
      `/tools/config-analyses/${configId}/prefill/${assessmentId}`
    );
    return data;
  },

  async listAssessmentsForEquipment(equipementId: number): Promise<
    { id: number; campaign_id: number; framework_id: number; framework_name: string; created_at: string }[]
  > {
    const { data } = await api.get(`/tools/assessments-for-equipment/${equipementId}`);
    return data;
  },

  // SSL Checker
  async sslCheck(request: SSLCheckRequest): Promise<SSLCheckResult> {
    const { data } = await api.post("/tools/ssl-check", request);
    return data;
  },

  async sslCheckBatch(
    requests: SSLCheckRequest[]
  ): Promise<SSLCheckResult[]> {
    const { data } = await api.post("/tools/ssl-check/batch", requests);
    return data;
  },

  // Collecte SSH / WinRM
  async launchCollect(params: CollectCreate): Promise<CollectResultSummary> {
    const { data } = await api.post("/tools/collect", params);
    return data;
  },

  async listCollects(equipementId?: number): Promise<CollectResultSummary[]> {
    const params = equipementId ? { equipement_id: equipementId } : {};
    const { data } = await api.get("/tools/collects", { params });
    return data;
  },

  async getCollect(collectId: number): Promise<CollectResultRead> {
    const { data } = await api.get(`/tools/collects/${collectId}`);
    return data;
  },

  async deleteCollect(collectId: number): Promise<void> {
    await api.delete(`/tools/collects/${collectId}`);
  },

  async prefillFromCollect(collectId: number, assessmentId: number): Promise<PrefillResult> {
    const { data } = await api.post(
      `/tools/collects/${collectId}/prefill/${assessmentId}`
    );
    return data;
  },

  // Audit Active Directory
  async launchADAudit(params: ADAuditCreate): Promise<ADAuditResultSummary> {
    const { data } = await api.post("/tools/ad-audit", params);
    return data;
  },

  async listADAudits(equipementId?: number): Promise<ADAuditResultSummary[]> {
    const params = equipementId ? { equipement_id: equipementId } : {};
    const { data } = await api.get("/tools/ad-audits", { params });
    return data;
  },

  async getADAudit(auditId: number): Promise<ADAuditResultRead> {
    const { data } = await api.get(`/tools/ad-audits/${auditId}`);
    return data;
  },

  async deleteADAudit(auditId: number): Promise<void> {
    await api.delete(`/tools/ad-audits/${auditId}`);
  },

  async prefillFromADAudit(auditId: number, assessmentId: number): Promise<PrefillResult> {
    const { data } = await api.post(
      `/tools/ad-audits/${auditId}/prefill/${assessmentId}`
    );
    return data;
  },


  // Monkey365
  async launchMonkey365Scan(data: Monkey365ScanCreate): Promise<Monkey365ScanResultSummary> {
    const response = await api.post("/tools/monkey365/run", data);
    return response.data;
  },

  async listMonkey365Scans(entrepriseId: number): Promise<Monkey365ScanResultSummary[]> {
    const response = await api.get(`/tools/monkey365/scans/${entrepriseId}`);
    return response.data;
  },

  async getMonkey365ScanDetail(resultId: number): Promise<Monkey365ScanResultDetail> {
    const response = await api.get(`/tools/monkey365/scans/result/${resultId}`);
    return response.data;
  },

  async deleteMonkey365Scan(resultId: number): Promise<{ message: string }> {
    const response = await api.delete(`/tools/monkey365/scans/${resultId}`);
    return response.data;
  },

  async getMonkey365ScanLogs(resultId: number): Promise<Monkey365ScanLogs> {
    const response = await api.get(`/tools/monkey365/scans/result/${resultId}/logs`);
    return response.data;
  },

  async cancelMonkey365Scan(resultId: number): Promise<Monkey365ScanResultSummary> {
    const response = await api.post(`/tools/monkey365/scans/${resultId}/cancel`);
    return response.data;
  },

  async openMonkey365Report(resultId: number): Promise<void> {
    const response = await api.get(`/tools/monkey365/scans/result/${resultId}/report`, {
      responseType: "blob",
    });
    const blob = new Blob([response.data], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const win = window.open(url, "_blank");
    // Révoquer l'URL objet après que le navigateur a eu le temps de charger la page
    if (win) {
      win.addEventListener("load", () => URL.revokeObjectURL(url), { once: true });
    } else {
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    }
  },

  async importMonkey365ToAudit(resultId: number, auditId: number): Promise<import("@/types/api").Monkey365ImportResult> {
    const { data } = await api.post(`/tools/monkey365/scans/${resultId}/import-to-audit`, { audit_id: auditId });
    return data;
  },
};

// ── Tags ──
export const tagsApi = {
  async list(params?: { audit_id?: number; scope?: string }): Promise<PaginatedResponse<Tag>> {
    const { data } = await api.get<PaginatedResponse<Tag>>("/tags", { params });
    return data;
  },
  async create(name: string, color?: string, scope?: string, auditId?: number): Promise<Tag> {
    const { data } = await api.post<Tag>("/tags", {
      name, color: color ?? "#6B7280", scope: scope ?? "global", audit_id: auditId ?? null,
    });
    return data;
  },
  async update(id: number, updates: { name?: string; color?: string }): Promise<Tag> {
    const { data } = await api.put<Tag>(`/tags/${id}`, updates);
    return data;
  },
  async remove(id: number): Promise<void> {
    await api.delete(`/tags/${id}`);
  },
  async associate(tagId: number, taggableType: string, taggableId: number): Promise<TagAssociation> {
    const { data } = await api.post<TagAssociation>("/tags/associate", {
      tag_id: tagId, taggable_type: taggableType, taggable_id: taggableId,
    });
    return data;
  },
  async dissociate(tagId: number, taggableType: string, taggableId: number): Promise<void> {
    await api.delete("/tags/associate", {
      params: { tag_id: tagId, taggable_type: taggableType, taggable_id: taggableId },
    });
  },
  async getEntityTags(taggableType: string, taggableId: number): Promise<Tag[]> {
    const { data } = await api.get<Tag[]>(`/tags/entity/${taggableType}/${taggableId}`);
    return data;
  },
};

// ── Checklists ──
export const checklistsApi = {
  async listTemplates(category?: string): Promise<ChecklistTemplate[]> {
    const params = category ? { category } : {};
    const { data } = await api.get<ChecklistTemplate[]>("/checklists/templates", { params });
    return data;
  },

  async getTemplate(id: number): Promise<ChecklistTemplateDetail> {
    const { data } = await api.get<ChecklistTemplateDetail>(`/checklists/templates/${id}`);
    return data;
  },

  async createInstance(templateId: number, auditId: number, siteId?: number): Promise<ChecklistInstance> {
    const { data } = await api.post<ChecklistInstance>("/checklists/instances", {
      template_id: templateId, audit_id: auditId, site_id: siteId ?? null,
    });
    return data;
  },

  async listInstances(auditId: number): Promise<ChecklistInstance[]> {
    const { data } = await api.get<ChecklistInstance[]>("/checklists/instances", { params: { audit_id: auditId } });
    return data;
  },

  async getInstance(id: number): Promise<ChecklistInstanceDetail> {
    const { data } = await api.get<ChecklistInstanceDetail>(`/checklists/instances/${id}`);
    return data;
  },

  async deleteInstance(id: number): Promise<void> {
    await api.delete(`/checklists/instances/${id}`);
  },

  async completeInstance(id: number): Promise<ChecklistInstance> {
    const { data } = await api.post<ChecklistInstance>(`/checklists/instances/${id}/complete`);
    return data;
  },

  async respondToItem(instanceId: number, itemId: number, status: string, note?: string): Promise<ChecklistResponse> {
    const { data } = await api.put<ChecklistResponse>(
      `/checklists/instances/${instanceId}/items/${itemId}`,
      { status, note: note ?? null },
    );
    return data;
  },

  async getProgress(instanceId: number): Promise<ChecklistProgress> {
    const { data } = await api.get<ChecklistProgress>(`/checklists/instances/${instanceId}/progress`);
    return data;
  },
};
