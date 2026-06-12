"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  Bot,
  ChevronLeft,
  ChevronRight,
  Clipboard,
  Database,
  FileDown,
  Loader2,
  PanelRightClose,
  PanelRightOpen,
  Rows3,
  SendHorizontal,
  Table2,
  TerminalSquare,
  UserRound,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type ChatResponse = {
  sql: string;
  answer: string;
  rows: Record<string, unknown>[];
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  error?: boolean;
};

type InspectorTab = "table" | "sql";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const formatNumber = new Intl.NumberFormat("en-US");

export default function Home() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Ask a database question. I will generate SQL, run it, and show the result here. The table and query live in the side panel when you need receipts.",
    },
  ]);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<InspectorTab>("table");
  const [panelOpen, setPanelOpen] = useState(true);
  const [copiedSql, setCopiedSql] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const columns = useMemo(() => {
    if (!result?.rows.length) return [];
    return Object.keys(result.rows[0]);
  }, [result]);

  useEffect(() => {
    const marker = messagesEndRef.current;
    if (!marker) return;

    const rect = marker.getBoundingClientRect();
    const isVisible = rect.top >= 0 && rect.bottom <= window.innerHeight;
    if (!isVisible) {
      marker.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages]);

  async function submit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    const pendingId = crypto.randomUUID();

    setMessages((current) => [
      ...current,
      userMessage,
      {
        id: pendingId,
        role: "assistant",
        content: "Running query...",
      },
    ]);
    setQuestion("");
    setLoading(true);
    setActiveTab("table");
    setCopiedSql(false);

    const history = messages
      .filter((m) => m.id !== "welcome" && !m.error && m.content !== "Running query...")
      .slice(-10)
      .map(({ role, content }) => ({ role, content }));

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed, history }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "The backend rejected the request.");
      }

      setResult(payload);
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingId
            ? {
                ...message,
                content: payload.answer || "Query completed, but the answer text came back empty. Very poetic. Not useful.",
              }
            : message,
        ),
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown frontend nonsense occurred.";
      setResult(null);
      setMessages((current) =>
        current.map((item) =>
          item.id === pendingId
            ? {
                ...item,
                content: message,
                error: true,
              }
            : item,
        ),
      );
    } finally {
      setLoading(false);
      window.requestAnimationFrame(() => resizeComposer());
    }
  }

  function resizeComposer() {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }

  async function copySql() {
    if (!result?.sql) return;
    await navigator.clipboard.writeText(result.sql);
    setCopiedSql(true);
    window.setTimeout(() => setCopiedSql(false), 1600);
  }

  function exportCsv() {
    if (!result?.rows.length) return;

    const header = columns.join(",");
    const body = result.rows
      .map((row) =>
        columns
          .map((column) => {
            const value = formatCell(row[column]);
            return `"${value.replace(/"/g, '""')}"`;
          })
          .join(","),
      )
      .join("\n");

    const blob = new Blob([[header, body].join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ragship-results.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="h-screen overflow-hidden bg-app text-foreground">
      <div
        className={cn(
          "grid h-screen overflow-hidden transition-[grid-template-columns] duration-300",
          panelOpen ? "lg:grid-cols-[minmax(0,1fr)_500px]" : "lg:grid-cols-[minmax(0,1fr)_56px]",
        )}
      >
        <section className="flex h-screen min-w-0 flex-col overflow-hidden">
          <header className="shrink-0 flex h-16 items-center justify-between gap-4 border-b border-border bg-panel px-4 lg:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-ink text-white shadow-soft">
                <Database className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <h1 className="truncate text-base font-semibold text-ink">Ragship</h1>
                <p className="truncate text-xs text-muted-foreground">Conversational SQL analyst</p>
              </div>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="lg:hidden"
              onClick={() => setPanelOpen((open) => !open)}
            >
              {panelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
              {panelOpen ? "Hide panel" : "Show panel"}
            </Button>
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6">
            <div className="mx-auto flex max-w-4xl flex-col gap-5">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              <div ref={messagesEndRef} aria-hidden="true" />
            </div>
          </div>

          <div className="shrink-0 border-t border-border bg-app/95 px-4 py-3 backdrop-blur">
            <form ref={formRef} onSubmit={submit} className="mx-auto max-w-4xl">
              <div className="flex items-end gap-2 rounded-[28px] border border-stone-800/10 bg-[#202020] px-4 py-2 shadow-[0_14px_40px_rgba(31,26,23,0.16)]">
                <Textarea
                  ref={textareaRef}
                  value={question}
                  rows={1}
                  onChange={(event) => {
                    setQuestion(event.target.value);
                    window.requestAnimationFrame(() => resizeComposer());
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      formRef.current?.requestSubmit();
                    }
                  }}
                  className="max-h-[180px] min-h-11 flex-1 resize-none overflow-y-auto border-0 bg-transparent px-1 py-2.5 text-[16px] leading-6 text-white shadow-none outline-none placeholder:text-stone-400 focus-visible:ring-0"
                  placeholder="Ask a database question..."
                />
                <Button
                  type="submit"
                  disabled={loading || !question.trim()}
                  size="icon"
                  className="mb-0.5 h-10 w-10 shrink-0 rounded-full bg-white text-ink hover:bg-stone-200 disabled:bg-stone-500 disabled:text-stone-300"
                  aria-label="Send query"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
                </Button>
              </div>
            </form>
          </div>
        </section>

        <aside
          className={cn(
            "min-w-0 border-l border-border bg-panel transition-transform duration-300",
            panelOpen ? "block" : "hidden lg:block",
          )}
        >
          {panelOpen ? (
            <div className="flex h-screen min-w-0 flex-col">
              <div className="flex h-16 items-center justify-between gap-3 border-b border-border px-4">
                <div className="min-w-0">
                  <h2 className="text-sm font-semibold text-ink">Inspector</h2>
                  <p className="truncate text-xs text-muted-foreground">
                    {result ? `${formatNumber.format(result.rows.length)} rows from latest answer` : "No result yet"}
                  </p>
                </div>
                <Button type="button" variant="ghost" size="icon" onClick={() => setPanelOpen(false)} title="Collapse panel">
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>

              <div className="border-b border-border p-3">
                <div className="grid grid-cols-2 rounded-lg bg-stone-100 p-1">
                  <TabButton active={activeTab === "table"} onClick={() => setActiveTab("table")}>
                    <Table2 className="h-3.5 w-3.5" />
                    Table
                  </TabButton>
                  <TabButton active={activeTab === "sql"} onClick={() => setActiveTab("sql")}>
                    <TerminalSquare className="h-3.5 w-3.5" />
                    SQL
                  </TabButton>
                </div>
              </div>

              <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
                <Badge variant="outline" className="border-stone-200 bg-stone-50 text-stone-700">
                  {activeTab === "table" ? "Rows" : "Query"}
                </Badge>
                <div className="flex gap-2">
                  <Button type="button" size="sm" variant="outline" disabled={!result?.rows.length} onClick={exportCsv}>
                    <FileDown className="h-3.5 w-3.5" />
                    CSV
                  </Button>
                  <Button type="button" size="sm" variant="outline" disabled={!result?.sql} onClick={copySql}>
                    <Clipboard className="h-3.5 w-3.5" />
                    {copiedSql ? "Copied" : "Copy SQL"}
                  </Button>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-hidden p-4">
                {activeTab === "table" ? (
                  <ResultsTable rows={result?.rows ?? []} columns={columns} />
                ) : (
                  <SqlBlock sql={result?.sql} />
                )}
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setPanelOpen(true)}
              className="flex h-screen w-full items-start justify-center border-l border-border bg-panel px-2 py-5 text-muted-foreground transition hover:bg-stone-50 hover:text-ink"
              title="Expand inspector"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
          )}
        </aside>
      </div>
    </main>
  );
}

