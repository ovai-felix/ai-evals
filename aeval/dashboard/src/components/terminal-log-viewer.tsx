"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { LogEntry } from "@/lib/types";
import { getRunLogs } from "@/lib/api";

interface TerminalLogViewerProps {
  runId: string;
  runStatus: string;
}

function colorize(message: string): React.ReactNode {
  // Color-code known patterns
  if (/\[aeval\]/i.test(message)) {
    return <span className="text-accent">{message}</span>;
  }
  if (/\[PASS\]/i.test(message)) {
    return <span className="text-success">{message}</span>;
  }
  if (/\[FAIL\]/i.test(message) || /error/i.test(message)) {
    return <span className="text-danger">{message}</span>;
  }
  if (/\[judge\]/i.test(message)) {
    return <span className="text-purple-400">{message}</span>;
  }
  if (/warn/i.test(message)) {
    return <span className="text-yellow-400">{message}</span>;
  }
  return message;
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}

export function TerminalLogViewer({ runId, runStatus }: TerminalLogViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [nextAfter, setNextAfter] = useState(0);
  const [isActive, setIsActive] = useState(
    runStatus === "pending" || runStatus === "running",
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);
  const router = useRouter();

  const fetchLogs = useCallback(async () => {
    try {
      const res = await getRunLogs(runId, nextAfter);
      if (res.logs.length > 0) {
        setLogs((prev) => [...prev, ...res.logs]);
        setNextAfter(res.next_after);
      }
      const active = res.status === "pending" || res.status === "running";
      if (isActive && !active) {
        // Run just finished — refresh the page so server components re-render
        // with final score, status, and task results
        setTimeout(() => router.refresh(), 500);
      }
      setIsActive(active);
    } catch {
      // Silently ignore fetch errors during polling
    }
  }, [runId, nextAfter, isActive, router]);

  // Initial fetch
  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Poll every 2s while active
  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, [isActive, fetchLogs]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  // Detect user scrolling up to disable auto-scroll
  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    autoScrollRef.current = atBottom;
  }, []);

  if (logs.length === 0 && !isActive) {
    return null;
  }

  return (
    <div className="rounded border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#161b22] border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-secondary">
            Terminal Output
          </span>
          {isActive && (
            <span className="flex items-center gap-1.5 text-xs text-text-secondary">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
              </span>
              Live
            </span>
          )}
        </div>
        <span className="text-xs text-text-secondary">
          {logs.length} line{logs.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Log output */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="bg-[#0d1117] p-3 overflow-y-auto font-mono text-xs leading-5 max-h-96"
      >
        {logs.length === 0 && isActive && (
          <div className="text-text-secondary italic">
            Waiting for output...
          </div>
        )}
        {logs.map((log) => (
          <div key={log.seq} className="flex gap-2 hover:bg-white/5">
            <span className="text-text-secondary shrink-0 select-none">
              {formatTimestamp(log.timestamp)}
            </span>
            <span className="whitespace-pre-wrap break-all">
              {colorize(log.message)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
