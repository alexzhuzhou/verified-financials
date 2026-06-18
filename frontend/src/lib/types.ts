// DTO types mirroring the backend pydantic models. Money/ratio fields arrive as
// strings (Decimal) — never parse to float for display. Run `npm run gen:types`
// (with the API up) to regenerate from the OpenAPI schema.

export interface ScenarioInfo {
  id: string;
  label: string;
  description: string;
}

export interface FactRef {
  ref: string;
  value: string;
  source_file: string;
  source_locator: string;
  as_of_date: string;
  version_tag: string | null;
}

export interface Finding {
  check_id: string;
  label: string;
  status: "pass" | "fail";
  severity: string;
  left: FactRef;
  right: FactRef;
  delta: string;
  tolerance_abs: string;
  message: string;
}

export interface VerificationReport {
  run_id: string;
  as_of_date: string;
  findings: Finding[];
  passed: number;
  failed: number;
}

export interface IneligibleContribution {
  entity: string;
  amount: string;
  fact_id: string;
  note: string;
}

export interface IneligibleLine {
  rule_id: string;
  label: string;
  citation: string;
  amount: string;
  detail: IneligibleContribution[];
}

export interface ConcentrationLine {
  customer: string;
  balance_in_base: string;
  cap_amount: string;
  excess_excluded: string;
  pct_of_base: string;
  pct_of_gross: string;
}

export interface NolvLine {
  category: string;
  cost: string;
  nolv_ratio: string;
  nolv_value: string;
}

export interface AssetClassResult {
  asset_class: string;
  gross: string;
  ineligibles: IneligibleLine[];
  concentration: ConcentrationLine[];
  total_ineligible: string;
  eligible: string;
  valuation_basis: string;
  nolv_detail: NolvLine[];
  eligible_nolv_value: string | null;
  advance_rate: string;
  availability: string;
}

export interface ReserveDetail {
  id: string;
  label: string;
  type: string;
  amount: string;
  citation: string;
}

export interface BorrowingBaseCertificate {
  run_id: string;
  as_of_date: string;
  borrower: string;
  lender: string;
  agent: string;
  facility_name: string;
  agreement_reference: string;
  certificate_no: number;
  config_hash: string;
  accounts_receivable: AssetClassResult;
  inventory: AssetClassResult;
  gross_availability: string;
  reserves_total: string;
  reserve_detail: ReserveDetail[];
  borrowing_base: string;
  commitment: string;
  binding_constraint: string;
  suppressed_availability: string;
  outstanding: string;
  lc_exposure: string;
  excess_availability: string;
}

export interface FccrComponent {
  name: string;
  value: string;
  fact_id: string | null;
  side: "numerator" | "denominator";
  role: "add" | "subtract";
}

export interface QuarterPoint {
  quarter: string;
  fccr: string;
}

export interface FccrReport {
  run_id: string;
  as_of_date: string;
  basis: string;
  components: FccrComponent[];
  numerator: string;
  denominator: string;
  fccr: string;
  covenant: string;
  in_compliance: boolean;
  headroom_abs: string;
  headroom_pct: string;
  ebitda_cushion: string;
  springing_enabled: boolean;
  covenant_active: boolean;
  springing_trigger: string | null;
  excess_availability: string | null;
  equity_cure_enabled: boolean;
  equity_cure_needed: string;
  cures_used: number;
  cures_remaining_year: number | null;
  cures_remaining_lifetime: number | null;
  trend: QuarterPoint[];
  consecutive_declines: number;
  early_warning: boolean;
  warning_reasons: string[];
}

export interface ComputeResponse {
  run_id: string;
  summary: Record<string, unknown>;
  verification: VerificationReport;
  borrowing_base: BorrowingBaseCertificate;
  fccr: FccrReport;
}

export interface Fact {
  id: string;
  dataset: string;
  entity: string | null;
  metric: string;
  value: string;
  unit: string;
  attributes: Record<string, unknown>;
  provenance: {
    source_file: string;
    source_locator: string;
    as_of_date: string;
    loaded_at: string;
    version_tag: string | null;
  };
}

export interface SensitivityLever {
  id: string;
  label: string;
  baseline_excess: string;
  new_excess: string;
  delta_excess: string;
  baseline_bb: string;
  new_bb: string;
  delta_bb: string;
  baseline_fccr: string;
  new_fccr: string;
  delta_fccr: string;
}

export interface SensitivityResponse {
  levers: SensitivityLever[];
}

export interface BriefingResponse {
  briefing: string;
  generated_by: "ai" | "fallback";
}

export interface GoalSeekResult {
  lever: string;
  label: string;
  target: string;
  reachable: boolean;
  solved_value: string;
  achieved_excess: string;
  baseline_value: string;
  baseline_excess: string;
  message: string;
}

// A loose shape for the resolved config (the editable loan agreement).
export type AppConfig = Record<string, any>;
export type Overrides = Record<string, any>;
