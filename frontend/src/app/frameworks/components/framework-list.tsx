"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  BookOpen,
  Search,
  Loader2,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Shield,
  Eye,
  Plus,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/auth-context";
import { frameworksApi } from "@/services/api";
import type { FrameworkSummary } from "@/types";
import { cn } from "@/lib/utils";
import { ENGINE_LABELS, getFrameworkIcon } from "@/lib/constants";

// ── Props ──

export interface FrameworkListProps {
  onSelect: (fw: FrameworkSummary) => void;
  onCreate: () => void;
}

// ══════════════════════════════════════════════════════════
// ──  LIST VIEW
// ══════════════════════════════════════════════════════════
export function FrameworkList({ onSelect, onCreate }: FrameworkListProps) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [frameworks, setFrameworks] = useState<FrameworkSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const pageSize = 20;

  const loadFrameworks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await frameworksApi.list(page, pageSize);
      setFrameworks(res.items);
      setTotal(res.total);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadFrameworks();
  }, [loadFrameworks]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await frameworksApi.sync();
      loadFrameworks();
    } catch {
      /* ignore */
    } finally {
      setSyncing(false);
    }
  };

  const filtered = useMemo(() => {
    if (!search.trim()) return frameworks;
    const q = search.toLowerCase();
    return frameworks.filter(
      (fw) =>
        fw.name.toLowerCase().includes(q) ||
        fw.ref_id.toLowerCase().includes(q) ||
        (fw.engine || "").toLowerCase().includes(q)
    );
  }, [frameworks, search]);

  const pages = Math.ceil(total / pageSize);

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Référentiels</h1>
          <p className="text-muted-foreground">
            {total} référentiel{total !== 1 ? "s" : ""} d&apos;audit disponibles
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <Button onClick={onCreate}>
              <Plus data-icon="inline-start" />
              Nouveau référentiel
            </Button>
          )}
          <Button variant="outline" onClick={handleSync} disabled={syncing}>
            <RefreshCw className={cn(syncing && "animate-spin")} data-icon="inline-start" />
            {syncing ? "Synchronisation\u2026" : "Synchroniser"}
          </Button>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher un référentiel\u2026"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* Frameworks Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="size-8 animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">
            <BookOpen className="size-10 mx-auto mb-3 opacity-50" />
            <p className="font-medium">Aucun référentiel trouvé</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((fw) => (
            <FrameworkCard key={fw.id} framework={fw} onClick={() => onSelect(fw)} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="icon"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            <ChevronLeft />
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} / {pages}
          </span>
          <Button
            variant="outline"
            size="icon"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            <ChevronRight />
          </Button>
        </div>
      )}
    </div>
  );
}

// ── Framework Card ──
function FrameworkCard({
  framework: fw,
  onClick,
}: {
  framework: FrameworkSummary;
  onClick: () => void;
}) {
  const icon = getFrameworkIcon(fw.ref_id);

  return (
    <Card
      className="cursor-pointer hover:shadow-md hover:border-primary/30 transition-all group"
      onClick={onClick}
    >
      <CardContent className="pt-6 flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <span className="text-2xl shrink-0">{icon}</span>
            <div className="min-w-0">
              <p className="font-semibold truncate group-hover:text-primary transition-colors">
                {fw.name}
              </p>
              <p className="text-xs text-muted-foreground font-mono">{fw.ref_id}</p>
            </div>
          </div>
          <Badge variant="outline" className="text-[10px] shrink-0 ml-2">
            v{fw.version}
          </Badge>
        </div>

        {/* Stats row */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Shield className="h-3.5 w-3.5" />
            <span>{fw.total_controls} contrôles</span>
          </div>
          <Badge
            variant="secondary"
            className="text-[10px]"
          >
            {ENGINE_LABELS[fw.engine || "manual"] || fw.engine}
          </Badge>
        </div>

        {/* Footer: view button hint */}
        <div className="flex items-center justify-end text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
          <Eye className="size-3 mr-1" />
          Voir le détail
        </div>
      </CardContent>
    </Card>
  );
}
