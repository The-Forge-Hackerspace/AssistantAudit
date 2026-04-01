"use client";

import { useEffect, useState } from "react";
import { tagsApi } from "@/services/api";
import type { Tag } from "@/types";

interface TagFilterProps {
  onFilterChange: (selectedTagIds: number[]) => void;
  selectedTagIds?: number[];
}

/** Barre de filtres multi-tag : badges cliquables pour filtrer les listes. */
export function TagFilter({ onFilterChange, selectedTagIds = [] }: TagFilterProps) {
  const [tags, setTags] = useState<Tag[]>([]);

  useEffect(() => {
    tagsApi.list({ scope: "global" })
      .then((res) => setTags(res.items))
      .catch(() => {});
  }, []);

  const toggle = (tagId: number) => {
    const next = selectedTagIds.includes(tagId)
      ? selectedTagIds.filter((id) => id !== tagId)
      : [...selectedTagIds, tagId];
    onFilterChange(next);
  };

  if (tags.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {tags.map((tag) => {
        const active = selectedTagIds.includes(tag.id);
        return (
          <button
            key={tag.id}
            type="button"
            onClick={() => toggle(tag.id)}
            className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-all"
            style={
              active
                ? { backgroundColor: tag.color, borderColor: tag.color, color: "#fff" }
                : { backgroundColor: `${tag.color}1A`, borderColor: `${tag.color}66`, color: tag.color }
            }
            aria-pressed={active}
          >
            {tag.name}
          </button>
        );
      })}
      {selectedTagIds.length > 0 && (
        <button
          type="button"
          onClick={() => onFilterChange([])}
          className="text-xs text-muted-foreground hover:text-foreground underline"
        >
          Effacer
        </button>
      )}
    </div>
  );
}
