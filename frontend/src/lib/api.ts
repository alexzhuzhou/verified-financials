import type {
  AppConfig,
  BriefingResponse,
  ComputeResponse,
  Fact,
  GoalSeekResult,
  Overrides,
  ScenarioInfo,
  SensitivityResponse,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

/** Build a friendly Error from a failed response, preferring the server's `detail`. */
async function errorFor(res: Response, method: string, path: string): Promise<Error> {
  let detail: unknown;
  try {
    detail = (await res.json())?.detail;
  } catch {
    /* non-JSON body — fall through to the status line */
  }
  if (typeof detail === "string") return new Error(detail);
  if (detail && typeof detail === "object" && Array.isArray((detail as { errors?: unknown }).errors)) {
    return new Error((detail as { errors: string[] }).errors.join("; "));
  }
  if (Array.isArray(detail)) {
    // FastAPI request-validation error shape: [{ msg, loc, ... }]
    return new Error(detail.map((d) => (d as { msg?: string })?.msg ?? "invalid input").join("; "));
  }
  return new Error(`${method} ${path} → ${res.status}`);
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw await errorFor(res, "GET", path);
  return res.json() as Promise<T>;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await errorFor(res, "POST", path);
  return res.json() as Promise<T>;
}

export interface ComputeArgs {
  scenario?: string;
  uploadId?: string;
  configOverrides: Overrides;
}

export type UploadResult =
  | { ok: true; uploadId: string; files: string[] }
  | { ok: false; errors: string[] };

export const api = {
  scenarios: () => getJSON<ScenarioInfo[]>("/scenarios"),

  config: (scenario: string) => getJSON<AppConfig>(`/config?scenario=${scenario}`),

  compute: (args: ComputeArgs) =>
    postJSON<ComputeResponse>("/compute", {
      scenario: args.scenario ?? "baseline",
      upload_id: args.uploadId ?? null,
      config_overrides: args.configOverrides,
    }),

  /** The bank-ready borrowing-base certificate as standalone, print-styled HTML. */
  async certificateHtml(args: ComputeArgs): Promise<string> {
    const res = await fetch(`${BASE}/compute/certificate.html`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        scenario: args.scenario ?? "baseline",
        upload_id: args.uploadId ?? null,
        config_overrides: args.configOverrides,
      }),
    });
    if (!res.ok) throw await errorFor(res, "POST", "/compute/certificate.html");
    return res.text();
  },

  sensitivity: (args: ComputeArgs) =>
    postJSON<SensitivityResponse>("/sensitivity", {
      scenario: args.scenario ?? "baseline",
      upload_id: args.uploadId ?? null,
      config_overrides: args.configOverrides,
    }),

  goalSeek: (args: {
    scenario?: string;
    uploadId?: string;
    configOverrides: Overrides;
    lever: string;
    targetValue: string;
  }) =>
    postJSON<GoalSeekResult>("/goal-seek", {
      scenario: args.scenario ?? "baseline",
      upload_id: args.uploadId ?? null,
      config_overrides: args.configOverrides,
      lever: args.lever,
      target_value: args.targetValue,
    }),

  facts: (params: {
    scenario?: string;
    uploadId?: string;
    dataset?: string;
    metric?: string;
    entity?: string;
  }) => {
    const q = new URLSearchParams();
    if (params.uploadId) q.set("upload_id", params.uploadId);
    else q.set("scenario", params.scenario ?? "baseline");
    if (params.dataset) q.set("dataset", params.dataset);
    if (params.metric) q.set("metric", params.metric);
    if (params.entity) q.set("entity", params.entity);
    return getJSON<Fact[]>(`/facts?${q.toString()}`);
  },

  briefing: (args: ComputeArgs) =>
    postJSON<BriefingResponse>("/briefing", {
      scenario: args.scenario ?? "baseline",
      upload_id: args.uploadId ?? null,
      config_overrides: args.configOverrides,
    }),

  /** Stream an answer to a question (SSE). Calls onDelta per chunk, onDone at the end. */
  async askStream(
    args: ComputeArgs & { question: string },
    onDelta: (text: string) => void,
    onDone?: () => void,
  ): Promise<void> {
    const res = await fetch(`${BASE}/ask`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        scenario: args.scenario ?? "baseline",
        upload_id: args.uploadId ?? null,
        config_overrides: args.configOverrides,
        question: args.question,
      }),
    });
    if (!res.ok || !res.body) throw new Error(`POST /ask → ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? ""; // keep the trailing partial frame
      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith("data:")) continue;
        const data = line.slice(5).trim();
        if (data === "[DONE]") {
          onDone?.();
          return;
        }
        try {
          const parsed = JSON.parse(data) as { delta?: string };
          if (parsed.delta) onDelta(parsed.delta);
        } catch {
          /* ignore a malformed/partial frame */
        }
      }
    }
    onDone?.();
  },

  templateUrl: (name: string) => `${BASE}/templates/${name}`,

  async uploadFiles(files: Record<string, File>): Promise<UploadResult> {
    const fd = new FormData();
    for (const [name, file] of Object.entries(files)) fd.append("files", file, name);
    const res = await fetch(`${BASE}/uploads`, { method: "POST", body: fd });
    if (res.ok) {
      const body = await res.json();
      return { ok: true, uploadId: body.upload_id, files: body.files };
    }
    let errors = [`Upload failed (HTTP ${res.status})`];
    try {
      const body = await res.json();
      if (body?.detail?.errors) errors = body.detail.errors;
      else if (typeof body?.detail === "string") errors = [body.detail];
    } catch {
      /* keep default */
    }
    return { ok: false, errors };
  },
};
