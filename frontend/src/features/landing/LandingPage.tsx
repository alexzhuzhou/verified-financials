import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck,
  ScrollText,
  FileBarChart,
  ArrowRight,
  ArrowDown,
  Sparkles,
  Gauge,
  Check,
  FileCheck2,
  TrendingDown,
  Lock,
  Zap,
  Eye,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { useInView } from "@/hooks/useInView";

import wordmark from "@/assets/brand/wordmark.png";
import mark from "@/assets/brand/mark.png";
import shotVerification from "@/assets/landing/verification.png";
import shotCertificate from "@/assets/landing/certificate.png";
import shotFccr from "@/assets/landing/fccr.png";

/* ------------------------------------------------------------------ */
/* Small reusable helpers                                              */
/* ------------------------------------------------------------------ */

/** Fade + rise when scrolled into view. */
function Reveal({
  children,
  className = "",
  as: Tag = "div",
  delayMs = 0,
}: {
  children: React.ReactNode;
  className?: string;
  as?: "div" | "section" | "li" | "header" | "p" | "h2" | "h3";
  delayMs?: number;
}) {
  const { ref, inView } = useInView();
  const Component = Tag as React.ElementType;
  return (
    <Component
      ref={ref}
      className={`reveal ${inView ? "is-in" : ""} ${className}`}
      style={{ transitionDelay: `${delayMs}ms` }}
    >
      {children}
    </Component>
  );
}

