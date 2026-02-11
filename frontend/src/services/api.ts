import api, { setTokens, clearTokens } from "@/lib/api-client";
import type {
  TokenResponse,
  User,
  PaginatedResponse,
  Entreprise,
  EntrepriseCreate,
  Audit,
  AuditCreate,
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
  Scan,
  ScanCreate,
  ScanSummary,
  ScanHostDecision,
  ConfigUploadResponse,
  SSLCheckRequest,
  SSLCheckResult,
  VendorInfo,
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
    setTokens(data.access_token, data.refresh_token);
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

  logout() {
    clearTokens();
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
    filters?: { site_id?: number; type_equipement?: string; status_audit?: string }
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

// ── Scans (Scanner réseau) ──
export const scansApi = {
  async launch(data: ScanCreate): Promise<Scan> {
    const { data: result } = await api.post("/scans", data);
    return result;
  },

  async list(params?: {
    site_id?: number;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<ScanSummary>> {
    const { data } = await api.get("/scans", { params });
    return data;
  },

  async get(scanId: number): Promise<Scan> {
    const { data } = await api.get(`/scans/${scanId}`);
    return data;
  },

  async delete(scanId: number): Promise<void> {
    await api.delete(`/scans/${scanId}`);
  },

  async updateHostDecision(
    hostId: number,
    decision: ScanHostDecision
  ): Promise<Record<string, unknown>> {
    const { data } = await api.put(`/scans/hosts/${hostId}/decision`, decision);
    return data;
  },

  async linkHostToEquipement(
    hostId: number,
    equipementId: number
  ): Promise<Record<string, unknown>> {
    const { data } = await api.post(
      `/scans/hosts/${hostId}/link/${equipementId}`
    );
    return data;
  },

  async importAllKept(scanId: number): Promise<Record<string, unknown>> {
    const { data } = await api.post(`/scans/${scanId}/import-all`);
    return data;
  },

  async previewCommand(params: {
    scan_type: string;
    target?: string;
    custom_args?: string;
  }): Promise<{ command: string }> {
    const { data } = await api.get("/scans/preview-command", { params });
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
};
