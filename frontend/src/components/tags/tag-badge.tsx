"use client";

import { X } from "lucide-react";
import type { Tag } from "@/types";
import { cn } from "@/lib/utils";

interface TagBadgeProps {
  tag: Tag;
  onRemove?: () => void;
  size?: "sm" | "md";
}

/** Badge coloré affichant le nom d'un tag avec sa couleur. */
export function TagBadge({ tag, onRemove, size = "sm" }: TagBadgeProps) {
  const hex = tag.color;

  // Convertit la couleur hex en rgba avec opacité réduite pour le fond
  const bgStyle = `${hex}26`; // ~15% opacité
  const borderStyle = `${hex}66`; // ~40% opacité

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border font-medium whitespace-nowrap",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm"
      )}
      style={{
        backgroundColor: bgStyle,
        borderColor: borderStyle,
        color: hex,
      }}
    >
      {tag.name}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="rounded-full hover:opacity-70 transition-opacity"
          aria-label={`Retirer le tag ${tag.name}`}
        >
          <X className={size === "sm" ? "size-3" : "size-3.5"} />
        </button>
      )}
    </span>
  );
}