function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "justify-end")}>
      {!isUser && <Avatar error={message.error}>{message.error ? <AlertCircle /> : <Bot />}</Avatar>}
      <div
        className={cn(
          "max-w-[min(760px,calc(100%-3rem))] rounded-2xl px-4 py-3 text-[15px] leading-7 shadow-soft",
          isUser
            ? "bg-ink text-white"
            : message.error
              ? "border border-rose-200 bg-rose-50 text-rose-950"
              : "border border-border bg-panel text-stone-800",
        )}
      >
        <div className={cn("mb-1 text-xs font-semibold", isUser ? "text-white/70" : "text-muted-foreground")}>
          {isUser ? "You" : "Ragship"}
        </div>
        {message.content === "Running query..." ? (
          <span className="inline-flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin text-teal-700" />
            Running query...
          </span>
        ) : (
          <MessageText value={message.content} />
        )}
      </div>
      {isUser && <Avatar>{<UserRound />}</Avatar>}
    </div>
  );
}

function Avatar({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return (
    <div
      className={cn(
        "grid h-9 w-9 shrink-0 place-items-center rounded-lg border bg-white [&>svg]:h-4 [&>svg]:w-4",
        error ? "border-rose-200 text-rose-700" : "border-border text-teal-700",
      )}
    >
      {children}
    </div>
  );
}

function MessageText({ value }: { value: string }) {
  return (
    <div className="space-y-3">
      {stripMarkdown(value)
        .split(/\n{2,}/)
        .map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex h-9 items-center justify-center gap-2 rounded-md text-sm font-medium text-muted-foreground transition",
        active && "bg-white text-ink shadow-soft",
      )}
    >
      {children}
    </button>
  );
}

function ResultsTable({ rows, columns }: { rows: Record<string, unknown>[]; columns: string[] }) {
  if (!rows.length) {
    return (
      <div className="grid h-full min-h-64 place-items-center rounded-lg border border-dashed border-border bg-stone-50 p-6 text-center">
        <div>
          <Rows3 className="mx-auto h-8 w-8 text-stone-400" />
          <p className="mt-3 text-sm font-semibold text-stone-700">No table yet</p>
          <p className="mt-1 text-sm text-muted-foreground">Send a query first.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto rounded-lg border border-border bg-white">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <thead className="sticky top-0 z-10 bg-stone-100 text-[11px] uppercase text-stone-600 shadow-[0_1px_0_hsl(var(--border))]">
          <tr>
            {columns.map((column) => (
              <th key={column} className="whitespace-nowrap px-3 py-3 font-semibold">
                {humanizeColumn(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-b border-stone-100 hover:bg-teal-50/50">
              {columns.map((column) => (
                <td
                  key={column}
                  className={cn(
                    "max-w-[260px] px-3 py-2.5 align-top text-stone-800",
                    typeof row[column] === "number" && "font-medium tabular-nums text-stone-950",
                  )}
                >
                  <span className="line-clamp-3 break-words">{formatCell(row[column])}</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SqlBlock({ sql }: { sql?: string }) {
  return (
    <pre className="h-full min-h-64 overflow-auto rounded-lg bg-[#171717] p-4 text-sm leading-6 text-stone-100 shadow-inner">
      {sql ?? "No SQL yet. Send a query first."}
    </pre>
  );
}

function formatCell(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return value.toLocaleString();
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function stripMarkdown(value: string) {
  return value
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
}

function humanizeColumn(column: string) {
  return column.replace(/_/g, " ");
}
