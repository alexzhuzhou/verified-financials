import { Send, Sparkles } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

import { ErrorState, LoadingState } from "@/components/QueryStates";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useBriefing } from "@/hooks/queries";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";

const MD = "text-sm leading-relaxed [&_h2]:font-serif [&_h2]:text-lg [&_h2]:mt-1 [&_h3]:font-serif [&_h3]:font-semibold [&_h3]:mt-4 [&_h3]:mb-1 [&_p]:mt-2 [&_ul]:mt-2 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:mt-1 [&_strong]:font-semibold [&_em]:text-muted-foreground";

const SUGGESTED = [
  "Why is excess availability so low?",
  "How close are we to a covenant breach, and what would fix it?",
  "Which reconciliation exception is most concerning?",
];

export function BriefingPage() {
  const { data, isLoading, isError, error, refetch } = useBriefing();
  const dataSource = useAppStore((s) => s.dataSource);
  const overrides = useAppStore((s) => s.overrides);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);

  const sourceArgs = dataSource.kind === "upload" ? { uploadId: dataSource.uploadId } : { scenario: dataSource.scenario };

  const ask = async (q: string) => {
    const query = q.trim();
    if (!query || streaming) return;
    setQuestion(query);
    setAnswer("");
    setAskError(null);
    setStreaming(true);
    try {
      await api.askStream(
        { ...sourceArgs, configOverrides: overrides, question: query },
        (delta) => setAnswer((a) => a + delta),
        () => setStreaming(false),
      );
    } catch (e) {
      setAskError(e instanceof Error ? e.message : String(e));
      setStreaming(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl">
          <Sparkles className="h-5 w-5 text-primary" /> Advisor Briefing
        </h1>
        <p className="text-sm text-muted-foreground">
          A plain-English read of the live numbers — and ask anything about them.
        </p>
      </div>

      {/* Executive briefing */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Executive briefing</CardTitle>
            {data && (
              <Badge variant={data.generated_by === "ai" ? "default" : "outline"}>
                {data.generated_by === "ai" ? "AI-generated" : "Rule-generated"}
              </Badge>
            )}
          </div>
          <CardDescription>Synthesized from the current scenario and any what-if edits.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && !data ? (
            <LoadingState label="Writing the briefing…" />
          ) : isError || !data ? (
            <ErrorState error={error} onRetry={() => refetch()} title="Couldn't write the briefing" />
          ) : (
            <div className={MD}>
              <ReactMarkdown>{data.briefing}</ReactMarkdown>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Ask the data */}
      <Card>
        <CardHeader>
          <CardTitle>Ask the data</CardTitle>
          <CardDescription>Answered only from the computed figures — it won't invent numbers.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void ask(question);
            }}
          >
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. What's the fastest way to free up $5M of availability?"
            />
            <Button type="submit" disabled={streaming || !question.trim()}>
              <Send className="h-4 w-4" />
              {streaming ? "…" : "Ask"}
            </Button>
          </form>

          <div className="flex flex-wrap gap-2">
            {SUGGESTED.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => void ask(s)}
                disabled={streaming}
                className="rounded-full border bg-muted/40 px-3 py-1 text-xs text-muted-foreground hover:bg-accent disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>

          {askError && <p className="text-sm text-bad">{askError}</p>}
          {answer && (
            <div className="rounded-md border bg-muted/30 p-4">
              <div className={MD}>
                <ReactMarkdown>{answer}</ReactMarkdown>
              </div>
              {streaming && <span className="ml-0.5 inline-block animate-pulse">▌</span>}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
