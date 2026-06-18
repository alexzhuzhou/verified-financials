// Backend money/ratio fields are Decimal strings. Format for display only.

const USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const USD0 = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export function money(value: string | number | null | undefined, compact = false): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(n)) return String(value);
  return compact ? USD0.format(n) : USD.format(n);
}

export function ratio(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  return Number.isNaN(n) ? String(value) : `${n.toFixed(2)}x`;
}

export function pct(value: string | number | null | undefined, dp = 1): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  return Number.isNaN(n) ? String(value) : `${(n * 100).toFixed(dp)}%`;
}

export function titleize(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
