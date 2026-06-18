import { CheckCircle2, Download, Upload } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";

const DATASETS = [
  { file: "ar_aging.csv", label: "A/R Aging" },
  { file: "inventory.csv", label: "Inventory" },
  { file: "trial_balance.csv", label: "Trial Balance" },
  { file: "balance_sheet.csv", label: "Balance Sheet" },
  { file: "financials_ttm.csv", label: "Financials (TTM)" },
  { file: "financials_2025_refreshed.csv", label: "Financials (refreshed)" },
];

export function SetupPage() {
  const navigate = useNavigate();
  const setUpload = useAppStore((s) => s.setUpload);
  const [files, setFiles] = useState<Record<string, File>>({});
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const allSelected = DATASETS.every((d) => files[d.file]);

  const pick = (name: string, f: File | null) => {
    setFiles((prev) => {
      const next = { ...prev };
      if (f) next[name] = f;
      else delete next[name];
      return next;
    });
    setErrors([]);
  };

  const submit = async () => {
    setBusy(true);
    setErrors([]);
    const res = await api.uploadFiles(files);
    setBusy(false);
    if (res.ok) {
      setUpload(res.uploadId);
      navigate("/app");
    } else {
      setErrors(res.errors);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl">Upload your data</h1>
        <p className="text-sm text-muted-foreground">
          Provide the six datasets as CSVs. Each must match the template columns exactly — download a
          template to see the required format. Then set the facility terms and rules in the panel on the right.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Datasets</CardTitle>
          <CardDescription>All six files are required.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {DATASETS.map((d) => (
            <div key={d.file} className="flex items-center gap-3 border-b pb-3 last:border-b-0 last:pb-0">
              <div className="w-44 shrink-0">
                <div className="text-sm font-medium">{d.label}</div>
                <div className="text-xs text-muted-foreground">{d.file}</div>
              </div>
              <a
                href={api.templateUrl(d.file)}
                download={d.file}
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                <Download className="h-3.5 w-3.5" /> template
              </a>
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => pick(d.file, e.target.files?.[0] ?? null)}
                className="flex-1 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-accent"
              />
              {files[d.file] && <CheckCircle2 className="h-4 w-4 shrink-0 text-ok" />}
            </div>
          ))}
        </CardContent>
      </Card>

      {errors.length > 0 && (
        <Card className="border-bad/40 bg-bad-bg/40">
          <CardHeader>
            <CardTitle className="text-base text-bad">Upload rejected</CardTitle>
            <CardDescription>Fix these and try again:</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 text-sm text-bad">
              {errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Button onClick={submit} disabled={!allSelected || busy}>
        <Upload className="h-4 w-4" />
        {busy ? "Uploading…" : "Use this data"}
      </Button>
    </div>
  );
}
