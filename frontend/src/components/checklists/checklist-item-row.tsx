"use client";

import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { ChecklistItem, ChecklistResponse } from "@/types";

type ItemStatus = "OK" | "NOK" | "NA" | "UNCHECKED";

interface ChecklistItemRowProps {
  item: ChecklistItem;
  response: ChecklistResponse | undefined;
  onRespond: (itemId: number, status: ItemStatus, note?: string) => Promise<void>;
}

const STATUS_CONFIG: Record<ItemStatus, { label: string; className: string }> = {
  OK: { label: "✓ OK", className: "bg-green-500 text-white border-green-600 hover:bg-green-600" },
  NOK: { label: "✗ NOK", className: "bg-red-500 text-white border-red-600 hover:bg-red-600" },
  NA: { label: "— N/A", className: "bg-gray-400 text-white border-gray-500 hover:bg-gray-500" },
  UNCHECKED: { label: "?", className: "bg-white text-gray-600 border-gray-300 hover:bg-gray-100" },
};

export function ChecklistItemRow({ item, response, onRespond }: ChecklistItemRowProps) {
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useState(response?.note ?? "");
  const [saving, setSaving] = useState(false);

  const currentStatus: ItemStatus = (response?.status as ItemStatus) ?? "UNCHECKED";

  const handleStatus = async (status: ItemStatus) => {
    setSaving(true);
    try {
      await onRespond(item.id, status, note || undefined);
    } finally {
      setSaving(false);
    }
  };

  const handleNoteBlur = async () => {
    if (currentStatus !== "UNCHECKED") {
      setSaving(true);
      try {
        await onRespond(item.id, currentStatus, note || undefined);
      } finally {
        setSaving(false);
      }
    }
  };

  return (
    <div
      className={cn(
        "border-b last:border-b-0 py-3 px-4 transition-colors",
        currentStatus === "OK" && "bg-green-50",
        currentStatus === "NOK" && "bg-red-50",
        currentStatus === "NA" && "bg-gray-50",
      )}
    >
      {/* En-tête de l'item */}
      <button
        type="button"
        className="w-full text-left flex items-start gap-3 mb-3"
        onClick={() => setNoteOpen((v) => !v)}
      >
        {item.ref_code && (
          <span className="font-mono font-bold text-sm text-muted-foreground shrink-0 mt-0.5 min-w-[2.5rem]">
            {item.ref_code}
          </span>
        )}
        <span className="text-base font-medium leading-tight flex-1">{item.label}</span>
      </button>

      {/* Boutons de statut — touch-friendly (min 48px) */}
      <div className="flex gap-2 flex-wrap">
        {(["OK", "NOK", "NA", "UNCHECKED"] as ItemStatus[]).map((status) => {
          const cfg = STATUS_CONFIG[status];
          const isActive = currentStatus === status;
          return (
            <button
              key={status}
              type="button"
              disabled={saving}
              onClick={() => handleStatus(status)}
              className={cn(
                "min-h-[48px] px-5 rounded-lg border-2 font-semibold text-sm transition-all active:scale-95",
                isActive
                  ? cfg.className + " ring-2 ring-offset-2 ring-current"
                  : "bg-white text-gray-500 border-gray-200 hover:border-gray-400",
                saving && "opacity-60 cursor-not-allowed",
              )}
            >
              {cfg.label}
            </button>
          );
        })}
      </div>

      {/* Zone de note (ouverte au tap sur l'item ou si note existante) */}
      {(noteOpen || response?.note) && (
        <div className="mt-3">
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={handleNoteBlur}
            placeholder="Note libre…"
            className="text-sm min-h-[72px] resize-none"
          />
        </div>
      )}
    </div>
  );
}
