import { AlertTriangle, RefreshCw } from "lucide-react";
import { useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/** Last-resort boundary for a render-time crash — keeps the demo off a white screen. */
export function RouteError() {
  const error = useRouteError();
  const message =
    error instanceof Error
      ? error.message
      : "An unexpected error occurred while rendering this page.";
  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <Card className="max-w-md border-bad/40" role="alert">
        <CardContent className="flex flex-col items-start gap-3 p-6">
          <div className="flex items-center gap-2 font-serif text-lg font-semibold text-bad">
            <AlertTriangle className="h-5 w-5" aria-hidden />
            Something went wrong
          </div>
          <p className="text-sm text-muted-foreground">{message}</p>
          <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden />
            Reload
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
