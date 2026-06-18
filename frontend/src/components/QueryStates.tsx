import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/** Consistent loading indicator for a page that's waiting on a query. */
export function LoadingState({ label = "Computing…" }: { label?: string }) {
  return (
    <div
      className="flex items-center gap-2 py-12 text-muted-foreground"
      role="status"
      aria-live="polite"
    >
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

function humanize(error: unknown): string {
  const msg = error instanceof Error ? error.message : String(error ?? "Unknown error");
  // fetch() rejects with a cryptic TypeError when the API is unreachable.
  if (/failed to fetch|networkerror|load failed/i.test(msg)) {
    return "Couldn't reach the API. Is the backend running on :8000?";
  }
  return msg;
}

/** Friendly, recoverable error card with a Retry affordance. */
export function ErrorState({
  error,
  onRetry,
  title = "Couldn't load this view",
}: {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}) {
  return (
    <Card className="border-bad/40" role="alert">
      <CardContent className="flex flex-col items-start gap-3 p-6">
        <div className="flex items-center gap-2 font-serif text-base font-semibold text-bad">
          <AlertTriangle className="h-4 w-4" aria-hidden />
          {title}
        </div>
        <p className="text-sm text-muted-foreground">{humanize(error)}</p>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden />
            Try again
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
