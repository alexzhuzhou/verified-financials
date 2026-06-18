import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

function sseResponse(frames: string[]): Response {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      const enc = new TextEncoder();
      for (const f of frames) controller.enqueue(enc.encode(f));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } });
}

afterEach(() => vi.unstubAllGlobals());

describe("askStream", () => {
  it("parses SSE deltas in order and fires onDone at [DONE]", async () => {
    const frames = [
      'data: {"delta": "Excess availability "}\n\n',
      'data: {"delta": "is $5.3M."}\n\n',
      "data: [DONE]\n\n",
    ];
    vi.stubGlobal("fetch", vi.fn(async () => sseResponse(frames)));

    const chunks: string[] = [];
    let done = false;
    await api.askStream(
      { scenario: "baseline", configOverrides: {}, question: "how much room?" },
      (d) => chunks.push(d),
      () => {
        done = true;
      },
    );

    expect(chunks.join("")).toBe("Excess availability is $5.3M.");
    expect(done).toBe(true);
  });

  it("handles a delta split across two reads (partial frame buffering)", async () => {
    const frames = ['data: {"delta": "par', 'tial"}\n\n', "data: [DONE]\n\n"];
    vi.stubGlobal("fetch", vi.fn(async () => sseResponse(frames)));

    const chunks: string[] = [];
    await api.askStream(
      { scenario: "baseline", configOverrides: {}, question: "x" },
      (d) => chunks.push(d),
    );

    expect(chunks.join("")).toBe("partial");
  });
});

describe("error handling", () => {
  it("surfaces the server's `detail` message instead of a bare status code", async () => {
    const detail = "inventory.csv row 5, column 'value': expected a number, got 'abc'";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail }), { status: 422 })),
    );
    await expect(api.compute({ scenario: "baseline", configOverrides: {} })).rejects.toThrow(detail);
  });

  it("joins a `detail.errors` array into one message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: { errors: ["a.csv: not found", "b.csv: bad"] } }), {
            status: 400,
          }),
      ),
    );
    await expect(api.compute({ scenario: "baseline", configOverrides: {} })).rejects.toThrow(
      "a.csv: not found; b.csv: bad",
    );
  });

  it("falls back to the status line when there is no JSON body", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 500 })));
    await expect(api.compute({ scenario: "baseline", configOverrides: {} })).rejects.toThrow(
      "/compute → 500",
    );
  });
});

describe("certificateHtml", () => {
  it("returns the rendered HTML as text", async () => {
    const html = "<!DOCTYPE html><html><body>Borrowing Base Certificate</body></html>";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(html, { status: 200, headers: { "content-type": "text/html" } })),
    );
    const out = await api.certificateHtml({ scenario: "baseline", configOverrides: {} });
    expect(out).toContain("Borrowing Base Certificate");
  });

  it("throws the server detail on error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "boom" }), { status: 422 })),
    );
    await expect(api.certificateHtml({ scenario: "baseline", configOverrides: {} })).rejects.toThrow(
      "boom",
    );
  });
});
