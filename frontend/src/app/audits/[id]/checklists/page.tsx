"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ClipboardList, Loader2, Play, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChecklistFiller } from "@/components/checklists/checklist-filler";
import { checklistsApi } from "@/services/api";
import { toast } from "sonner";
import type { ChecklistTemplate, ChecklistInstance } from "@/types";

export default function ChecklistsPage() {
  const params = useParams();
  const router = useRouter();
  const auditId = Number(params.id);

  const [templates, setTemplates] = useState<ChecklistTemplate[]>([]);
  const [instances, setInstances] = useState<ChecklistInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeInstance, setActiveInstance] = useState<{ templateId: number; instanceId: number } | null>(null);
  const [creating, setCreating] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [tpls, insts] = await Promise.all([
        checklistsApi.listTemplates(),
        checklistsApi.listInstances(auditId),
      ]);
      setTemplates(tpls);
      setInstances(insts);
    } catch {
      toast.error("Impossible de charger les checklists.");
    } finally {
      setLoading(false);
    }
  }, [auditId]);

  useEffect(() => {
    if (auditId) load();
  }, [auditId, load]);

  const getInstanceForTemplate = (templateId: number) =>
    instances.find((i) => i.template_id === templateId);

  const handleStart = async (templateId: number) => {
    setCreating(templateId);
    try {
      const inst = await checklistsApi.createInstance(templateId, auditId);
      setInstances((prev) => [...prev, inst]);
      setActiveInstance({ templateId, instanceId: inst.id });
    } catch {
      toast.error("Erreur lors de la création de la checklist.");
    } finally {
      setCreating(null);
    }
  };

  const handleOpen = (templateId: number, instanceId: number) => {
    setActiveInstance({ templateId, instanceId });
  };

  const handleFillerCompleted = () => {
    setActiveInstance(null);
    load();
  };

  if (!auditId) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p>Identifiant d&apos;audit manquant.</p>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/audits")}>
          Retour aux audits
        </Button>
      </div>
    );
  }

  if (activeInstance) {
    return (
      <div className="flex flex-col gap-4">
        <Button
          variant="ghost"
          className="self-start gap-2"
          onClick={() => { setActiveInstance(null); load(); }}
        >
          <ArrowLeft data-icon="inline-start" />
          Retour aux checklists
        </Button>
        <ChecklistFiller
          templateId={activeInstance.templateId}
          instanceId={activeInstance.instanceId}
          onCompleted={handleFillerCompleted}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* En-tête */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" onClick={() => router.push("/audits")} className="gap-2">
          <ArrowLeft data-icon="inline-start" />
          Retour
        </Button>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ClipboardList className="size-6" />
            Checklists terrain
          </h1>
          <p className="text-sm text-muted-foreground">Audit #{auditId}</p>
        </div>
      </div>

      {/* Liste des templates */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="size-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {templates.length === 0 && (
            <Card>
              <CardContent className="text-center py-8 text-muted-foreground">
                Aucun template de checklist disponible.
              </CardContent>
            </Card>
          )}
          {templates.map((tpl) => {
            const instance = getInstanceForTemplate(tpl.id);
            const isCompleted = instance?.status === "completed";
            const isInProgress = instance?.status === "in_progress" || instance?.status === "draft";

            return (
              <Card key={tpl.id} className="overflow-hidden">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <CardTitle className="text-lg">{tpl.name}</CardTitle>
                      {tpl.description && (
                        <CardDescription className="mt-1">{tpl.description}</CardDescription>
                      )}
                      <div className="flex items-center gap-2 mt-2">
                        <Badge variant="outline" className="text-xs">{tpl.category}</Badge>
                        {isCompleted && (
                          <Badge className="text-xs bg-green-500 hover:bg-green-600">Terminée</Badge>
                        )}
                        {isInProgress && (
                          <Badge variant="secondary" className="text-xs">En cours</Badge>
                        )}
                        {!instance && (
                          <Badge variant="outline" className="text-xs text-muted-foreground">
                            Non démarrée
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Actions — gros boutons touch-friendly */}
                    <div className="shrink-0">
                      {!instance && (
                        <Button
                          size="lg"
                          className="min-h-[48px] gap-2"
                          onClick={() => handleStart(tpl.id)}
                          disabled={creating === tpl.id}
                        >
                          {creating === tpl.id ? (
                            <Loader2 className="animate-spin" />
                          ) : (
                            <Play className="size-4" />
                          )}
                          Démarrer
                        </Button>
                      )}
                      {isInProgress && instance && (
                        <Button
                          size="lg"
                          variant="outline"
                          className="min-h-[48px] gap-2"
                          onClick={() => handleOpen(tpl.id, instance.id)}
                        >
                          <RotateCcw className="size-4" />
                          Continuer
                        </Button>
                      )}
                      {isCompleted && instance && (
                        <Button
                          size="lg"
                          variant="ghost"
                          className="min-h-[48px] gap-2 text-green-600"
                          onClick={() => handleOpen(tpl.id, instance.id)}
                        >
                          Voir le résultat
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
