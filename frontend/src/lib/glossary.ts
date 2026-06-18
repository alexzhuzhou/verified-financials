/**
 * Plain-English definitions for finance / asset-based-lending terms used across
 * the app. Keys are matched case-insensitively by the <Term> component, so a key
 * like "FCCR" will also resolve "fccr". Definitions are written for readers with
 * no finance background — each is a single, self-contained sentence.
 */
export const GLOSSARY: Record<string, string> = {
  FCCR:
    "Fixed Charge Coverage Ratio — a measure of how comfortably a company's earnings cover its required fixed payments (like interest, debt repayments, and leases); higher is safer, and lenders usually require it to stay above 1.0x.",
  EBITDA:
    "Earnings Before Interest, Taxes, Depreciation, and Amortization — a rough proxy for the cash a business generates from its core operations before financing and accounting effects.",
  "borrowing base":
    "The maximum amount a lender will let a company borrow at any moment, calculated from the value of approved collateral such as receivables and inventory.",
  "advance rate":
    "The percentage of an asset's value a lender is willing to lend against — for example, an 85% advance rate means $0.85 of borrowing for every $1.00 of eligible collateral.",
  eligible:
    "Collateral that meets the lender's rules and therefore counts toward how much the company can borrow.",
  ineligible:
    "Collateral the lender excludes from the borrowing base — such as overdue, disputed, or related-party items — because it is considered too risky to lend against.",
  "concentration cap":
    "A limit on how much of the borrowing base can come from a single customer or category, so the loan isn't overly dependent on one source.",
  NOLV:
    "Net Orderly Liquidation Value — the estimated cash a lender could recover by selling inventory in an organized sale, after the costs of selling it.",
  reserves:
    "Amounts the lender subtracts from the borrowing base to set aside a cushion for known or anticipated risks, reducing how much can be borrowed.",
  "excess availability":
    "The unused borrowing capacity that remains after subtracting what's already borrowed from the borrowing base — essentially the spare room left to draw on.",
  covenant:
    "A promise written into the loan agreement that the borrower will (or won't) do certain things, such as keeping a financial ratio above a set level.",
  headroom:
    "The safety margin between a current value and the limit a covenant allows — more headroom means less risk of breaching the agreement.",
  "equity cure":
    "A right that lets the owners inject new cash into the business to fix a covenant breach, effectively curing the default with fresh equity.",
  "springing covenant":
    "A covenant that only becomes active ('springs' into effect) once a specific trigger is met, such as borrowing rising above a certain threshold.",
  revolver:
    "A revolving line of credit the company can borrow from, repay, and borrow against again, much like a corporate credit card with a set limit.",
  commitment:
    "The total amount of credit the lender has formally agreed to make available, whether or not it is currently borrowed.",
  outstanding:
    "The amount currently borrowed and not yet repaid — the balance the company still owes on the facility.",
  "A/R":
    "Accounts Receivable — money customers owe the company for goods or services already delivered but not yet paid for.",
  inventory:
    "The goods and materials a company holds to sell or use in production, which can serve as collateral for a loan.",
  "cross-aging":
    "A rule that makes a customer's entire balance ineligible once a large enough portion of it becomes overdue, on the view that the whole account is now risky.",
  dilution:
    "The portion of receivables that never gets collected in cash — due to returns, discounts, or credits — which lenders track because it lowers the real value of A/R.",
  provenance:
    "The documented trail showing exactly where a number came from — the source file and location — so every figure can be traced back and verified.",
};
