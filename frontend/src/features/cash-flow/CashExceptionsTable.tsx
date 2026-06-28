import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { money } from "@/lib/format";
import type { CashFlowException } from "@/lib/types";

export function CashExceptionsTable({ exceptions }: { exceptions: CashFlowException[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-serif text-base">Exceptions register</CardTitle>
        <CardDescription>
          Ledger rows needing a human decision before the forecast can fully trust them.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {exceptions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No open exceptions — the ledger is clean.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event</TableHead>
                <TableHead>Party</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Suggested action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {exceptions.map((e) => (
                <TableRow key={e.row_id}>
                  <TableCell className="text-xs">{e.row_id} · {e.type}</TableCell>
                  <TableCell className="text-xs">{e.party}</TableCell>
                  <TableCell className="text-right tnum">{money(e.amount, true)}</TableCell>
                  <TableCell><Badge variant="warn">{e.reason_code}</Badge></TableCell>
                  <TableCell className="text-xs text-muted-foreground">{e.suggested_action}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
