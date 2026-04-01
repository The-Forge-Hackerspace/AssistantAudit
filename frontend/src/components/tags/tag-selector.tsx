"use client";

import { useEffect, useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { tagsApi } from "@/services/api";
import type { Tag } from "@/types";
import { TagBadge } from "./tag-badge";
import { toast } from "sonner";

interface TagSelectorProps {
  taggableType: "equipement" | "control_result" | "checklist_response" | "scan_host";
  taggableId: number;
}

/** Sélecteur de tags pour une entité : affiche les tags actuels et permet d'en ajouter/retirer. */
export function TagSelector({ taggableType, taggableId }: TagSelectorProps) {
  const [entityTags, setEntityTags] = useState<Tag[]>([]);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  // Charge les tags disponibles et les tags de l'entité
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [allRes, entityRes] = await Promise.all([
          tagsApi.list(),
          tagsApi.getEntityTags(taggableType, taggableId),
        ]);
        setAllTags(allRes.items);
        setEntityTags(entityRes);
      } catch {
        toast.error("Erreur lors du chargement des tags");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [taggableType, taggableId]);

  const entityTagIds = new Set(entityTags.map((t) => t.id));
  const availableTags = allTags.filter((t) => !entityTagIds.has(t.id));

  const handleAssociate = async (tag: Tag) => {
    setOpen(false);
    try {
      await tagsApi.associate(tag.id, taggableType, taggableId);
      setEntityTags((prev) => [...prev, tag]);
    } catch {
      toast.error(`Erreur lors de l'ajout du tag ${tag.name}`);
    }
  };

  const handleDissociate = async (tag: Tag) => {
    try {
      await tagsApi.dissociate(tag.id, taggableType, taggableId);
      setEntityTags((prev) => prev.filter((t) => t.id !== tag.id));
    } catch {
      toast.error(`Erreur lors du retrait du tag ${tag.name}`);
    }
  };

  if (loading) {
    return <Loader2 className="size-4 animate-spin text-muted-foreground" />;
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {entityTags.map((tag) => (
        <TagBadge
          key={tag.id}
          tag={tag}
          onRemove={() => handleDissociate(tag)}
        />
      ))}
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="icon"
            className="size-6 rounded-full"
            aria-label="Ajouter un tag"
          >
            <Plus className="size-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-48">
          {availableTags.length === 0 ? (
            <p className="px-2 py-1.5 text-xs text-muted-foreground">
              Tous les tags sont déjà associés
            </p>
          ) : (
            availableTags.map((tag) => (
              <DropdownMenuItem
                key={tag.id}
                onClick={() => handleAssociate(tag)}
                className="gap-2"
              >
                <span
                  className="size-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: tag.color }}
                />
                {tag.name}
              </DropdownMenuItem>
            ))
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
