"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

interface PingCastleTerminalProps {
  token: string;
  /** Override the WebSocket URL (defaults to auto-detect from API URL) */
  wsUrl?: string;
}

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error" | "closed";

export default function PingCastleTerminal({ token, wsUrl }: PingCastleTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");

  const connect = useCallback(() => {
    if (!terminalRef.current || !token) return;

    // ── Initialize xterm.js ──
    if (termRef.current) {
      termRef.current.dispose();
    }

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace",
      theme: {
        background: "#1a1b26",
        foreground: "#a9b1d6",
        cursor: "#c0caf5",
        selectionBackground: "#33467c",
        black: "#15161e",
        red: "#f7768e",
        green: "#9ece6a",
        yellow: "#e0af68",
        blue: "#7aa2f7",
        magenta: "#bb9af7",
        cyan: "#7dcfff",
        white: "#a9b1d6",
      },
      convertEol: false,
      scrollback: 5000,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    termRef.current = term;
    fitAddonRef.current = fitAddon;

    // ── Build WebSocket URL ──
    let url = wsUrl;
    if (!url) {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const wsBase = apiBase.replace(/^http/, "ws");
      url = `${wsBase}/tools/pingcastle/terminal?token=${encodeURIComponent(token)}`;
    }

    term.writeln("\x1b[36m🏰 Connexion au terminal PingCastle...\x1b[0m\r");
    setStatus("connecting");

    // ── WebSocket ──
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      term.writeln("\x1b[32m✓ Connecté au serveur PingCastle\x1b[0m\r");
      term.writeln("");
    };

    ws.onmessage = (event) => {
      term.write(event.data);
    };

    ws.onclose = (event) => {
      setStatus("closed");
      term.writeln("");
      term.writeln(
        `\x1b[33m⚡ Connexion fermée${event.reason ? ` : ${event.reason}` : ""}\x1b[0m\r`
      );
    };

    ws.onerror = () => {
      setStatus("error");
      term.writeln("\x1b[31m✗ Erreur de connexion WebSocket\x1b[0m\r");
    };

    // ── Send keystrokes to WS ──
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });
  }, [token, wsUrl]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus("disconnected");
  }, []);

  // ── Handle window resize ──
  useEffect(() => {
    const handleResize = () => {
      if (fitAddonRef.current) {
        try {
          fitAddonRef.current.fit();
        } catch {
          // ignore fit errors during unmount
        }
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // ── Cleanup on unmount ──
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (termRef.current) {
        termRef.current.dispose();
        termRef.current = null;
      }
    };
  }, []);

  const statusColors: Record<ConnectionStatus, string> = {
    disconnected: "bg-gray-500",
    connecting: "bg-yellow-500 animate-pulse",
    connected: "bg-green-500",
    error: "bg-red-500",
    closed: "bg-orange-500",
  };

  const statusLabels: Record<ConnectionStatus, string> = {
    disconnected: "Déconnecté",
    connecting: "Connexion...",
    connected: "Connecté",
    error: "Erreur",
    closed: "Session terminée",
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${statusColors[status]}`} />
          <span className="text-sm text-muted-foreground">{statusLabels[status]}</span>
        </div>
        <div className="flex gap-2">
          {(status === "disconnected" || status === "closed" || status === "error") && (
            <button
              onClick={connect}
              className="px-3 py-1.5 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              {status === "disconnected" ? "Démarrer session" : "Reconnecter"}
            </button>
          )}
          {status === "connected" && (
            <button
              onClick={disconnect}
              className="px-3 py-1.5 text-sm font-medium bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors"
            >
              Arrêter
            </button>
          )}
        </div>
      </div>

      {/* Terminal */}
      <div
        ref={terminalRef}
        className="w-full rounded-lg border border-border overflow-hidden min-h-[450px] bg-[#1a1b26]"
      />
    </div>
  );
}
