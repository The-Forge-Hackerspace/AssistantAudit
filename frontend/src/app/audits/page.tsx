"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { auditsApi, entreprisesApi } from "@/services/api";
import type { Audit, Entreprise } from "@/types";
import { AuditListView } from "./components/audits-tab";
import { AuditDetailView } from "./components/audit-detail-view";

export default function AuditsPage() {
  return (
    <Suspense fallback={<div className="p-6">Chargement…</div>}>
      <AuditsContent />
    </Suspense>
  );
}

function AuditsContent() {
  const searchParams = useSearchParams();
  const initialEntreprise = searchParams.get("entreprise") || "all";

  // ── Global State ──
  const [view, setView] = useState<"list" | "detail">("list");
  const [selectedAudit, setSelectedAudit] = useState<Audit | null>(null);

  // ── Shared Data ──
  const [entreprises, setEntreprises] = useState<Entreprise[]>([]);
  const [entrepriseMap, setEntrepriseMap] = useState<Record<number, string>>({});

  // Load entreprises once
  useEffect(() => {
    const load = async () => {
      try {
        const res = await entreprisesApi.list(1, 100);
        setEntreprises(res.items);
        const map: Record<number, string> = {};
        res.items.forEach((e) => (map[e.id] = e.nom));
        setEntrepriseMap(map);
      } catch { /* ignore */ }
    };
    load();
  }, []);

  const openDetail = useCallback(async (audit: Audit) => {
    try {
      const detail = await auditsApi.get(audit.id);
      setSelectedAudit(detail);
      setView("detail");
    } catch {
      setSelectedAudit(audit);
      setView("detail");
    }
  }, []);

  const backToList = () => {
    setView("list");
    setSelectedAudit(null);
  };

  if (view === "detail" && selectedAudit) {
    return (
      <AuditDetailView
        audit={selectedAudit}
        entrepriseMap={entrepriseMap}
        onBack={backToList}
        onAuditUpdated={(a) => setSelectedAudit(a)}
      />
    );
  }

  return (
    <AuditListView
      entreprises={entreprises}
      entrepriseMap={entrepriseMap}
      initialEntreprise={initialEntreprise}
      onOpenDetail={openDetail}
    />
  );
}