/** A frosted "browser window" frame that straightens on scroll-in. */
function WindowFrame({
  src,
  alt,
  label,
}: {
  src: string;
  alt: string;
  label: string;
}) {
  const { ref, inView } = useInView();
  return (
    <div
      ref={ref}
      className={`frame-tilt ${inView ? "is-in" : ""} rounded-xl border border-white/10 bg-white/[0.04] p-2 shadow-[0_40px_90px_-30px_rgba(0,0,0,0.65)] backdrop-blur`}
    >
      <div className="flex items-center gap-2 px-3 py-2">
        <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
        <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
        <span className="h-3 w-3 rounded-full bg-[#28c840]" />
        <span className="ml-3 truncate font-sans text-xs tracking-wide text-white/45">
          {label}
        </span>
      </div>
      <img
        src={src}
        alt={alt}
        className="w-full rounded-lg border border-white/10"
        loading="lazy"
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Hero signature visual: collateral steps down to availability        */
/* ------------------------------------------------------------------ */

function HeroVisual() {
  const { ref, inView } = useInView();

  // Count-ups fire only once the card is in view (AnimatedNumber animates on change).
  const gross = inView ? 50000000 : 0;
  const base = inView ? 27327500 : 0;
  const avail = inView ? 5327500 : 0;
  const fccr = inView ? 1.2 : 0;

  return (
    <div ref={ref} className="relative">
      {/* spotlight behind the card */}
      <div className="vf-spotlight pointer-events-none absolute -inset-x-10 -top-16 bottom-0" />
      <div className="relative rounded-2xl border border-white/12 bg-white/[0.06] p-6 shadow-[0_50px_120px_-40px_rgba(0,0,0,0.8)] backdrop-blur-xl sm:p-8">
        <div className="flex items-center justify-between">
          <span className="font-sans text-[11px] font-medium uppercase tracking-[0.22em] text-white/55">
            Borrowing Base · Live
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-2.5 py-1 font-sans text-[11px] text-white/70">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Reconciled
          </span>
        </div>

        {/* Collateral -> Base step-down */}
        <div className="mt-6 space-y-3">
          <Row
            label="Gross collateral"
            value={<AnimatedNumber value={gross} format="money" durationMs={1400} />}
            muted
          />
          <StepArrow text="Eligibility, advance rates & reserves applied" />
          <div className="rounded-xl border border-primary/40 bg-primary/15 p-4">
            <div className="flex items-baseline justify-between">
              <span className="font-sans text-xs uppercase tracking-widest text-white/60">
                Borrowing base
              </span>
              <AnimatedNumber
                value={base}
                format="money"
                durationMs={1600}
                className="font-serif text-2xl text-white sm:text-3xl"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <Stat
              label="Availability"
              value={
                <AnimatedNumber
                  value={avail}
                  format="money"
                  durationMs={1700}
                  className="text-emerald-300"
                />
              }
              sub="after $22.0M drawn"
            />
            <Stat
              label="FCCR"
              value={
                <span className="inline-flex items-baseline gap-1.5">
                  <AnimatedNumber
                    value={fccr}
                    format="ratio"
                    durationMs={1500}
                    className="text-white"
                  />
                  <Gauge className="h-4 w-4 translate-y-0.5 text-amber-300" aria-hidden />
                </span>
              }
              sub="vs 1.10x covenant"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  muted = false,
}: {
  label: string;
  value: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="font-sans text-sm text-white/55">{label}</span>
      <span
        className={`tnum tabular-nums font-serif text-xl ${muted ? "text-white/80" : "text-white"}`}
      >
        {value}
      </span>
    </div>
  );
}

function StepArrow({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2 pl-1 text-white/40">
      <ArrowDown className="h-4 w-4 text-primary" aria-hidden />
      <span className="font-sans text-[11px] uppercase tracking-wider">{text}</span>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: React.ReactNode;
  sub: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="font-sans text-[11px] uppercase tracking-widest text-white/45">
        {label}
      </div>
      <div className="mt-1 tnum tabular-nums font-serif text-2xl">{value}</div>
      <div className="mt-0.5 font-sans text-[11px] text-white/40">{sub}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Capability row                                                      */
/* ------------------------------------------------------------------ */

interface Capability {
  index: string;
  icon: React.ReactNode;
  eyebrow: string;
  title: string;
  body: string;
  bullets: string[];
  src: string;
  alt: string;
  label: string;
}

function CapabilityRow({ cap, flip }: { cap: Capability; flip: boolean }) {
  return (
    <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
      <Reveal className={flip ? "lg:order-2" : ""}>
        <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 font-sans text-xs font-medium uppercase tracking-widest text-primary">
          {cap.icon}
          {cap.eyebrow}
        </div>
        <div className="mt-4 flex items-baseline gap-3">
          <span className="font-serif text-2xl text-primary/50">{cap.index}</span>
          <h3 className="font-serif text-3xl leading-tight text-[#1a2332] sm:text-4xl">
            {cap.title}
          </h3>
        </div>
        <p className="mt-4 max-w-md font-sans text-base leading-relaxed text-[#1a2332]/70">
          {cap.body}
        </p>
        <ul className="mt-6 space-y-3">
          {cap.bullets.map((b) => (
            <li key={b} className="flex items-start gap-3 font-sans text-sm text-[#1a2332]/80">
              <span className="mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-primary/10 text-primary">
                <Check className="h-3.5 w-3.5" aria-hidden />
              </span>
              {b}
            </li>
          ))}
        </ul>
      </Reveal>

      <div className={flip ? "lg:order-1" : ""}>
        {/* Dark recessed stage so the frosted frame reads as cinematic. */}
        <div className="rounded-2xl bg-gradient-to-b from-[#1a1410] to-[#0e0b09] p-5 sm:p-7">
          <WindowFrame src={cap.src} alt={cap.alt} label={cap.label} />
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const capabilities: Capability[] = [
    {
      index: "01",
      icon: <FileCheck2 className="h-3.5 w-3.5" aria-hidden />,
      eyebrow: "Verify",
      title: "Reconcile the files. Flag what won't tie out.",
      body: "Drop in the borrower's general ledger, A/R aging, inventory and financials. Verified Financials ties every figure back to source and surfaces only the exceptions that matter — with the variance quantified.",
      bullets: [
        "A/R off by $200K against the aging detail",
        "Inventory variance of $500K versus the perpetual",
        "Revenue discrepancy of $1.3M, traced to source",
      ],
      src: shotVerification,
      alt: "Verification screen listing three reconciliation exceptions with quantified variances.",
      label: "verified-financials.app / verification",
    },
    {
      index: "02",
      icon: <FileBarChart className="h-3.5 w-3.5" aria-hidden />,
      eyebrow: "Size the loan",
      title: "From gross collateral to a bank-ready certificate.",
      body: "Apply eligibility rules, advance rates and reserves deterministically. $50.0M of gross collateral steps down to a $27,327,500 borrowing base — and a clean, exportable certificate your credit committee can sign.",
      bullets: [
        "$27,327,500 borrowing base, fully itemized",
        "$5,327,500 of availability after $22.0M drawn",
        "Bank-ready certificate with full provenance",
      ],
      src: shotCertificate,
      alt: "Borrowing base certificate showing the step-down from gross collateral to availability.",
      label: "verified-financials.app / certificate",
    },
    {
      index: "03",
      icon: <Gauge className="h-3.5 w-3.5" aria-hidden />,
      eyebrow: "Watch the covenant",
      title: "Early warning before a breach becomes a surprise.",
      body: "Track the fixed-charge coverage ratio continuously. Today it sits at 1.20x against a 1.10x covenant — compliant, but thin. Stress the inputs and you can watch it slide to 0.89x before it ever happens for real.",
      bullets: [
        "FCCR 1.20x vs a 1.10x covenant — compliant but thin",
        "Stress scenario drops coverage to 0.89x (breach)",
        "Headroom monitored continuously, not quarterly",
      ],
      src: shotFccr,
      alt: "FCCR covenant monitor showing 1.20x current coverage and a 0.89x stress breach.",
      label: "verified-financials.app / covenant",
    },
  ];

  const pains = [
    {
      icon: <ScrollText className="h-5 w-5" aria-hidden />,
      title: "Messy, multi-file data",
      body: "Ledgers, agings and financials arrive in a dozen formats that never quite agree.",
    },
    {
      icon: <Gauge className="h-5 w-5" aria-hidden />,
      title: "Slow spreadsheet math",
      body: "Borrowing-base models live in fragile workbooks that take days to rebuild and reconcile.",
    },
    {
      icon: <TrendingDown className="h-5 w-5" aria-hidden />,
      title: "Covenants caught too late",
      body: "A coverage breach surfaces at quarter-end — long after there was time to act.",
    },
    {
      icon: <Lock className="h-5 w-5" aria-hidden />,
      title: "No audit trail",
      body: "When the number is questioned, nobody can prove where it actually came from.",
    },
  ];

  const outcomes = [
    {
      icon: <Zap className="h-5 w-5" aria-hidden />,
      title: "Speed",
      body: "Days of spreadsheet reconciliation collapse into a single, reviewable pass.",
    },
    {
      icon: <ShieldCheck className="h-5 w-5" aria-hidden />,
      title: "Trust",
      body: "Deterministic math with full provenance — every figure traces back to source.",
    },
    {
      icon: <Eye className="h-5 w-5" aria-hidden />,
      title: "Foresight",
      body: "Covenant stress testing flags a breach before it ever reaches the statements.",
    },
    {
      icon: <FileCheck2 className="h-5 w-5" aria-hidden />,
      title: "Tangibility",
      body: "A bank-ready certificate your credit committee can actually sign and file.",
    },
  ];

  return (
    <div className="min-h-screen bg-[#f4f6f9] font-sans text-[#1a2332]">
      {/* ---------------- Nav ---------------- */}
      <header
        className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
          scrolled
            ? "border-b border-black/5 bg-white/85 backdrop-blur-md"
            : "border-b border-transparent bg-transparent"
        }`}
      >
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          <Link to="/app" className="flex items-center" aria-label="Red Lion Advisory home">
            <img
              src={wordmark}
              alt="Red Lion Advisory"
              className={`h-7 w-auto transition ${scrolled ? "" : "brightness-0 invert"}`}
            />
          </Link>
          <Button
            asChild
            size="lg"
            className={
              scrolled ? "" : "bg-primary text-primary-foreground hover:bg-primary/90"
            }
          >
            <Link to="/app">
              Launch the demo
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </Button>
        </nav>
      </header>

      {/* ---------------- Hero ---------------- */}
      <section className="relative overflow-hidden bg-gradient-to-b from-[#1a0809] via-[#120607] to-[#0c0a09] text-white">
        {/* drifting grid */}
        <div className="vf-grid pointer-events-none absolute inset-0 opacity-60" aria-hidden />
        {/* maroon glow top-left */}
        <div
          className="pointer-events-none absolute -left-40 -top-40 h-[36rem] w-[36rem] rounded-full bg-[#8a1c1c] opacity-30 blur-[120px]"
          aria-hidden
        />
        {/* giant rotating watermark mark */}
        <img
          src={mark}
          alt=""
          aria-hidden
          className="vf-spin-slow pointer-events-none absolute -right-40 top-10 h-[42rem] w-[42rem] select-none opacity-[0.05]"
        />

        <div className="relative mx-auto grid max-w-6xl items-center gap-14 px-5 pb-24 pt-32 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:pb-32 lg:pt-40">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 font-sans text-[11px] font-medium uppercase tracking-[0.22em] text-white/70">
              <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden />
              Red Lion Advisory · Asset-Based Lending
            </div>

            <h1 className="mt-6 font-serif text-5xl leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">
              The borrowing base,
              <br />
              <span className="relative inline-block">
                <span>proven cold.</span>
                <span className="vf-sheen absolute inset-0" aria-hidden>
                  proven cold.
                </span>
              </span>
            </h1>

            <p className="mt-6 max-w-md font-sans text-lg leading-relaxed text-white/65">
              Verify the data. Size the loan. Watch the covenant. One workspace
              that reconciles a borrower's files, computes how much can be
              borrowed, and sounds the alarm before a covenant breaks.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Button
                asChild
                size="lg"
                className="vf-cta-glow h-12 px-7 text-base"
              >
                <Link to="/app">
                  Launch the demo
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
              </Button>
              <span className="font-sans text-sm text-white/45">
                Live, on synthetic data — no signup.
              </span>
            </div>
          </div>

          <Reveal>
            <HeroVisual />
          </Reveal>
        </div>

        {/* fade into the light body */}
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-b from-transparent to-[#f4f6f9]"
          aria-hidden
        />
      </section>

      {/* ---------------- The problem ---------------- */}
      <section className="mx-auto max-w-6xl px-5 py-24 sm:px-8 lg:py-32">
        <Reveal as="header" className="max-w-3xl">
          <p className="font-sans text-xs font-semibold uppercase tracking-[0.22em] text-primary">
            The problem
          </p>
          <h2 className="mt-4 font-serif text-4xl leading-tight sm:text-5xl">
            Asset-based lending runs on numbers nobody fully trusts — assembled
            by hand, checked too late.
          </h2>
        </Reveal>

        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {pains.map((p, i) => (
            <Reveal key={p.title} delayMs={i * 90}>
              <div className="h-full rounded-2xl border border-black/5 bg-white p-6 shadow-[0_2px_24px_-12px_rgba(26,35,50,0.25)]">
                <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  {p.icon}
                </div>
                <h3 className="mt-5 font-serif text-xl">{p.title}</h3>
                <p className="mt-2 font-sans text-sm leading-relaxed text-[#1a2332]/65">
                  {p.body}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------------- Capabilities ---------------- */}
      <section className="border-y border-black/5 bg-white">
        <div className="mx-auto max-w-6xl px-5 py-24 sm:px-8 lg:py-32">
          <Reveal as="header" className="mx-auto max-w-2xl text-center">
            <p className="font-sans text-xs font-semibold uppercase tracking-[0.22em] text-primary">
              What it does
            </p>
            <h2 className="mt-4 font-serif text-4xl leading-tight sm:text-5xl">
              Three jobs, done deterministically.
            </h2>
            <p className="mt-4 font-sans text-base text-[#1a2332]/65">
              Shown here on synthetic data — a fictional ~$180M McLane-style food
              distributor.
            </p>
          </Reveal>

          <div className="mt-20 space-y-24 lg:space-y-32">
            {capabilities.map((cap, i) => (
              <CapabilityRow key={cap.index} cap={cap} flip={i % 2 === 1} />
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- Trust band ---------------- */}
      <section className="relative overflow-hidden bg-primary text-primary-foreground">
        <img
          src={mark}
          alt=""
          aria-hidden
          className="pointer-events-none absolute -bottom-24 -right-16 h-96 w-96 select-none opacity-[0.08]"
        />
        <div className="relative mx-auto max-w-5xl px-5 py-20 text-center sm:px-8 lg:py-28">
          <Reveal>
            <ShieldCheck className="mx-auto h-10 w-10 opacity-90" aria-hidden />
            <h2 className="mt-6 font-serif text-3xl leading-tight sm:text-4xl lg:text-5xl">
              Deterministic math. Full provenance.
              <br className="hidden sm:block" /> AI explains — it never invents.
            </h2>
            <p className="mx-auto mt-6 max-w-2xl font-sans text-base leading-relaxed text-primary-foreground/80">
              Every figure is computed by fixed rules and traces back to its
              source document. The model narrates the result in plain English —
              but the numbers are the numbers, and they always tie out.
            </p>
          </Reveal>
        </div>
      </section>

      {/* ---------------- Outcomes ---------------- */}
      <section className="mx-auto max-w-6xl px-5 py-24 sm:px-8 lg:py-32">
        <Reveal as="header" className="max-w-2xl">
          <p className="font-sans text-xs font-semibold uppercase tracking-[0.22em] text-primary">
            The outcome
          </p>
          <h2 className="mt-4 font-serif text-4xl leading-tight sm:text-5xl">
            What your credit team actually gets.
          </h2>
        </Reveal>

        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {outcomes.map((o, i) => (
            <Reveal key={o.title} delayMs={i * 90}>
              <div className="group h-full rounded-2xl border border-black/5 bg-white p-7 shadow-[0_2px_24px_-12px_rgba(26,35,50,0.25)] transition hover:-translate-y-1 hover:shadow-[0_18px_44px_-20px_rgba(138,28,28,0.45)]">
                <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                  {o.icon}
                </div>
                <h3 className="mt-5 font-serif text-2xl">{o.title}</h3>
                <p className="mt-2 font-sans text-sm leading-relaxed text-[#1a2332]/65">
                  {o.body}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------------- Closing CTA + footer ---------------- */}
      <footer className="relative overflow-hidden bg-gradient-to-b from-[#14181f] to-[#0c0a09] text-white">
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-72 w-72 -translate-x-1/2 rounded-full bg-[#8a1c1c] opacity-30 blur-[110px]"
          aria-hidden
        />
        <div className="relative mx-auto max-w-4xl px-5 py-24 text-center sm:px-8 lg:py-32">
          <Reveal>
            <h2 className="font-serif text-4xl leading-tight sm:text-5xl lg:text-6xl">
              See a $27,327,500 borrowing base
              <br className="hidden sm:block" /> proven in minutes.
            </h2>
            <p className="mx-auto mt-6 max-w-xl font-sans text-lg text-white/60">
              Step through the live demonstration — verification, certificate and
              covenant, on synthetic data.
            </p>
            <div className="mt-10 flex justify-center">
              <Button asChild size="lg" className="vf-cta-glow h-12 px-8 text-base">
                <Link to="/app">
                  Launch the demo
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
              </Button>
            </div>
          </Reveal>
        </div>

        <div className="relative border-t border-white/10">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 sm:flex-row sm:px-8">
            <img
              src={wordmark}
              alt="Red Lion Advisory"
              className="h-6 w-auto brightness-0 invert"
            />
            <p className="font-sans text-xs text-white/45">
              Demonstration on synthetic data. © Red Lion Advisory.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
