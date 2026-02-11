/**
 * SWR-based hooks for client-side data caching & revalidation.
 *
 * Usage:
 *   const { data, error, isLoading, mutate } = useEntreprises(page, pageSize);
 *
 * Benefits:
 *   - Automatic cache + deduplication
 *   - Background revalidation on focus
 *   - Instant UI with stale data while refreshing
 */
import useSWR from "swr";
import {
  entreprisesApi,
  sitesApi,
  equipementsApi,
  auditsApi,
  frameworksApi,
  campaignsApi,
} from "@/services/api";
import type {
  PaginatedResponse,
  Entreprise,
  Site,
  Equipement,
  Audit,
  FrameworkSummary,
  CampaignSummary,
} from "@/types";

// ─── Entreprises ─────────────────────────────────────────────

export function useEntreprises(page = 1, pageSize = 20) {
  return useSWR<PaginatedResponse<Entreprise>>(
    ["entreprises", page, pageSize],
    () => entreprisesApi.list(page, pageSize),
    { revalidateOnFocus: false }
  );
}

export function useEntreprise(id: number | null) {
  return useSWR(
    id ? ["entreprise", id] : null,
    () => entreprisesApi.get(id!),
    { revalidateOnFocus: false }
  );
}

// ─── Sites ───────────────────────────────────────────────────

export function useSites(page = 1, pageSize = 20, entrepriseId?: number) {
  return useSWR<PaginatedResponse<Site>>(
    ["sites", page, pageSize, entrepriseId],
    () => sitesApi.list(page, pageSize, entrepriseId),
    { revalidateOnFocus: false }
  );
}

// ─── Équipements ─────────────────────────────────────────────

export function useEquipements(
  page = 1,
  pageSize = 20,
  filters?: { site_id?: number; type_equipement?: string; status_audit?: string }
) {
  return useSWR<PaginatedResponse<Equipement>>(
    ["equipements", page, pageSize, filters],
    () => equipementsApi.list(page, pageSize, filters),
    { revalidateOnFocus: false }
  );
}

// ─── Audits ──────────────────────────────────────────────────

export function useAudits(page = 1, pageSize = 20) {
  return useSWR<PaginatedResponse<Audit>>(
    ["audits", page, pageSize],
    () => auditsApi.list(page, pageSize),
    { revalidateOnFocus: false }
  );
}

// ─── Frameworks ──────────────────────────────────────────────

export function useFrameworks(page = 1, pageSize = 20) {
  return useSWR<PaginatedResponse<FrameworkSummary>>(
    ["frameworks", page, pageSize],
    () => frameworksApi.list(page, pageSize),
    { revalidateOnFocus: false }
  );
}

// ─── Campaigns ───────────────────────────────────────────────

export function useCampaigns(auditId: number | null, page = 1, pageSize = 20) {
  return useSWR<PaginatedResponse<CampaignSummary>>(
    auditId ? ["campaigns", auditId, page, pageSize] : null,
    () => campaignsApi.list(page, pageSize, auditId!),
    { revalidateOnFocus: false }
  );
}
