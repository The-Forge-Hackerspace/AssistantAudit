"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { ChecklistItemRow } from "./checklist-item-row";
import { ChecklistProgressBar } from "./checklist-progress";
import { checklistsApi } from "@/services/api";
import { toast } from "sonner";
import type {
  ChecklistTemplateDetail,
  ChecklistInstanceDetail,
  ChecklistProgress,
  ChecklistResponse,
} from "@/types";

type ItemStatus = "OK" | "NOK" | "NA" | "UNCHECKED";

interface ChecklistFillerProps {
  templateId: number;
  instanceId: number;
  onCompleted: () => void;
}

export function ChecklistFiller({ templateId, instanceId, onCompleted }: ChecklistFillerProps) {
  const [template, setTemplate] = useState<ChecklistTemplateDetail | null>(null);
  const [instance, setInstance] = useState<ChecklistInstanceDetail | null>(null);
  const [progress, setProgress] = useState<ChecklistProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);

  // Map item_id → réponse pour accès O(1)
  const [responseMap, setResponseMap] = useState<Map<number, ChecklistResponse>>(new Map());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [tpl, inst, prog] = await Promise.all([
        checklistsApi.getTemplate(templateId),
        checklistsApi.getInstance(instanceId),
        checklistsApi.getProgress(instanceId),
      ]);
      setTemplate(tpl);
      setInstance(inst);
      setProgress(prog);
      const map = new Map<number, ChecklistResponse>();
      for (const r of inst.responses) {
        map.set(r.item_id, r);
      }
      setResponseMap(map);
    } catch {
      toast.error("Impossible de charger la checklist.");
    } finally {
      setLoading(false);
    }
  }, [templateId, instanceId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRespond = async (itemId: number, status: ItemStatus, note?: string) => {
    const updated = await checklistsApi.respondToItem(instanceId, itemId, status, note);
    setResponseMap((prev) => {
      const next = new Map(prev);
      next.set(itemId, updated);
      return next;
    });
    // Mise à jour locale de la progression
    const prog = await checklistsApi.getProgress(instanceId);
    setProgress(prog);
  };

  const handleComplete = async () => {
    setCompleting(true);
    try {
      await checklistsApi.completeInstance(instanceId);
      toast.success("Checklist marquée comme terminée.");
      onCompleted();
    } catch {
      toast.error("Erreur lors de la finalisation.");
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!template || !instance || !progress) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Checklist introuvable.
      </div>
    );
  }

  const isCompleted = instance.status === "completed";

  return (
    <div className="flex flex-col gap-4">
      {/* En-tête avec progression */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">{template.name}</CardTitle>
            <Badge variant={isCompleted ? "default" : "outline"}>
              {isCompleted ? "Terminée" : instance.status === "in_progress" ? "En cours" : "Brouillon"}
            </Badge>
          </div>
          {template.description && (
            <p className="text-sm text-muted-foreground">{template.description}</p>
          )}
        </CardHeader>
        <CardContent>
          <ChecklistProgressBar progress={progress} />
        </CardContent>
      </Card>

      {/* Sections en Accordion */}
      <Accordion type="single" collapsible className="flex flex-col gap-2">
        {template.sections.map((section) => {
          const sectionAnswered = section.items.filter((it) => {
            const r = responseMap.get(it.id);
            return r && r.status !== "UNCHECKED";
          }).length;

          return (
            <Card key={section.id} className="overflow-hidden">
              <AccordionItem value={String(section.id)} className="border-0">
                <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-muted/30">
                  <div className="flex items-center gap-3 flex-1 text-left">
                    <span className="font-semibold text-base">{section.name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {sectionAnswered}/{section.items.length}
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="pb-0">
                  <div className="divide-y border-t">
                    {section.items.map((item) => (
                      <ChecklistItemRow
                        key={item.id}
                        item={item}
                        response={responseMap.get(item.id)}
                        onRespond={isCompleted ? async () => {} : handleRespond}
                      />
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Card>
          );
        })}
      </Accordion>

      {/* Bouton finalisation */}
      {!isCompleted && (
        <Button
          size="lg"
          className="min-h-[52px] text-base font-semibold"
          onClick={handleComplete}
          disabled={completing}
        >
          {completing ? (
            <Loader2 className="animate-spin" data-icon="inline-start" />
          ) : (
            <CheckCircle2 data-icon="inline-start" />
          )}
          Marquer comme terminée
        </Button>
      )}
    </div>
  );
}
