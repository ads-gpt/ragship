"use client";

import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Clock3,
  Database,
  Loader2,
  MessageSquareText,
  Play,
  Rows3,
  Sparkles,
  Table2,
  TerminalSquare,
  UserRound,
} from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type ChatResponse = {
  sql: string;
  answer: string;
  rows: Record<string, unknown>[];
};

type InspectorTab = "table" | "sql";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const examples = [
  "Top 10 customers by revenue",
  "Which products have the highest sales quantity?",
  "Show sales by territory",
];

export default function Home() {
  const [question, setQuestion] = useState(examples[0]);
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(null);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [durationMs, setDurationMs] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<InspectorTab>("table");

  const columns = useMemo(() => {
    if (!result?.rows.length) return [];
    return Object.keys(result.rows[0]);
  }, [result]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    const startedAt = performance.now();
    setLoading(true);
    setError(null);
    setSubmittedQuestion(trimmed);
    setActiveTab("table");

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "The backend rejected the request.");
      }

      setResult(payload);
      setDurationMs(Math.round(performance.now() - startedAt));
    } catch (err) {
      setResult(null);
      setDurationMs(null);
      setError(err instanceof Error ? err.message : "Unknown frontend nonsense occurred.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f5f7fb] text-foreground">
      <div className="mx-auto grid min-h-screen max-w-[1500px] grid-cols-1 gap-0 lg:grid-cols-[390px_1fr]">
        <aside className="border-b border-border bg-white px-5 py-5 lg:border-b-0 lg:border-r">
          <div className="flex h-full flex-col gap-5">
            <header className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
                    <Database className="h-5 w-5" />
                  </div>
                  <div>
                    <h1 className="text-lg font-semibold tracking-normal text-ink">Ragship</h1>
                    <p className="text-xs text-muted-foreground">AdventureWorks SQL analyst</p>
                  </div>
                </div>
                <Badge variant="outline" className="gap-1.5 border-emerald-200 bg-emerald-50 text-emerald-700">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  API
                </Badge>
              </div>
              <div className="rounded-md border border-border bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                Backend <span className="font-medium text-foreground">{API_URL}</span>
              </div>
            </header>

            <form onSubmit={submit} className="space-y-3">
              <div className="space-y-2">
                <label htmlFor="question" className="text-sm font-medium text-foreground">
                  Ask a database question
                </label>
                <Textarea
                  id="question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  className="min-h-40 resize-none bg-white text-[15px]"
                  placeholder="Ask for revenue, products, customers, territories, or other AdventureWorks pain."
                />
              </div>
              <Button type="submit" disabled={loading || !question.trim()} className="w-full">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Run query
              </Button>
            </form>

            <section className="space-y-2">
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Useful prompts</div>
              <div className="grid gap-2">
                {examples.map((example) => (
                  <Button
                    key={example}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-auto justify-start whitespace-normal py-2 text-left"
                    onClick={() => setQuestion(example)}
                  >
                    <Sparkles className="h-3.5 w-3.5 shrink-0 text-primary" />
                    {example}
                  </Button>
                ))}
              </div>
            </section>

            <div className="mt-auto rounded-md border border-border bg-[#fbfcff] p-3 text-xs leading-5 text-muted-foreground">
              Ask in plain English. Ragship generates SQL, executes it, and keeps the query visible so the magic trick has receipts.
            </div>
          </div>
        </aside>

        <section className="flex min-w-0 flex-col">
          <header className="flex flex-col gap-3 border-b border-border bg-white px-5 py-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <MessageSquareText className="h-4 w-4 text-primary" />
                Query session
              </div>
              <h2 className="mt-1 text-2xl font-semibold tracking-normal text-ink">Ask, answer, inspect.</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              <Metric label="Rows" value={result ? String(result.rows.length) : "-"} />
              <Metric label="Latency" value={durationMs ? `${(durationMs / 1000).toFixed(1)}s` : "-"} icon={<Clock3 />} />
            </div>
          </header>

          <div className="grid flex-1 gap-5 p-5 xl:grid-cols-[minmax(0,1fr)_560px]">
            <div className="flex min-w-0 flex-col gap-4">
              <ChatBubble
                tone="user"
                icon={<UserRound className="h-4 w-4" />}
                title="You"
                body={submittedQuestion ?? "Ask a question from the panel. The database is not going to interrogate itself, regrettably."}
              />

              <Card className="overflow-hidden">
                <CardHeader className="border-b border-border bg-white">
                  <div className="flex items-center justify-between gap-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                      </span>
                      Ragship answer
                    </CardTitle>
                    {result && <Badge variant="secondary">{result.rows.length} rows</Badge>}
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  {error ? (
                    <div className="m-5 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
                      <div className="mb-1 flex items-center gap-2 font-semibold">
                        <AlertCircle className="h-4 w-4" />
                        Request failed
                      </div>
                      <p>{error}</p>
                    </div>
                  ) : (
                    <div className="space-y-5 p-5">
                      <AnswerView answer={result?.answer} loading={loading} />
                      {result && (
                        <div className="flex flex-wrap items-center gap-2 border-t border-border pt-4">
                          <Button type="button" variant="outline" size="sm" onClick={() => setActiveTab("table")}>
                            <Rows3 className="h-3.5 w-3.5" />
                            View rows
                          </Button>
                          <Button type="button" variant="outline" size="sm" onClick={() => setActiveTab("sql")}>
                            <TerminalSquare className="h-3.5 w-3.5" />
                            Inspect SQL
                          </Button>
                          <span className="text-xs text-muted-foreground">
                            Answer first, receipts one click away. Novel concept, apparently.
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            <Card className="min-w-0 overflow-hidden">
              <CardHeader className="border-b border-border bg-white pb-3">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-base">Inspector</CardTitle>
                  <Badge variant="outline">SQL transparent</Badge>
                </div>
                <div className="mt-3 grid grid-cols-2 rounded-md bg-muted p-1">
                  <TabButton active={activeTab === "table"} onClick={() => setActiveTab("table")}>
                    Rows
                  </TabButton>
                  <TabButton active={activeTab === "sql"} onClick={() => setActiveTab("sql")}>
                    SQL
                  </TabButton>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {activeTab === "table" && (
                  <InspectorPane icon={<Table2 className="h-4 w-4" />} title="Returned rows">
                    <ResultsTable rows={result?.rows ?? []} columns={columns} />
                  </InspectorPane>
                )}

                {activeTab === "sql" && (
                  <InspectorPane icon={<TerminalSquare className="h-4 w-4" />} title="Generated SQL">
                    <pre className="max-h-[620px] min-h-52 overflow-auto rounded-md bg-slate-950 p-4 text-sm leading-6 text-slate-100">
                      {result?.sql ?? "No SQL yet. Ask a question first; databases rarely volunteer."}
                    </pre>
                  </InspectorPane>
                )}
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-[#fbfcff] px-3 text-sm">
      {icon && <span className="text-muted-foreground [&>svg]:h-4 [&>svg]:w-4">{icon}</span>}
      <span className="text-muted-foreground">{label}</span>
      <span className="font-semibold text-foreground">{value}</span>
    </div>
  );
}

function ChatBubble({
  icon,
  title,
  body,
  tone,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  tone: "user" | "assistant";
}) {
  return (
    <div className={cn("flex gap-3", tone === "user" && "justify-end")}>
      {tone === "assistant" && <Avatar>{icon}</Avatar>}
      <div
        className={cn(
          "max-w-3xl rounded-lg border px-4 py-3 shadow-sm",
          tone === "user" ? "border-primary/20 bg-primary text-primary-foreground" : "border-border bg-white",
        )}
      >
        <div className={cn("mb-1 text-xs font-medium", tone === "user" ? "text-white/80" : "text-muted-foreground")}>
          {title}
        </div>
        <p className="text-sm leading-6">{body}</p>
      </div>
      {tone === "user" && <Avatar>{icon}</Avatar>}
    </div>
  );
}

function Avatar({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-white text-primary">
      {children}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "h-8 rounded text-sm font-medium text-muted-foreground transition",
        active && "bg-white text-foreground shadow-sm",
      )}
    >
      {children}
    </button>
  );
}

function InspectorPane({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3 p-5">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <span className="text-primary">{icon}</span>
        {title}
      </div>
      {children}
    </section>
  );
}

function ResultsTable({ rows, columns }: { rows: Record<string, unknown>[]; columns: string[] }) {
  if (!rows.length) {
    return (
      <div className="rounded-md border border-dashed border-border bg-[#fbfcff] p-4 text-sm text-muted-foreground">
        No rows yet.
      </div>
    );
  }

  return (
    <div className="max-h-[620px] overflow-auto rounded-md border border-border bg-white">
      <table className="w-full min-w-[720px] border-collapse text-left text-sm">
        <thead className="sticky top-0 bg-muted text-xs uppercase text-muted-foreground">
          <tr>
            {columns.map((column) => (
              <th key={column} className="border-b border-border px-3 py-2 font-semibold">
                {humanizeColumn(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="odd:bg-white even:bg-[#fbfcff]">
              {columns.map((column) => (
                <td key={column} className="border-b border-border px-3 py-2 align-top text-slate-800">
                  {formatCell(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return value.toLocaleString();
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function AnswerView({
  answer,
  loading,
  compact = false,
}: {
  answer?: string;
  loading?: boolean;
  compact?: boolean;
}) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        Generating SQL, running it, and attempting not to embarrass itself.
      </div>
    );
  }

  if (!answer) {
    return <p className="text-sm text-muted-foreground">No answer yet. Which is refreshingly honest.</p>;
  }

  const normalized = stripMarkdown(answer);
  const numberedItems = extractNumberedItems(normalized);

  if (numberedItems.length) {
    const intro = normalized.slice(0, numberedItems[0].index).replace(/:\s*$/, "").trim();
    return (
      <div className={cn("space-y-4", compact && "space-y-3")}>
        {intro && <p className={cn("leading-7 text-foreground", compact && "text-sm leading-6")}>{intro}.</p>}
        <ol className="grid gap-2">
          {numberedItems.map((item) => (
            <li
              key={`${item.rank}-${item.label}`}
              className="grid grid-cols-[2rem_1fr] items-start gap-2 rounded-md border border-border bg-white px-3 py-2"
            >
              <span className="flex h-6 w-6 items-center justify-center rounded bg-primary/10 text-xs font-semibold text-primary">
                {item.rank}
              </span>
              <span className="min-w-0">
                <span className="font-medium text-foreground">{item.label}</span>
                {item.value && <span className="ml-1 text-muted-foreground">{item.value}</span>}
              </span>
            </li>
          ))}
        </ol>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3 text-base leading-7 text-foreground", compact && "text-sm leading-6")}>
      {normalized.split(/\n{2,}/).map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
    </div>
  );
}

function stripMarkdown(value: string) {
  return value
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
}

function extractNumberedItems(value: string) {
  const matches = [
    ...value.matchAll(
      /(?:^|\n|\s)(\d+)\.\s+(.+?)(?:\s+with\s+|:\s+)(\$?[\d,.]+(?:\.\d+)?|[^\n]+?)(?=\s+\d+\.|\n\d+\.|$)/g,
    ),
  ];
  return matches.map((match) => ({
    rank: match[1],
    label: match[2].trim(),
    value: match[3].trim(),
    index: match.index ?? 0,
  }));
}

function humanizeColumn(column: string) {
  return column.replace(/_/g, " ");
}
