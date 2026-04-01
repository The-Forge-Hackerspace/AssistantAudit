"use client";

import { useState } from "react";
import { frameworksApi } from "@/services/api";
import type { FrameworkSummary, Framework } from "@/types";
import { FrameworkList } from "./components/framework-list";
import { FrameworkDetail } from "./components/framework-detail";
import { FrameworkEditor } from "./components/framework-editor";

// ── Main Page ──
export default function FrameworksPage() {
  const [view, setView] = useState<"list" | "detail" | "editor">("list");
  const [selectedFramework, setSelectedFramework] = useState<Framework | null>(null);
  const [editingFramework, setEditingFramework] = useState<Framework | null>(null);
  const [listKey, setListKey] = useState(0);

  const openDetail = async (fw: FrameworkSummary) => {
    try {
      const full = await frameworksApi.get(fw.id);
      setSelectedFramework(full);
      setView("detail");
    } catch {
      /* ignore */
    }
  };

  const openEditor = (fw?: Framework) => {
    setEditingFramework(fw || null);
    setView("editor");
  };

  const backToList = () => {
    setView("list");
    setSelectedFramework(null);
    setEditingFramework(null);
    setListKey((k) => k + 1);
  };

  if (view === "editor") {
    return (
      <FrameworkEditor
        framework={editingFramework}
        onBack={() => {
          if (selectedFramework && !editingFramework) {
            setView("list");
          } else if (editingFramework) {
            setView("detail");
          } else {
            setView("list");
          }
          setEditingFramework(null);
        }}
        onSaved={backToList}
      />
    );
  }

  if (view === "detail" && selectedFramework) {
    return (
      <FrameworkDetail
        framework={selectedFramework}
        onBack={() => {
          setView("list");
          setSelectedFramework(null);
        }}
        onEdit={() => openEditor(selectedFramework)}
        onDeleted={backToList}
      />
    );
  }

  return <FrameworkList key={listKey} onSelect={openDetail} onCreate={() => openEditor()} />;
}
